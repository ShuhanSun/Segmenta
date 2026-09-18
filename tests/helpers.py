from __future__ import annotations

from segmenta import EventStore


def populated_store(root, count: int = 12, *, max_segment_bytes: int = 1024) -> EventStore:
    store = EventStore.create(root, max_segment_bytes=max_segment_bytes)
    store.append(
        [
            {
                "timestamp": float(index),
                "type": "purchase" if index % 2 else "view",
                "data": {
                    "user": f"u{index % 3}",
                    "amount": index * 1.5,
                    "nested": {"region": "west" if index % 2 else "east"},
                },
            }
            for index in range(count)
        ],
        sync=False,
    )
    return store

