"""Public event model and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping


class EventValidationError(ValueError):
    """Raised when an event does not satisfy the public event contract."""


def _validate_json(value: Any, path: str = "data") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise EventValidationError(f"{path} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise EventValidationError(f"{path} keys must be strings")
            _validate_json(item, f"{path}.{key}")
        return
    raise EventValidationError(f"{path} contains unsupported value {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class Event:
    timestamp: float
    type: str
    data: Mapping[str, Any]
    id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)):
            raise EventValidationError("timestamp must be a finite number")
        if not isfinite(float(self.timestamp)):
            raise EventValidationError("timestamp must be a finite number")
        if not isinstance(self.type, str) or not self.type.strip():
            raise EventValidationError("type must be a non-empty string")
        if len(self.type) > 128:
            raise EventValidationError("type must not exceed 128 characters")
        if not isinstance(self.data, Mapping):
            raise EventValidationError("data must be an object")
        _validate_json(dict(self.data))
        if self.id is not None and (not isinstance(self.id, str) or not self.id):
            raise EventValidationError("id must be a non-empty string when supplied")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Event":
        if not isinstance(value, Mapping):
            raise EventValidationError("event must be an object")
        allowed = {"timestamp", "type", "data", "id"}
        unknown = set(value) - allowed
        if unknown:
            raise EventValidationError(f"unknown event fields: {', '.join(sorted(unknown))}")
        missing = {"timestamp", "type", "data"} - set(value)
        if missing:
            raise EventValidationError(f"missing event fields: {', '.join(sorted(missing))}")
        return cls(
            timestamp=value["timestamp"],
            type=value["type"],
            data=value["data"],
            id=value.get("id"),
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "timestamp": self.timestamp,
            "type": self.type,
            "data": dict(self.data),
        }
        if self.id is not None:
            result["id"] = self.id
        return result

