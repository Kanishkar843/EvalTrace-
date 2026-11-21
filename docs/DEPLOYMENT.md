# Windows and Docker setup

Use Python 3.12, Node 22 and one project stack at a time. Install requirements.lock and frontend/package-lock.json dependencies; build the React bundle, then start Uvicorn on loopback port 8002. Set ADMIN_TOKEN in the current PowerShell environment. PowerShell 5.1 users can assign a locally generated secret; `Read-Host -MaskInput` is not required. Native default is an explicitly labeled SQLite demo.

Set DATABASE_URL for PostgreSQL and apply `python -m alembic upgrade head`. Start `python -m app.worker` for continuous execution, or use authenticated UI worker stepping. A worker never creates deployed schemas on startup; migrations run first. A crashed worker's pending case can repeat after its 90-second lease expires; committed checkpoints are retained.

```powershell
docker compose up --build -d --wait
$env:ACCEPTANCE_URL='http://127.0.0.1:8002'
$env:COMPOSE_PROJECT_NAME='evaltrace'
python tests/compose_acceptance.py
docker compose down
```

Set the same COMPOSE_PROJECT_NAME before startup/testing. Use an isolated project for acceptance: it creates fixture evidence and restarts only its API. Set POSTGRES_PASSWORD and ADMIN_TOKEN before Compose. To enable the continuous worker: `docker compose --profile worker up -d`. Default API/database Compose acceptance passed; the optional separate worker service is not separately claimed as tested. Actual worker process recovery is verified against PostgreSQL by integration/test_postgres.py.

Images use a nonroot API user. PostgreSQL and API are limited to 512MB each; optional worker 384MB. PostgreSQL has no exposed host port. Compose runs Alembic before API startup. Keep volumes by omitting `down -v`. WSL/Docker were installed with authorization; no automatic Windows restart or security-policy bypass. Enterprise CA roots can be supplied externally with BUILD_CA_FILE and compose.trust.yaml during build; never disable TLS or commit private trust material.

Live endpoints are optional. LOCAL_TARGET_URL must be loopback HTTP. REMOTE_TARGET_URL and LLM_BASE_URL require HTTPS; redirects are disabled. Credentials are environment-only. HTTP retries and timeouts are bounded. Cost remains unreported unless a separately implemented trustworthy cost source exists; current code reports null. See SECURITY and METRICS for limitations.
