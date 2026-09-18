from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout

from segmenta.cli import build_parser, run


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parser = build_parser()

    def invoke(self, argv, stdin=""):
        output = io.StringIO()
        with redirect_stdout(output):
            status = run(self.parser.parse_args(argv), stdin=io.StringIO(stdin))
        return status, json.loads(output.getvalue())

    def test_end_to_end_cli_workflow(self):
        self.invoke(["init", self.temp.name])
        status, appended = self.invoke(
            ["append", self.temp.name, "-", "--no-sync"],
            '{"timestamp":1,"type":"sale","data":{"amount":2}}\n',
        )
        self.assertEqual(status, 0)
        self.assertEqual(appended["appended"], 1)
        _, page = self.invoke(["query", self.temp.name, "--type", "sale"])
        self.assertEqual(page["events"][0]["data"]["amount"], 2)
        _, groups = self.invoke(["aggregate", self.temp.name, "sum", "--value-path", "data.amount"])
        self.assertEqual(groups["groups"], {"all": 2.0})
        _, stats = self.invoke(["stats", self.temp.name])
        self.assertEqual(stats["events"], 1)

    def test_jsonl_reports_the_source_line(self):
        self.invoke(["init", self.temp.name])
        with self.assertRaisesRegex(ValueError, "line 2"):
            self.invoke(["append", self.temp.name, "-"], '{}\nnot-json\n')


if __name__ == "__main__":
    unittest.main()

