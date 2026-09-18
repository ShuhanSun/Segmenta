"""Measurement helpers shared by feature-level performance entry points."""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Callable

from segmenta import EventStore, aggregate, compact, query


def events(count: int) -> list[dict]:
    return [
        {
            "timestamp": float(index),
            "type": "rare" if index % 100 == 0 else "common",
            "data": {
                "user": f"u{index % 1000}",
                "value": index % 10_000,
                "region": f"r{index % 8}",
                "message": "event payload for repeatable local benchmark",
            },
        }
        for index in range(count)
    ]


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile_value)))
    return ordered[index]


def summarize(name: str, count: int, seconds: list[float], peak_memory_mb: float, **extra) -> dict:
    milliseconds = [value * 1000 for value in seconds]
    median_seconds = statistics.median(seconds)
    return {
        "benchmark": name,
        "events": count,
        "repeats": len(seconds),
        "latency_ms": {
            "mean": round(statistics.mean(milliseconds), 3),
            "p50": round(statistics.median(milliseconds), 3),
            "p95": round(percentile(milliseconds, 0.95), 3),
            "p99": round(percentile(milliseconds, 0.99), 3),
        },
        "throughput_events_per_sec": round(count / median_seconds, 1),
        "peak_traced_memory_mb": round(peak_memory_mb, 3),
        **extra,
    }


def timed(action: Callable[[], object], repeats: int, warmups: int = 1) -> tuple[list[float], float]:
    for _ in range(warmups):
        action()
    durations = []
    for _ in range(repeats):
        started = time.perf_counter()
        action()
        durations.append(time.perf_counter() - started)
    tracemalloc.start()
    action()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return durations, peak / (1024 * 1024)


def bench_append(count: int, repeats: int) -> dict:
    payload = events(count)
    durations: list[float] = []
    bytes_written = 0
    for run in range(repeats + 1):
        temp = tempfile.TemporaryDirectory()
        try:
            store = EventStore.create(temp.name, max_segment_bytes=4 * 1024 * 1024)
            started = time.perf_counter()
            store.append(payload, sync=False)
            elapsed = time.perf_counter() - started
            bytes_written = sum(path.stat().st_size for path in Path(temp.name).glob("segment-*.log"))
            if run:
                durations.append(elapsed)
        finally:
            temp.cleanup()
    temp = tempfile.TemporaryDirectory()
    try:
        store = EventStore.create(temp.name, max_segment_bytes=4 * 1024 * 1024)
        tracemalloc.start()
        store.append(payload, sync=False)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    finally:
        temp.cleanup()
    peak = peak_bytes / (1024 * 1024)
    return summarize("F1_append_batch_no_fsync", count, durations, peak, bytes_written=bytes_written)


def _prepared_store(count: int):
    temp = tempfile.TemporaryDirectory()
    store = EventStore.create(temp.name, max_segment_bytes=4 * 1024 * 1024)
    store.append(events(count), sync=False)
    return temp, store


def bench_query(count: int, repeats: int) -> dict:
    temp, store = _prepared_store(count)
    try:
        def action():
            return query(store, event_type="rare", where={"data.region": "r0"}, limit=10_000)

        durations, peak = timed(action, repeats)
        matches = len(action().events)
        return summarize("F2_filtered_full_scan", count, durations, peak, matches=matches)
    finally:
        temp.cleanup()


def bench_aggregate(count: int, repeats: int) -> dict:
    temp, store = _prepared_store(count)
    try:
        def action():
            return aggregate(store, operation="sum", value_path="data.value", group_by="data.region")

        durations, peak = timed(action, repeats)
        groups = len(action())
        return summarize("F3_grouped_sum", count, durations, peak, groups=groups)
    finally:
        temp.cleanup()


def bench_compact(count: int, repeats: int) -> dict:
    payload = events(count)
    durations: list[float] = []
    report = None
    for run in range(repeats + 1):
        temp = tempfile.TemporaryDirectory()
        try:
            store = EventStore.create(temp.name, max_segment_bytes=4 * 1024 * 1024)
            store.append(payload, sync=False)
            started = time.perf_counter()
            report = compact(store, retain_after=count / 2)
            elapsed = time.perf_counter() - started
            if run:
                durations.append(elapsed)
        finally:
            temp.cleanup()
    temp = tempfile.TemporaryDirectory()
    try:
        store = EventStore.create(temp.name, max_segment_bytes=4 * 1024 * 1024)
        store.append(payload, sync=False)
        tracemalloc.start()
        compact(store, retain_after=count / 2)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    finally:
        temp.cleanup()
    peak = peak_bytes / (1024 * 1024)
    assert report is not None
    return summarize(
        "F4_retention_compaction",
        count,
        durations,
        peak,
        events_after=report.events_after,
        bytes_after=report.bytes_after,
    )


BENCHMARKS = {
    "append": bench_append,
    "query": bench_query,
    "aggregate": bench_aggregate,
    "compact": bench_compact,
}


def run_one(name: str, count: int, repeats: int) -> dict:
    if count < 1:
        raise ValueError("events must be positive")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    return BENCHMARKS[name](count, repeats)


def feature_main(name: str) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=50_000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_one(name, args.events, args.repeats)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0
