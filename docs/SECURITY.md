# Local-studio security boundaries

Operator routes use constant-time comparison against ADMIN_TOKEN; all datasets/traces/policies require it. This shared-secret model is explicitly single-operator and not multi-tenant authentication. Tokens are supplied through headers and are not saved in browser screenshots. The UI stores its token only in component memory.

Remote endpoints are trusted operator configuration, not request-supplied URLs. Local HTTP is loopback-only; remote/provider endpoints require HTTPS without URL credentials, disable redirects, verify TLS, and use bounded attempts/timeouts. The Windows trust store avoids a native SSL initialization issue. Provider failure traces retain exception class only, not credential values or raw response errors.

Typed bounds and JSON Schema validate imported cases/outputs; SQL uses bound parameters. Dataset and provider content is untrusted and is rendered as text by React. Worker leases fence database writes; external calls may execute more than once after process death, so targets should be idempotent and read-only. No tools execute from imported trace declarations. Do not import private datasets into a public repository.

Secrets are ignored and scanned for known local credential values/private-key/token patterns before publication. This is a limited source scan, not a full security audit. Container API runs nonroot and exposes only loopback. No production compliance or definitive grounding guarantee is claimed.
