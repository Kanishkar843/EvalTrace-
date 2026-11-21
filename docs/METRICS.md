# Evaluators and limitations

- Structured validity: Draft 2020-12 JSON Schema validates the observed structured object; Pydantic validates trace/case shape.
- Tool accuracy: exact ordered equality of tool names and JSON arguments. This does not prove a provider actually executed a claimed tool.
- Recall@5: unique relevant retrieved IDs among the first five divided by all unique relevant IDs. Empty relevance scores zero.
- nDCG@10: binary relevance gain `1/log2(rank+1)` divided by ideal gain. Repeated IDs earn gain only once.
- Citation-reference validity: fraction of declared citation IDs that exist in retrieved documents; no citations scores zero.
- Grounded token overlap: answer-token overlap with cited text, retained for comparison with original runs.
- Citation support: split answer into claims; require at least .8 token coverage in a cited document, containment of claim numbers, and matching presence/absence of negation words. Report each claim and its best coverage. Empty claims/evidence score zero.
- Task completion: completed flag without exception. Exception rate: whether a sanitized exception was recorded.

Claim support is stronger than checking citation existence, but is not semantic entailment. It can miss paraphrases, misread numerical formatting/decimal sentence boundaries, fail on scope/coreference, and accept misleading token overlap. Negation parity is coarse. Human review is required for consequential conclusions. No LLM judge is configured or claimed. Optional provider execution creates an observed trace to evaluate; it is not an independent judge.

Case elapsed_ms is measured wall time around target invocation and evaluation, excluding checkpoint/database overhead. Tokens are reported only when the provider returns nonnegative observed usage; cost remains null. Fixture time measures fixture execution, not LLM latency. Metric version 2 adds claim-support evidence; comparisons reject mismatched metric versions.
