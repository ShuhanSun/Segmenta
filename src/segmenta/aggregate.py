"""Streaming aggregation over the public query semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .query import lookup
from .storage import EventStore


@dataclass(slots=True)
class _Accumulator:
    count: int = 0
    total: float = 0.0
    minimum: float | None = None
    maximum: float | None = None

    def add(self, value: float | None) -> None:
        self.count += 1
        if value is not None:
            self.total += value
            self.minimum = value if self.minimum is None else min(self.minimum, value)
            self.maximum = value if self.maximum is None else max(self.maximum, value)


def aggregate(
    store: EventStore,
    *,
    operation: str = "count",
    value_path: str | None = None,
    group_by: str | None = None,
    event_type: str | None = None,
    start: float | None = None,
    end: float | None = None,
    where: Mapping[str, Any] | None = None,
) -> dict[str, int | float | None]:
    operations = {"count", "sum", "min", "max", "avg"}
    if operation not in operations:
        raise ValueError(f"operation must be one of {', '.join(sorted(operations))}")
    if operation != "count" and not value_path:
        raise ValueError(f"{operation} requires value_path")
    filters = dict(where or {})
    groups: dict[str, _Accumulator] = {}

    for event in store.iter_events():
        if event_type is not None and event.type != event_type:
            continue
        if start is not None and event.timestamp < start:
            continue
        if end is not None and event.timestamp > end:
            continue
        if any(lookup(event, path) != expected for path, expected in filters.items()):
            continue
        key_value = lookup(event, group_by) if group_by else "all"
        key = json_group_key(key_value)
        numeric: float | None = None
        if operation != "count":
            value = lookup(event, value_path or "")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            numeric = float(value)
        groups.setdefault(key, _Accumulator()).add(numeric)

    result: dict[str, int | float | None] = {}
    for key, item in groups.items():
        if operation == "count":
            result[key] = item.count
        elif operation == "sum":
            result[key] = item.total
        elif operation == "min":
            result[key] = item.minimum
        elif operation == "max":
            result[key] = item.maximum
        else:
            result[key] = item.total / item.count if item.count else None
    return result


def json_group_key(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)

