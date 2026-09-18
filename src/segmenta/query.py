"""Filtered reads with stable, query-bound physical cursors."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .models import Event
from .storage import EventStore


class CursorError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QueryPage:
    events: tuple[Event, ...]
    next_cursor: str | None


def lookup(event: Event, path: str) -> Any:
    if path == "type":
        return event.type
    if path == "timestamp":
        return event.timestamp
    if path == "id":
        return event.id
    if not path.startswith("data."):
        raise ValueError("field paths must be type, timestamp, id, or start with data.")
    value: Any = event.data
    for part in path.split(".")[1:]:
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _signature(
    event_type: str | None, start: float | None, end: float | None, where: Mapping[str, Any]
) -> str:
    raw = json.dumps([event_type, start, end, sorted(where.items())], separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _encode_cursor(segment: str, offset: int, signature: str) -> str:
    raw = json.dumps([segment, offset, signature], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str, signature: str) -> tuple[str, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        segment, offset, cursor_signature = json.loads(raw)
        if not isinstance(segment, str) or not isinstance(offset, int) or offset < 0:
            raise ValueError
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise CursorError("malformed cursor") from exc
    if cursor_signature != signature:
        raise CursorError("cursor belongs to a different query")
    return segment, offset


def query(
    store: EventStore,
    *,
    event_type: str | None = None,
    start: float | None = None,
    end: float | None = None,
    where: Mapping[str, Any] | None = None,
    limit: int = 100,
    cursor: str | None = None,
) -> QueryPage:
    if limit < 1 or limit > 10_000:
        raise ValueError("limit must be between 1 and 10000")
    if start is not None and end is not None and start > end:
        raise ValueError("start must not exceed end")
    filters = dict(where or {})
    for path in filters:
        if not path.startswith("data."):
            raise ValueError("where filters must use data.<field> paths")

    signature = _signature(event_type, start, end, filters)
    start_segment: str | None = None
    start_offset = 0
    if cursor:
        start_segment, start_offset = _decode_cursor(cursor, signature)

    matches: list[Event] = []
    last_location: tuple[str, int] | None = None
    has_more = False
    for located in store.iter_located_events(start_segment=start_segment, start_offset=start_offset):
        event = located.event
        if event_type is not None and event.type != event_type:
            continue
        if start is not None and event.timestamp < start:
            continue
        if end is not None and event.timestamp > end:
            continue
        if any(lookup(event, path) != expected for path, expected in filters.items()):
            continue
        if len(matches) == limit:
            has_more = True
            break
        matches.append(event)
        last_location = (located.segment, located.next_offset)

    next_cursor = None
    if has_more and last_location:
        next_cursor = _encode_cursor(*last_location, signature)
    return QueryPage(tuple(matches), next_cursor)

