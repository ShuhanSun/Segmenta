# Segmenta

Segmenta is a small embedded event store for local tools and services that need
durable JSON events, deterministic recovery, filtered reads, aggregation, and
retention without a database server.

It runs on Python 3.11+ and has no runtime dependencies outside the standard
library.

```bash
.venv/bin/python scripts/install.py
segmenta init ./demo-store
printf '%s\n' '{"timestamp":1,"type":"login","data":{"user":"u1"}}' | \
  segmenta append ./demo-store -
segmenta query ./demo-store --type login
```

See `PRD.md`, `tests/FEATURE_MAP.md`, and `META.yaml` for the product contract,
feature-level verification, and reproducibility metadata.

## Verification

```bash
./scripts/verify.sh
./scripts/clean_verify.sh
./scripts/bench.sh --sizes 10000 50000 100000 --repeats 5
```

`clean_verify.sh` copies the snapshot to a temporary directory, installs it in
a fresh virtual environment, runs every feature test, and exercises the
installed CLI. The benchmark writes concrete latency, throughput, and memory
measurements; it does not turn them into an arbitrary pass/fail threshold.

The standard-library installer is the reproducible offline path. Environments
that already provide setuptools may alternatively use
`python -m pip install --no-deps --no-build-isolation .`.
