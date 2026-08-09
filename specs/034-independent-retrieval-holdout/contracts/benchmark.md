# Retrieval Holdout v0.1.0 Maintainer Contract

- Inputs are the committed `corpora/retrieval-holdout/v0.1.0` and
  `benchmarks/retrieval-holdout/v0.1.0` identities.
- Generation requires the exact pinned XQuAD files and never overwrites an output.
- Runtime requires an explicit reviewed E5 bundle, performs no network access and changes no product state outside fresh
  temporary workspaces.
- A valid below-target result exits successfully and remains publishable.
- Output inventory is `observations.json`, `summary.json`, `decision.json`, `report.md`, `run-manifest.json`.
- Results contain no source/question/answer bodies, paths, hostnames or usernames.
- Stable failures are `holdout_input_rejected`, `holdout_execution_failed`, `holdout_evidence_invalid`,
  `holdout_output_conflict` and `holdout_drift_detected`.
