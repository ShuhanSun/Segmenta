# Human performance run worksheet

This worksheet must be completed by the real engineer; do not ask an assistant to invent the answers.

1. Record `git rev-parse HEAD`, `python3 --version`, operating system, CPU and available memory.
2. Run `./scripts/verify.sh` and paste the final test summary.
3. Run `./scripts/bench.sh --sizes 10000 50000 100000 250000 --repeats 5 --output docs/performance-human-run.json`.
4. Open the JSON and compare throughput and traced memory across sizes. Record any run-to-run spread or unexpected nonlinearity.
5. Choose one real next optimization. Explain which measurement supports the choice and which product contract must not change.
6. After an implementation commit, rerun the identical command and compare before/after values. Keep regressions as well as wins.

Human operator: **pending**

Run date and environment: **pending**

Observed limit in my own words: **pending**

Chosen optimization and why: **pending**

Before/after commit hashes: **pending**

Result file: **pending**

