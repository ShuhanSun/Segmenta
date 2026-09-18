# Segmenta

Segmenta is a small embedded event store for local tools and services that need
durable JSON events, deterministic recovery, filtered reads, aggregation, and
retention without a database server.

It runs on Python 3.11+ and has no runtime dependencies outside the standard
library.

```bash
python -m pip install --no-deps .
segmenta init ./demo-store
printf '%s\n' '{"timestamp":1,"type":"login","data":{"user":"u1"}}' | \
  segmenta append ./demo-store -
segmenta query ./demo-store --type login
```

See `PRD.md`, `tests/FEATURE_MAP.md`, and `META.yaml` for the product contract,
feature-level verification, and reproducibility metadata.

