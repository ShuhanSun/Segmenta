"""Append-only segment storage and deterministic tail recovery."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .codec import FrameError, decode_frame, encode_event, iter_frames
from .models import Event, EventValidationError


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    files_checked: int
    frames_checked: int
    bytes_truncated: int
    repaired_files: tuple[str, ...]


class EventStore:
    """A directory-backed, checksum-framed event store.

    Writes are serialized across processes with an advisory lock. A batch is
    validated and encoded before touching disk, so validation failure cannot
    partially append it. A process crash may leave a partial tail; ``recover``
    can detect or truncate that tail deterministically.
    """

    FORMAT_VERSION = 1

    def __init__(self, root: str | os.PathLike[str], *, max_segment_bytes: int = 16 * 1024 * 1024):
        if max_segment_bytes < 1024:
            raise ValueError("max_segment_bytes must be at least 1024")
        self.root = Path(root)
        self.max_segment_bytes = max_segment_bytes
        self._thread_lock = threading.RLock()

    @classmethod
    def create(
        cls, root: str | os.PathLike[str], *, max_segment_bytes: int = 16 * 1024 * 1024
    ) -> "EventStore":
        store = cls(root, max_segment_bytes=max_segment_bytes)
        store.root.mkdir(parents=True, exist_ok=True)
        metadata = store.root / "metadata.json"
        if not metadata.exists():
            temporary = store.root / ".metadata.tmp"
            temporary.write_text(
                json.dumps({"format_version": cls.FORMAT_VERSION}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, metadata)
        store._lock_path.touch(exist_ok=True)
        return store

    @property
    def _lock_path(self) -> Path:
        return self.root / ".write.lock"

    def _require_store(self) -> None:
        metadata = self.root / "metadata.json"
        if not metadata.is_file():
            raise FileNotFoundError(f"not a Segmenta store: {self.root}")
        value = json.loads(metadata.read_text(encoding="utf-8"))
        if value.get("format_version") != self.FORMAT_VERSION:
            raise ValueError(f"unsupported store format: {value.get('format_version')}")

    @contextlib.contextmanager
    def _write_lock(self) -> Iterator[None]:
        self._require_store()
        with self._thread_lock, self._lock_path.open("a+b") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def _segments(self) -> list[Path]:
        self._require_store()
        return sorted(self.root.glob("segment-*.log"))

    def _next_segment(self) -> Path:
        segments = self._segments()
        if not segments:
            return self.root / "segment-000001.log"
        current = segments[-1]
        if current.stat().st_size < self.max_segment_bytes:
            return current
        number = int(current.stem.split("-")[1]) + 1
        return self.root / f"segment-{number:06d}.log"

    def append(self, events: Iterable[Event | dict], *, sync: bool = True) -> list[Event]:
        prepared: list[Event] = []
        for value in events:
            event = value if isinstance(value, Event) else Event.from_dict(value)
            if event.id is None:
                event = Event(event.timestamp, event.type, event.data, uuid.uuid4().hex)
            prepared.append(event)
        if not prepared:
            return []
        frames = [encode_event(event) for event in prepared]

        with self._write_lock():
            path = self._next_segment()
            with path.open("ab", buffering=0) as handle:
                for frame in frames:
                    handle.write(frame)
                if sync:
                    os.fsync(handle.fileno())
        return prepared

    def iter_events(self) -> Iterator[Event]:
        for path in self._segments():
            with path.open("rb") as handle:
                for frame in iter_frames(handle):
                    yield frame.event

    def recover(self, *, repair: bool = False) -> RecoveryReport:
        files_checked = 0
        frames_checked = 0
        bytes_truncated = 0
        repaired: list[str] = []
        lock = self._write_lock() if repair else contextlib.nullcontext()
        with lock:
            for path in self._segments():
                files_checked += 1
                last_good = 0
                invalid_offset: int | None = None
                with path.open("rb") as handle:
                    while True:
                        offset = handle.tell()
                        line = handle.readline()
                        if not line:
                            break
                        try:
                            decode_frame(line)
                        except FrameError:
                            invalid_offset = offset
                            break
                        frames_checked += 1
                        last_good = handle.tell()
                if invalid_offset is not None:
                    damaged = path.stat().st_size - last_good
                    if not repair:
                        raise FrameError(f"corrupt frame in {path.name} at byte {invalid_offset}")
                    with path.open("r+b") as handle:
                        handle.truncate(last_good)
                        handle.flush()
                        os.fsync(handle.fileno())
                    bytes_truncated += damaged
                    repaired.append(path.name)
        return RecoveryReport(files_checked, frames_checked, bytes_truncated, tuple(repaired))

    def stats(self) -> dict[str, int]:
        segments = self._segments()
        events = 0
        for _ in self.iter_events():
            events += 1
        return {
            "segments": len(segments),
            "events": events,
            "bytes": sum(path.stat().st_size for path in segments),
        }

