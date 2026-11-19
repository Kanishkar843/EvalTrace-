# Workflows

1. Validated immutable dataset versions using SHA-256 content identity.
2. JSON Schema validity, exact tool name/arguments, Recall@5 and nDCG@10.
3. Citation-reference validity and explicitly heuristic grounded-token overlap.
4. Fixture and restricted loopback HTTP target adapters; actual measured case duration.
5. Stored runs, policy snapshots, baseline/candidate comparison and CLI pass/block exit status.

```mermaid
sequenceDiagram
participant User
participant UI
participant API
participant DB
User->>UI: Submit validated input
UI->>API: Request
API->>DB: Read or transaction
DB-->>API: Stored evidence
API-->>UI: Actual result or explicit error
UI-->>User: Inspect evidence
```

The full acceptance workflow remains in MASTER_PROMPT.md. A native success does not establish Docker, cloud or provider success.
