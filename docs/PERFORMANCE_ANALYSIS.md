# Performance scale analysis

## What was measured

The checked-in raw result is `performance-agent-baseline.json`. It was produced on 2026-09-18 with Python 3.12.14 on Linux. Each point has one warm-up, three timed repeats, and a separate `tracemalloc` memory run. Three repeats are enough for a development baseline but not enough to treat p95/p99 as production percentiles; with three samples those fields are effectively the slowest observed run.

The append measurement excludes store creation and uses `sync=False`, so it represents bulk ingestion rather than durable one-batch latency. Query scans all input and selects the rare event type. Aggregation performs grouped sum. Compaction rewrites a prepared store while retaining its newer half; setup is outside the timer.

## Agent-run scale results

| Path | 10k p50 / rate | 50k p50 / rate | 100k p50 / rate | 250k p50 / rate |
|---|---:|---:|---:|---:|
| F1 append, no fsync | 110.5 ms / 90.5k/s | 562.6 ms / 88.9k/s | 1169.2 ms / 85.5k/s | 3073.3 ms / 81.3k/s |
| F2 filtered full scan | 77.5 ms / 129.1k/s | 403.9 ms / 123.8k/s | 780.2 ms / 128.2k/s | 1981.8 ms / 126.1k/s |
| F3 grouped sum | 98.6 ms / 101.4k/s | 532.0 ms / 94.0k/s | 996.3 ms / 100.4k/s | 2496.2 ms / 100.2k/s |
| F4 retention compaction | 105.4 ms / 94.9k/s | 531.4 ms / 94.1k/s | 1044.2 ms / 95.8k/s | 2624.0 ms / 95.3k/s |

Throughput stays within roughly 10% across a 25× scale increase, so no path shows a superlinear collapse in this range. Query, aggregation, and compaction are intentionally streaming and show less than 1 MB of traced transient memory at 250k events. F1 append is the clear scalability limit: traced peak rises from 3.6 MB at 10k to 36.2 MB at 100k and 90.8 MB at 250k because the API first materializes validated `Event` objects and then a second list of encoded frames.

## Real optimization headroom

The highest-value task is bounded-memory atomic validation. Encoding into a temporary spool while validating, then copying the validated spool under the write lock, preserves “invalid batch writes nothing” without retaining all frames in RAM. A naive generator rewrite would lower memory but silently break that contract if a late event is invalid.

The second task is segment-level pruning. Query and aggregation currently deserialize every JSON frame. Per-segment timestamp min/max, event-type summaries or bloom filters, plus sparse offsets would let selective queries skip most bytes. After that, fused field extraction or parallel independent segment scans can improve CPU throughput. Compaction can use larger buffered writes and parallel decode/encode, while preserving output order.

## Agent limit and failure analysis

The development Agent successfully produced a coherent multi-module baseline, feature mapping, measurement harness, and scale run. The first correctness run nevertheless exposed a batch-rotation bug: the initial append implementation chose one segment before the loop, so a large batch ignored the configured segment size. Tests caught it and commit `496cda7` fixed rotation inside the batch. This is evidence that generation alone is not reliable; feature tests found a boundary error that a happy-path smoke check missed.

The Agent also needed to correct its first benchmark design. It initially included `stats()` full scanning in append time and included store setup in compaction time. Those numbers would have mislabeled mixed work as feature latency. The checked-in harness separates setup, timed operation, warm-up and memory measurement. Remaining limits are explicit: no fsync latency distribution, only one machine, three repeats in the checked-in scale run, no concurrent readers/writers, and no dataset wider than 250k events.

The first clean-install attempt found another Agent oversight: `pip --no-build-isolation` still required `setuptools`, which a fresh Python 3.12 virtual environment did not contain. Because the target is offline, fetching the backend would violate the environment contract. The final repository includes `scripts/install.py`, a standard-library-only installer, and `scripts/clean_verify.sh` now validates that path in a new virtual environment.

## Human performance run status

No human-operated performance run has occurred yet. `HUMAN_PERFORMANCE_WORKSHEET.md` defines the required procedure without inventing results. Until a real person runs it, records observations, and decides which bottleneck matters, this package does not satisfy the requested “human + agent” performance evidence.
