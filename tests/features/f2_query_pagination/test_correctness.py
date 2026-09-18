from __future__ import annotations

import tempfile
import unittest

from segmenta import CursorError, query
from tests.helpers import populated_store


class QueryPaginationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = populated_store(self.temp.name)

    def test_filters_type_time_and_nested_data(self):
        page = query(
            self.store,
            event_type="purchase",
            start=3,
            end=9,
            where={"data.nested.region": "west", "data.user": "u1"},
        )
        self.assertEqual([event.timestamp for event in page.events], [7.0])

    def test_cursor_pages_without_duplicates_or_gaps(self):
        seen = []
        cursor = None
        while True:
            page = query(self.store, event_type="purchase", limit=2, cursor=cursor)
            seen.extend(event.timestamp for event in page.events)
            cursor = page.next_cursor
            if cursor is None:
                break
        self.assertEqual(seen, [1, 3, 5, 7, 9, 11])

    def test_cursor_is_bound_to_original_query(self):
        first = query(self.store, event_type="purchase", limit=1)
        self.assertIsNotNone(first.next_cursor)
        with self.assertRaises(CursorError):
            query(self.store, event_type="view", limit=1, cursor=first.next_cursor)

    def test_rejects_invalid_range_and_limit(self):
        with self.assertRaises(ValueError):
            query(self.store, start=10, end=1)
        with self.assertRaises(ValueError):
            query(self.store, limit=0)


if __name__ == "__main__":
    unittest.main()

