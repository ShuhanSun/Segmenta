from __future__ import annotations

import tempfile
import unittest

from segmenta import aggregate
from tests.helpers import populated_store


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = populated_store(self.temp.name, count=6)

    def test_count_grouped_by_type(self):
        self.assertEqual(aggregate(self.store, operation="count", group_by="type"), {"view": 3, "purchase": 3})

    def test_numeric_operations_and_filters(self):
        self.assertEqual(
            aggregate(
                self.store,
                operation="sum",
                value_path="data.amount",
                event_type="purchase",
            ),
            {"all": 13.5},
        )
        self.assertEqual(
            aggregate(self.store, operation="avg", value_path="data.amount", group_by="data.user"),
            {"u0": 2.25, "u1": 3.75, "u2": 5.25},
        )

    def test_nonnumeric_values_are_skipped_for_numeric_aggregation(self):
        self.store.append([{"timestamp": 10, "type": "view", "data": {"amount": "unknown"}}], sync=False)
        self.assertEqual(aggregate(self.store, operation="max", value_path="data.amount"), {"all": 7.5})

    def test_invalid_operation_contract(self):
        with self.assertRaises(ValueError):
            aggregate(self.store, operation="median", value_path="data.amount")
        with self.assertRaises(ValueError):
            aggregate(self.store, operation="sum")


if __name__ == "__main__":
    unittest.main()

