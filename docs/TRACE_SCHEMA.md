# Trace schema

Pydantic Trace requires answer text and structured JSON. It accepts bounded tool calls (name + arguments), retrieved documents (ID + text), citation IDs, completion flag and optional exception class. Case includes expected tool calls, relevant document IDs, JSON Schema, baseline fixture and regressed fixture. See data/suite.jsonl for actual input examples.

The engine validates all cases and schemas before storing an immutable dataset version. Each run stores the dataset hash, target, metric version, policy snapshot, observed trace, calculated scores and measured duration. The compact initial implementation stores case data in run JSON rather than the normalized entity model requested in MASTER_PROMPT. No LLM judge, provider cost or token count is synthesized.
