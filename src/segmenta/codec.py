"""Checksum-framed JSON encoding used by segment files."""

from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from typing import BinaryIO, Iterator

from .models import Event


class FrameError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DecodedFrame:
    event: Event
    offset: int
    next_offset: int


def encode_event(event: Event) -> bytes:
    payload = json.dumps(
        event.to_dict(), ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    return f"{checksum:08x}\t".encode("ascii") + payload + b"\n"


def decode_frame(line: bytes) -> Event:
    if not line.endswith(b"\n"):
        raise FrameError("incomplete frame")
    try:
        checksum_raw, payload = line[:-1].split(b"\t", 1)
        expected = int(checksum_raw, 16)
    except (ValueError, TypeError) as exc:
        raise FrameError("invalid frame header") from exc
    actual = zlib.crc32(payload) & 0xFFFFFFFF
    if actual != expected:
        raise FrameError("checksum mismatch")
    try:
        value = json.loads(payload)
        return Event.from_dict(value)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise FrameError(f"invalid event payload: {exc}") from exc


def iter_frames(handle: BinaryIO) -> Iterator[DecodedFrame]:
    while True:
        offset = handle.tell()
        line = handle.readline()
        if not line:
            return
        event = decode_frame(line)
        yield DecodedFrame(event=event, offset=offset, next_offset=handle.tell())

