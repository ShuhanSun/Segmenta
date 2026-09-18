# Segmenta — Coding Agent Work Trace Store

## Document Information

- Product owner: Shuhan Sun
- Applicable version: `v0.1.0` and subsequent product-scope updates

## Product Purpose

Segmenta provides one storage and query tool for multi-turn development work that is otherwise scattered across agents, platforms, and conversations. Chat records remain isolated in their respective platforms, while Git primarily preserves code results. Neither source alone explains how a requirement was introduced, what an agent attempted, why the code changed, why a test failed, or how the failure was corrected.

Segmenta is intended to preserve the full development trail: user requests, agent responses, tool calls, code changes, test results, performance measurements, and errors. Users can retrieve records by project and topic, with offline approximate search planned for queries that do not exactly match stored keywords.

The current repository implements the underlying event store first. An upper layer can represent every message, tool call, test, or commit as a structured JSON event and store fields such as `project`, `topic`, `session_id`, `agent`, `role`, `text`, and `commit` inside `data`. Agent-specific importers, offline hybrid search, and automatic redaction are planned features and are not presented as implemented in the current release.

## Current Core Features

### F1. Reliable Development Event Storage

A caller can append one event or a batch of events. Every event must contain a timestamp, type, and JSON data object. Segmenta validates the complete batch before writing it. If any event is invalid, no prefix of that batch is written. Events without IDs receive generated IDs, and append order is preserved.

Data is divided into size-bounded segment files. Each record contains a CRC32 checksum used to detect incomplete writes or file corruption. A normal read fails explicitly when corruption is found. Repair mode truncates only the tail beginning at the first damaged frame and leaves previously verified records unchanged.

### F2. Filtered Queries and Cursor Pagination

Users can apply exact filters by event type, time range, and fields inside `data`, such as a project, session, agent, or test status. Results are returned in original append order.

Large result sets use cursor pagination with a maximum of 10,000 events per page. A cursor can continue only the query that created it. Compaction changes physical file positions, so cursors issued before compaction are not guaranteed to remain valid.

The current release implements exact field filtering only. The planned project-and-topic query capability will use offline hybrid search based on keywords, spelling similarity, and relevance ranking. It will not require an external language model, account, network service, or bundled model weights.

### F3. Coding Agent Trace Aggregation

Users can run `count`, `sum`, `min`, `max`, and `avg` operations and group results by event type or a field inside `data`. Example uses include counting tool calls per agent, counting failed tests per project, and calculating average task duration.

Aggregation runs as a sequential stream and does not load every event into memory simultaneously. Numeric aggregation skips missing values, booleans, and nonnumeric content. Every operation except `count` requires a numeric value path.

### F4. Data Retention and File Compaction

Users can rewrite segment files and optionally provide a retention timestamp that discards older events. Retained event contents, IDs, and order remain unchanged. The operation reports event counts and file sizes before and after compaction.

Compaction blocks writers while it runs. The current release does not provide multi-node replication and does not guarantee database-level snapshot consistency between concurrent readers and compaction.

### F5. Local Command-Line Workflow

The command-line interface provides `init`, `append`, `query`, `aggregate`, `compact`, `recover`, and `stats`. Events are accepted as JSON Lines, and commands return JSON so different agents and scripts can integrate without custom parsing.

Invalid JSON reports its source line number, and failed commands exit with a nonzero status. The core workflow runs locally without a network connection, account, paid API, GPU, or model weights.

## Next-stage Features

The following product directions are defined but are not current, implemented core features:

1. Define standard event structures for agent sessions, messages, tool calls, file modifications, test results, and Git commits.
2. Import records across agents, conversations, and projects while preserving source metadata.
3. Query by project and topic with offline hybrid search combining keywords, spelling similarity, and relevance ranking.
4. Detect common tokens, email addresses, and local machine paths during import and redact them before storage.
5. Connect one requirement, multiple conversations, code commits, and test results into a replayable work trail.

Before any item moves into the current core feature set, it must have a corresponding implementation, correctness tests, and applicable performance measurements.

## Architecture

`models.py` defines the event structure and input boundaries. `codec.py` encodes events into compact JSON frames with CRC checksums. `storage.py` manages directories, write locking, segment rotation, sequential reads, and recovery. `query.py` applies filters and cursor pagination. `aggregate.py` performs streaming grouped aggregation. `lifecycle.py` manages retention and compaction. `cli.py` parses command-line input and calls the same library interfaces.

The write path is: agent or importer → event validation → JSON frame encoding → file lock → segment file. The read path is: segment file → CRC and JSON decoding → conditional filtering → pagination or aggregation.

The system currently runs as a single Python process. Multiple processes may submit writes concurrently, and a file lock prevents their frames from interleaving. Segmenta is not a network database and has no background service.

## Testing and Performance

The correctness and performance test mapping for F1–F5 is documented in `tests/FEATURE_MAP.md`. Run the complete correctness suite with `./scripts/verify.sh`. Validate installation in a clean virtual environment with `./scripts/clean_verify.sh`.

Run performance measurements with `./scripts/bench.sh`. The benchmark reports mean, p50, p95, and p99 latency, throughput, and traced memory without imposing an arbitrary binary latency threshold. The primary current limitation is that batch append holds both event objects and encoded frames, causing memory to grow with batch size. Queries and aggregations still scan and decode every relevant segment. Future optimization options include a temporary spool, segment metadata, and sparse indexes.

## Running the Project

```bash
python3 -m venv .venv
.venv/bin/python scripts/install.py
./scripts/verify.sh
./scripts/clean_verify.sh
./scripts/bench.sh --sizes 10000 50000 100000 --repeats 5
```

## Out of Scope

The current release does not provide a network API, SQL, user authentication, multi-node replication, encrypted storage, cloud backup, or general natural-language semantic understanding. CRC checks detect accidental corruption; they do not prevent malicious tampering. Automatic redaction is not implemented yet, so private source data must be redacted before import.
