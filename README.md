# EvalTrace

A dataset-driven evaluation studio with stored traces and reproducible release gates.

**Status: functional native demo, incomplete against the full master prompt.** This repository is original first-party code authored for this assignment. It is not a clone or reskin. No live data, production-readiness, PostgreSQL verification or successful GitHub publishing is claimed.

## Run on Windows

A project-local Python 3.12 virtual environment was created. From PowerShell 7:

```powershell
cd K:\Projects\EvalTrace
$env:ADMIN_TOKEN = Read-Host 'Enter a private local demo token' -MaskInput
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Open http://127.0.0.1:8002. OpenAPI is at `/docs`. For DeltaIndex/EvalTrace, enter the same local token in the UI. Run one application at a time. Stop it with Ctrl+C before starting the next.

Fresh install (dependency resolution and app runs tested; fresh-machine bootstrap not tested):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pytest -q
```

## Implemented

- Validated immutable dataset versions using SHA-256 content identity
- JSON Schema validity, exact tool name/arguments, Recall@5 and nDCG@10
- Citation-reference validity and explicitly heuristic grounded-token overlap
- Fixture and restricted loopback HTTP target adapters; actual measured case duration
- Stored runs, policy snapshots, baseline/candidate comparison and CLI pass/block exit status

## Screenshots

Browser-captured screenshots, if successful, are under `docs/assets/desktop.png`, `light.png` and `mobile.png`. See TEST_REPORT for the actual browser result; these are not design mockups.

## Tests and evidence

Backend: **6 passed in 10.02s (one upstream TestClient deprecation warning)**. Commands: `python -m pytest -q`, `node --check app/static/app.js`. Read [test report](docs/TEST_REPORT.md), [environment report](docs/ENVIRONMENT_REPORT.md), and [architecture](docs/ARCHITECTURE.md).

## Deployment

Native mode uses SQLite explicitly. PostgreSQL is selected with `DATABASE_URL=postgresql+psycopg://...`. Copy `.env.example` to `.env`, choose local secrets and run `docker compose up --build` when Docker Desktop is available. This path is **NOT RUN** on this host. Never use literal sample credentials for a deployment. Services bind only to loopback in Compose.

WSL 2 instructions (NOT RUN; WSL is not installed): install WSL 2 and Docker Desktop with the user's approval, enable Linux containers, open `/mnt/k/Projects/EvalTrace`, and run `docker compose up --build`. Native Windows virtual environments cannot be reused inside Linux; create a Linux venv or use containers.

## Environment

| Variable | Meaning |
|---|---|
| DATABASE_URL | SQLAlchemy database URL; defaults to project-local SQLite demo file |
| ADMIN_TOKEN | Required for protected DeltaIndex/EvalTrace routes; never committed |
| POSTGRES_PASSWORD | Required by Docker Compose |
| EMBEDDING_MODE | DeltaIndex: fixture (default) or sentence-transformers |
| REDIS_URL | DeltaIndex: enable actual Redis cache |
| LOCAL_TARGET_URL | EvalTrace: loopback HTTP endpoint; no remote redirects |

## Limits and remaining acceptance work

- PostgreSQL/Docker integration and CI execution are not verified.
- Citation reference existence and token overlap do not establish entailment; stronger citation-support checks remain to be implemented.
- The compact schema stores case traces in run JSON instead of all normalized tables requested in the master prompt.
- Runs execute synchronously; no durable background queue, crash recovery or live per-case progress.
- No remote provider adapter, LLM judge, token billing observation or retry/backoff.
- Plain JavaScript frontend; no TypeScript/React, dedicated retrieval table or failure taxonomy dashboard.

[Full requested specification](docs/MASTER_PROMPT.md) · [Dependency attribution](docs/DEPENDENCIES_AND_ATTRIBUTION.md) · [Security](docs/SECURITY.md)

Target repository: https://github.com/Kanishkar843/EvalTrace-. Existing remote history was detected. Nothing has been pushed or overwritten. Mandatory offline infrastructure checks must pass before publishing a feature branch. There is intentionally no project LICENSE pending the owner's decision.

Browser check on this Windows host: install `requirements-browser.txt`, then run `python tests/browser_journey.py`. Uses the installed Chrome executable, a temporary synthetic demo database, and one browser context. It starts and stops its own API server.
