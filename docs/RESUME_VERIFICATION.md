# Resume claim verification

| Claim | Implementation | Evidence |
|---|---|---|
| Dataset-driven evaluation harness | immutable typed JSONL/cases, adapters, engine | unit tests, React import and execution journey |
| Tool and structured-output correctness | ordered exact tool comparison, Pydantic and JSON Schema | manually checked fixtures and invalid-schema/tool cases |
| Retrieval relevance and grounded quality | Recall@5, duplicate-aware nDCG@10, citation references and claim support | hand-calculated metric tests; numerical/negation failures |
| Regression and failure cases | policy snapshots, stored deltas, relative release gate, CLI exits | baseline pass and deliberate regression block |
| Durable API reliability | PostgreSQL checkpoints, leases and owner fencing | real killed-worker recovery and concurrent claim test |
| Docker reproducibility | nonroot API, database health, startup migrations | see current TEST_REPORT and docker-test-output.txt |

Real Groq execution and 2,318 observed tokens are recorded in production-provider-result.json; the tested provider target failed its quality gate (structured validity 2/3, tool accuracy 0). No production reliability, semantic-entailment judge or unobserved cost measurement is claimed. Screenshots are from the actual React application with synthetic fixtures.
