#!/usr/bin/env sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

mkdir "$work_dir/source"
tar -C "$repo_dir" --exclude=.git --exclude=.venv --exclude=perf-results -cf - . | tar -C "$work_dir/source" -xf -
python3 -m venv "$work_dir/venv"
"$work_dir/venv/bin/python" "$work_dir/source/scripts/install.py"
cd "$work_dir/source"
PATH="$work_dir/venv/bin:$PATH" ./scripts/verify.sh

store="$work_dir/store"
"$work_dir/venv/bin/segmenta" init "$store" >/dev/null
printf '%s\n' '{"timestamp":1,"type":"clean-check","data":{"ok":true}}' | \
  "$work_dir/venv/bin/segmenta" append "$store" - --no-sync >/dev/null
"$work_dir/venv/bin/segmenta" stats "$store"
