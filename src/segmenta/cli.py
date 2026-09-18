"""Command-line interface for administering and querying a Segmenta store."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, TextIO

from .aggregate import aggregate
from .lifecycle import compact
from .query import query
from .storage import EventStore


def _json_value(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _where(values: Iterable[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"invalid filter {value!r}; expected data.path=JSON_VALUE")
        path, raw = value.split("=", 1)
        if not path.startswith("data."):
            raise ValueError("filters must start with data.")
        result[path] = _json_value(raw)
    return result


def _load_json_lines(handle: TextIO) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, raw in enumerate(handle, 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {line_number}: event must be a JSON object")
        events.append(value)
    return events


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="segmenta", description="Local structured event store")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a store")
    init.add_argument("store")
    init.add_argument("--max-segment-bytes", type=int, default=16 * 1024 * 1024)

    append = sub.add_parser("append", help="append JSON Lines events")
    append.add_argument("store")
    append.add_argument("input", help="JSONL file or - for stdin")
    append.add_argument("--no-sync", action="store_true", help="skip fsync for bulk loading")

    read = sub.add_parser("query", help="filter and page through events")
    read.add_argument("store")
    read.add_argument("--type", dest="event_type")
    read.add_argument("--start", type=float)
    read.add_argument("--end", type=float)
    read.add_argument("--where", action="append", default=[])
    read.add_argument("--limit", type=int, default=100)
    read.add_argument("--cursor")

    agg = sub.add_parser("aggregate", help="stream an aggregation")
    agg.add_argument("store")
    agg.add_argument("operation", choices=["count", "sum", "min", "max", "avg"])
    agg.add_argument("--value-path")
    agg.add_argument("--group-by")
    agg.add_argument("--type", dest="event_type")
    agg.add_argument("--start", type=float)
    agg.add_argument("--end", type=float)
    agg.add_argument("--where", action="append", default=[])

    compaction = sub.add_parser("compact", help="rewrite segments and apply retention")
    compaction.add_argument("store")
    compaction.add_argument("--retain-after", type=float)

    recovery = sub.add_parser("recover", help="verify checksums and optionally repair a bad tail")
    recovery.add_argument("store")
    recovery.add_argument("--repair", action="store_true")

    stats = sub.add_parser("stats", help="show store size")
    stats.add_argument("store")
    return parser


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


def run(args: argparse.Namespace, *, stdin: TextIO = sys.stdin) -> int:
    if args.command == "init":
        EventStore.create(args.store, max_segment_bytes=args.max_segment_bytes)
        _print({"store": str(Path(args.store)), "created": True})
        return 0

    store = EventStore(args.store)
    if args.command == "append":
        if args.input == "-":
            events = _load_json_lines(stdin)
        else:
            with open(args.input, encoding="utf-8") as handle:
                events = _load_json_lines(handle)
        written = store.append(events, sync=not args.no_sync)
        _print({"appended": len(written), "ids": [event.id for event in written]})
    elif args.command == "query":
        page = query(
            store,
            event_type=args.event_type,
            start=args.start,
            end=args.end,
            where=_where(args.where),
            limit=args.limit,
            cursor=args.cursor,
        )
        _print({"events": [event.to_dict() for event in page.events], "next_cursor": page.next_cursor})
    elif args.command == "aggregate":
        result = aggregate(
            store,
            operation=args.operation,
            value_path=args.value_path,
            group_by=args.group_by,
            event_type=args.event_type,
            start=args.start,
            end=args.end,
            where=_where(args.where),
        )
        _print({"groups": result})
    elif args.command == "compact":
        _print(asdict(compact(store, retain_after=args.retain_after)))
    elif args.command == "recover":
        _print(asdict(store.recover(repair=args.repair)))
    elif args.command == "stats":
        _print(store.stats())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        return run(parser.parse_args(argv))
    except (FileNotFoundError, ValueError, OSError) as exc:
        parser.exit(2, f"segmenta: error: {exc}\n")
