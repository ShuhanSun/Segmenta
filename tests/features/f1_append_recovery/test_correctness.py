from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from segmenta import EventStore, EventValidationError
from segmenta.codec import FrameError


class AppendRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = EventStore.create(self.temp.name, max_segment_bytes=1024)

    def test_append_assigns_ids_preserves_order_and_rotates(self):
        values = [
            {"timestamp": index, "type": "tick", "data": {"payload": "x" * 200}}
            for index in range(12)
        ]
        written = self.store.append(values, sync=False)
        read = list(self.store.iter_events())
        self.assertEqual(written, read)
        self.assertTrue(all(event.id for event in read))
        self.assertGreater(self.store.stats()["segments"], 1)

    def test_invalid_batch_does_not_append_a_prefix(self):
        with self.assertRaises(EventValidationError):
            self.store.append(
                [
                    {"timestamp": 1, "type": "valid", "data": {}},
                    {"timestamp": 2, "type": "", "data": {}},
                ]
            )
        self.assertEqual(self.store.stats()["events"], 0)

    def test_recover_reports_then_repairs_partial_tail(self):
        self.store.append([{"timestamp": 1, "type": "ok", "data": {}}], sync=False)
        segment = next(Path(self.temp.name).glob("segment-*.log"))
        with segment.open("ab") as handle:
            handle.write(b"12345678\t{\"partial\":")
        with self.assertRaises(FrameError):
            self.store.recover()
        report = self.store.recover(repair=True)
        self.assertGreater(report.bytes_truncated, 0)
        self.assertEqual(report.repaired_files, (segment.name,))
        self.assertEqual(len(list(self.store.iter_events())), 1)

    def test_rejects_non_json_values_and_unknown_fields(self):
        with self.assertRaises(EventValidationError):
            self.store.append([{"timestamp": 1, "type": "x", "data": {"v": object()}}])
        with self.assertRaises(EventValidationError):
            self.store.append([{"timestamp": 1, "type": "x", "data": {}, "extra": 1}])


if __name__ == "__main__":
    unittest.main()

