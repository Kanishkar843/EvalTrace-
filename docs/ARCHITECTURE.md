# Architecture and recovery

The React bundle is served by FastAPI on the same origin. Typed dataset registration creates immutable content-hash versions. Queue insertion snapshots policy before a worker claims the job. PostgreSQL uses `FOR UPDATE SKIP LOCKED`; an atomic conditional update is also checked. A random owner ID fences checkpoint/final writes against an expired worker. Each case renews a 90-second lease; bounded adapter attempts last at most roughly 31 seconds before evaluation. Process death leaves the job recoverable after lease expiry. Completed cases are read from PostgreSQL and skipped on recovery.

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> running: atomic claim
    running --> completed: final aggregate transaction
    running --> interrupted: caught interruption
    interrupted --> running: replacement claim
    running --> running: expired lease reclaimed
```

```mermaid
sequenceDiagram
    participant UI as React
    participant API as FastAPI
    participant DB as PostgreSQL
    participant W as Worker
    participant T as Target
    UI->>API: register dataset / queue run
    API->>DB: immutable cases + policy snapshot + job
    W->>DB: claim with lease and owner
    loop remaining cases
        W->>T: bounded typed request
        T-->>W: observed trace or sanitized exception
        W->>W: validate and calculate metrics
        W->>DB: owner-fenced atomic case checkpoint
    end
    W->>DB: aggregate scores and release gate
    UI->>API: poll persisted progress / compare runs
    API->>DB: read evidence and store comparison
    API-->>UI: actual scores and trace evidence
```

Tradeoffs: execution is at least once for an in-flight external call; owner fencing prevents duplicate stored cases, but it cannot undo remote side effects. Targets should be read-only/idempotent. Fixture results are reproducible; hosted model outputs may vary. The queue and API are appropriate for the bounded local studio, not a claim of production-scale reliability. The worker profile is optional; authenticated API stepping uses the same durable engine.
