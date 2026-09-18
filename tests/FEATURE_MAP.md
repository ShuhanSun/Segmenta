# Feature verification map

All correctness commands are deterministic. Performance commands measure and report values; they intentionally contain no pass/fail latency threshold.

| PRD feature | Correctness test | Performance measurement | Command |
|---|---|---|---|
| F1 Batch append, segmentation, recovery | `tests/features/f1_append_recovery/test_correctness.py` | `tests/features/f1_append_recovery/perf.py` | `PYTHONPATH=src:. python3 -m unittest tests.features.f1_append_recovery.test_correctness`; `PYTHONPATH=src:. python3 tests/features/f1_append_recovery/perf.py` |
| F2 Filtered query and cursor pagination | `tests/features/f2_query_pagination/test_correctness.py` | `tests/features/f2_query_pagination/perf.py` | `PYTHONPATH=src:. python3 -m unittest tests.features.f2_query_pagination.test_correctness`; `PYTHONPATH=src:. python3 tests/features/f2_query_pagination/perf.py` |
| F3 Streaming grouped aggregation | `tests/features/f3_aggregation/test_correctness.py` | `tests/features/f3_aggregation/perf.py` | `PYTHONPATH=src:. python3 -m unittest tests.features.f3_aggregation.test_correctness`; `PYTHONPATH=src:. python3 tests/features/f3_aggregation/perf.py` |
| F4 Compaction and timestamp retention | `tests/features/f4_compaction_retention/test_correctness.py` | `tests/features/f4_compaction_retention/perf.py` | `PYTHONPATH=src:. python3 -m unittest tests.features.f4_compaction_retention.test_correctness`; `PYTHONPATH=src:. python3 tests/features/f4_compaction_retention/perf.py` |
| F5 Complete CLI workflow | `tests/features/f5_cli/test_correctness.py` | Not separate: CLI is orchestration; underlying data paths are measured in F1–F4 | `PYTHONPATH=src:. python3 -m unittest tests.features.f5_cli.test_correctness` |

Run every correctness test with `./scripts/verify.sh`. Run the repeatable scale matrix with `./scripts/bench.sh`; results are printed and written as JSON.

