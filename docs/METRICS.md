# Metric definitions and limitations

- Structured validity: JSON Schema validation of actual structured output.
- Tool accuracy: exact ordered equality of tool names and JSON arguments against ground truth.
- Recall@5: unique relevant IDs in first five retrieved positions / total unique relevant IDs; zero when no relevant documents exist.
- nDCG@10: binary relevance gain discounted by log2(rank+1), divided by ideal gain; repeated IDs gain only once; zero for empty relevance.
- Citation reference validity: fraction of citation IDs present in retrieved documents. This checks identity, not semantic support.
- Grounded token overlap: unique lowercase alphanumeric answer tokens occurring in cited document text / unique answer tokens. This is a weak lexical heuristic, not entailment or hallucination detection.
- Task completion: declared completed and no exception. Exception rate: observed adapter exception fraction.

Case duration is measured with perf_counter, including adapter and scoring execution. Fixture timing is not a model latency benchmark. Tokens and costs are null because they were not observed. No judge scores are fabricated.
