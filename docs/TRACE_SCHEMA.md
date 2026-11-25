# Typed trace contracts

Case fields: id, prompt, relevant_ids, expected_tools, output_schema, fixture and regressed_fixture. Import JSONL with one full case per line; duplicate IDs, corrupt lines, invalid JSON Schema, empty suites and more than 100 cases are rejected.

Trace fields: answer, structured object, ordered tools (name/arguments), ordered retrieved documents (id/text), citation ID list, completed flag and optional exception. Pydantic rejects unknown top-level fields and bounds strings/list sizes. Each stored case adds measured elapsed_ms, scores, failure taxonomy, grounding evidence, observed tokens, metric_version=2, prompt_version=trace-v1 and adapter/model identity. Dataset SHA-256 is calculated after typed normalization; it is independent from the generated dataset ID.

HTTP targets must return this trace directly. The optional chat-completions provider returns schema-constrained trace JSON using supplied fixture evidence as context. This provider adapter does not implement a separate live retrieval system and never credits tool calls as verified execution. Exact tool correctness evaluates reported trace content only. Provider execution is unverified without credentials; transport tests are labeled mocks.
