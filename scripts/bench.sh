#!/usr/bin/env sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"
PYTHONPATH=src:. python3 tests/perf/run_matrix.py "$@"

