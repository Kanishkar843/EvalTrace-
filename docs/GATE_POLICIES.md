# Release policy

Default floors: structured validity 1, exact tool accuracy 1, Recall@5 .8, nDCG@10 .8, citation-reference validity 1, task completion 1. The editor accepts these floors plus citation_support and grounded_token_overlap within [0,1]. Exception rate is not a floor metric. Every queued job snapshots its policy; edits cannot change an existing run's gate.

A completed run passes only if every stored floor passes. Comparison requires identical dataset content hashes and metric versions. The comparison release gate additionally rejects decreases in benefit scores or increases in exception rate (tolerance 1e-9). It stores both deltas and regression names.

CLI baseline target exits 0; the intentionally regressed fixture exits 1. Comparing baseline/candidate IDs exits nonzero for an actual regression or candidate-floor failure. Synthetic baseline/regressed data demonstrates behavior, not production quality. Existing historical gate policies are preserved by migrations.
