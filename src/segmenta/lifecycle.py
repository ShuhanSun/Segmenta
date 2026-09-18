"""Retention compaction for Segmenta stores."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass

from .codec import encode_event
from .storage import EventStore


@dataclass(frozen=True, slots=True)
class CompactionReport:
    events_before: int
    events_after: int
    bytes_before: int
    bytes_after: int


def compact(store: EventStore, *, retain_after: float | None = None) -> CompactionReport:
    """Rewrite segments and optionally discard events older than a timestamp."""
    with store._write_lock():
        old_segments = store._segments()
        bytes_before = sum(path.stat().st_size for path in old_segments)
        events_before = 0
        events_after = 0
        temp_dir = tempfile.mkdtemp(prefix=".compact-", dir=store.root)
        try:
            segment_number = 1
            path = os.path.join(temp_dir, f"segment-{segment_number:06d}.log")
            handle = open(path, "wb", buffering=0)
            try:
                for event in store.iter_events():
                    events_before += 1
                    if retain_after is not None and event.timestamp < retain_after:
                        continue
                    frame = encode_event(event)
                    if handle.tell() and handle.tell() + len(frame) > store.max_segment_bytes:
                        os.fsync(handle.fileno())
                        handle.close()
                        segment_number += 1
                        path = os.path.join(temp_dir, f"segment-{segment_number:06d}.log")
                        handle = open(path, "wb", buffering=0)
                    handle.write(frame)
                    events_after += 1
                os.fsync(handle.fileno())
            finally:
                handle.close()

            backup_dir = tempfile.mkdtemp(prefix=".old-", dir=store.root)
            try:
                for old in old_segments:
                    os.replace(old, os.path.join(backup_dir, old.name))
                for name in sorted(os.listdir(temp_dir)):
                    os.replace(os.path.join(temp_dir, name), store.root / name)
                directory_fd = os.open(store.root, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except BaseException:
                for name in sorted(os.listdir(backup_dir)):
                    os.replace(os.path.join(backup_dir, name), store.root / name)
                raise
            finally:
                shutil.rmtree(backup_dir, ignore_errors=True)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        new_segments = store._segments()
        bytes_after = sum(path.stat().st_size for path in new_segments)
        return CompactionReport(events_before, events_after, bytes_before, bytes_after)

