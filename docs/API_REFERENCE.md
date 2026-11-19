# API reference

Open `/docs` for generated parameter and response contracts.

- `/health`
- `GET/POST /datasets`
- `POST /datasets/seed`
- `GET /suites`
- `GET/POST /runs`
- `GET /runs/{id}`
- `GET /runs/{id}/cases`
- `GET /traces`
- `POST /compare`
- `GET/PUT /gates`

Protected routes use `Authorization: Bearer <local-token>`. PrefLoom creates opaque demo session tokens at POST /sessions and scopes data by the authenticated user. DeltaIndex/EvalTrace are single-operator local tools using ADMIN_TOKEN, not multi-tenant services. Never put credentials in query parameters.
