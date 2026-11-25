# API reference

`/docs` and `/openapi.json` provide generated contracts. `/health` and `/ready` are public. All dataset, run, worker, comparison, trace and policy endpoints require `Authorization: Bearer <ADMIN_TOKEN>`. No credentials in query strings.

| Endpoint | Behavior |
|---|---|
| GET /datasets or /suites | List immutable dataset versions |
| POST /datasets | Register typed name/cases |
| POST /datasets/import | Register name/content JSONL |
| POST /datasets/seed | Register synthetic baseline/regressed suite |
| GET /datasets/{id}/cases | Inspect original typed cases |
| GET /runs | Latest 100 stored runs |
| POST /runs | Synchronous convenience execution through durable engine |
| POST /runs/queue | Persist a queued job and policy snapshot |
| POST /workers/step | Claim and process one eligible job |
| GET /runs/{id} | Actual stored progress and completed result |
| GET /runs/{id}/cases | Per-case trace/score/failure evidence |
| GET /traces?run_id=... | Equivalent trace inspection |
| POST /compare | Store matching-version score deltas and relative release gate |
| GET/PUT /gates | Inspect/edit future-run floors |

Run request: `{ "dataset_id": "...", "target": "fixture-baseline" }`. Comparison: `{ "baseline": "...", "candidate": "..." }`. Policy: `{ "recall_at_5": 0.8, "citation_support": 0.8 }`. Unknown/invalid inputs return 422; missing identities return 404; missing operator configuration returns 503; incorrect authentication returns 401. Existing synchronous run endpoints remain compatible while queued execution enables durable recovery.
