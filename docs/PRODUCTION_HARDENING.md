# Production hardening audit — 2026-11-25

Scope: existing application; dedicated branch `feat/production-hardening`. Historical CI and screenshots are not current security acceptance evidence.

## Findings

A shared administrator token protects global data. Worker leases and checkpoints exist, but cancellation, bounded retries, immutable execution configuration, policy history and personal ownership are incomplete.

| Area | Audit classification | Evidence / outstanding work |
|---|---|---|
| Existing React pages and exports | partially implemented | Existing distinct designs preserved; account/settings/error experiences missing |
| Managed account lifecycle | missing | No managed auth configuration found during environment-name inspection |
| Personal authorization | partially implemented | PrefLoom scopes local sessions; DeltaIndex/EvalTrace use a shared operator boundary |
| PostgreSQL persistence | partially implemented | Schema and prior integration reports exist; this hardening branch needs isolated migration and tenancy validation |
| External integrations | partially implemented | Real provider/search implementations exist; quotas and ownership need verification |
| Production readiness | blocked | Managed auth, preview isolation and two-user deployed acceptance not established |

## Trust boundaries and architecture

Browser input and model output are untrusted. API identity must come from a managed provider, never client ownership claims. Database and provider credentials stay server-side. Each application retains a separate database and account realm. Managed Neon Better Auth is the proposed provider matching existing infrastructure; provisioning and SDK integration remain pending. A configured Auth URL alone is not authentication verification.

Preview databases and provider configuration must be separate from production. Do not deploy this branch to production while acceptance gaps remain. No production data migration or deletion is authorized by this report.

## Implementation order

1. Close anonymous costly access; enforce request bounds and private cache controls.
2. Integrate managed sessions and lifecycle screens, validate revocation and callbacks.
3. Add additive ownership migrations and server-side authorization to all resources, caches and jobs.
4. Implement project-specific approval/ingestion/evaluation state guarantees and distributed quotas.
5. Validate isolated PostgreSQL, two-user browser journeys, preview environment and recovery.
6. Record dependency/security checks, operational evidence, rollout and rollback instructions; open reviewable PR.

## Permission target (not yet fully implemented)

Public visitors: landing only. Authenticated owners: own records, exports and operations within quotas. Operators: explicitly granted maintenance actions, without implicit access to private user data. Deny unknown roles and resources. No collaboration roles are needed for the present personal-user product.

## Deployment hold

Current live deployment is unchanged. No new security claim is made for it. Production rollout requires the managed-provider lifecycle, cross-user isolation, quota controls and deployed acceptance tests to pass. Backup availability, restore exercises and alerts are unverified.
