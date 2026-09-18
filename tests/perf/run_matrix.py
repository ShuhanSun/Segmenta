from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from tests.perf.benchmark import BENCHMARKS, run_one


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Segmenta performance scale matrix")
    parser.add_argument("--sizes", type=int, nargs="+", default=[1_000, 10_000, 50_000])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", default="perf-results/latest.json")
    args = parser.parse_args()

    results = []
    for size in args.sizes:
        for name in BENCHMARKS:
            result = run_one(name, size, args.repeats)
            results.append(result)
            print(
                f"{result['benchmark']} n={size} p50={result['latency_ms']['p50']}ms "
                f"rate={result['throughput_events_per_sec']} events/s",
                flush=True,
            )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor() or "not reported",
        },
        "method": {"warmups": 1, "repeats": args.repeats, "fsync_in_append": False},
        "results": results,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

