from __future__ import annotations

import tempfile
import unittest

from segmenta import compact
from tests.helpers import populated_store


class CompactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = populated_store(self.temp.name, count=20)

    def test_compaction_preserves_order_and_ids(self):
        before = list(self.store.iter_events())
        report = compact(self.store)
        after = list(self.store.iter_events())
        self.assertEqual(before, after)
        self.assertEqual(report.events_before, report.events_after)

    def test_retention_discards_only_events_before_cutoff(self):
        report = compact(self.store, retain_after=10)
        remaining = list(self.store.iter_events())
        self.assertEqual([event.timestamp for event in remaining], list(range(10, 20)))
        self.assertEqual(report.events_before, 20)
        self.assertEqual(report.events_after, 10)
        self.assertLess(report.bytes_after, report.bytes_before)

    def test_empty_result_is_a_valid_store(self):
        compact(self.store, retain_after=100)
        self.assertEqual(list(self.store.iter_events()), [])
        self.assertEqual(self.store.stats()["events"], 0)


if __name__ == "__main__":
    unittest.main()

