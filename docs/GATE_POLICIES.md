# Regression gates

Default floors: structured validity=1, tool accuracy=1, Recall@5=0.8, nDCG@10=0.8, citation-reference validity=1, completion=1. All floors must pass. A policy snapshot is stored with each run; editing policy cannot rewrite past decisions. Comparisons require the same immutable dataset version.

Executed commands:
- `python -m app.cli --target fixture-baseline`: exit 0, gate passes.
- `python -m app.cli --target fixture-regressed`: exit 1, gate blocks as expected.

Actual outputs are gate-baseline.json and gate-regressed.json. The deliberately regressed fixture is an expected release rejection, not a software test failure. Missing required metrics fail floors through the gate function; an empty policy is rejected at the API.
