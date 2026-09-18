"""Segmenta public API."""

from .models import Event, EventValidationError
from .aggregate import aggregate
from .lifecycle import CompactionReport, compact
from .query import CursorError, QueryPage, query
from .storage import EventStore, RecoveryReport

__all__ = [
    "CompactionReport",
    "CursorError",
    "Event",
    "EventStore",
    "EventValidationError",
    "QueryPage",
    "RecoveryReport",
    "aggregate",
    "compact",
    "query",
]
__version__ = "0.1.0"
