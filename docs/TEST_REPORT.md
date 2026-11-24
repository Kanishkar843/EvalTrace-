# Executed acceptance report

Updated 2026-11-22. This supersedes the initial native/static demo report.

| Command/check | Actual result |
|---|---|
| `python -m pytest -q tests` | PASS: 14 tests, 4.67 seconds |
| `python -m pytest -q integration` | PASS: 1 real PostgreSQL recovery/concurrency test, 4.87 seconds |
| TypeScript typecheck / ESLint | PASS |
| Vitest | PASS: 2 tests |
| Vite production build | PASS |
| Ruff selected correctness rules | PASS |
| React Chrome browser journey | PASS; desktop/light/mobile captured |
| Docker image build / Compose readiness | PASS |
| Docker queued-run restart persistence | PASS |
| Docker baseline / regressed evaluation / comparison | PASS; intentional regression correctly blocked |
| CLI baseline / regressed exit codes | PASS: 0 / 1, verified natively and inside Docker |
| Live provider / configured remote endpoint | BLOCKED: no credentials/configured service; transport test is mocked |
| GitHub CI/publication | Feature branch and PR published; Actions verification in progress |

Real PostgreSQL test: apply frozen migrations, queue a run, start an owned subprocess, kill it while the second case is in flight after the first checkpoint, accelerate the 90-second lease deadline, recover using a new Engine, verify exactly one stored output per case, reproduce scores, compare a deliberate regression, and race two workers for one job. Actual worker death is not simulated; lease time is shortened for test speed. PostgreSQL is 17.12. Native SQLite tests are listed separately.

Browser tests exercise unauthorized access, suite registration, durable run launch, baseline pass, deliberately blocked regression, stored comparison, failed tools/citation evidence, policy editing, invalid and valid JSONL imports, and responsive dark/light themes. No page errors or horizontal mobile overflow. Screenshots are actual UI captures under docs/assets. An initial selector failure exposed ambiguous comparison labels; explicit accessible labels corrected it before the passing run.

One upstream Starlette warning reports deprecation of its HTTPX TestClient integration; tests pass. The initial test invocation used the wrong working directory and failed collection; rerunning from the documented project root resolved it. No failed run is counted as a passing test. Live-provider usage/cost is not invented; fixture durations are not LLM latency benchmarks. docker-test-output.txt and postgres-test-output.txt preserve service evidence.

Published branch: `feat/durable-evaluation-react`; [PR](https://github.com/Kanishkar843/EvalTrace-/pull/1), [Actions](https://github.com/Kanishkar843/EvalTrace-/actions). Existing remote main is an ancestor of the delivered branch. No force push or main overwrite occurred.

## Production verification — 2026-11-24

See [CLOUD_DELIVERY](CLOUD_DELIVERY.md) for actual Vercel, Neon, provider, browser and model results. Earlier local results above retain their original scope.
