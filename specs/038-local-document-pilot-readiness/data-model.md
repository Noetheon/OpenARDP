# F038 Data and state

Runtime: existing ContextBundle, ContextEvidenceItem, block/projection provenance, untrusted envelope and artifact handles only; no new persisted model.

Manual pilot: task registry (triplet, real question, exact source versions, arm and run order); attempt records (active work/check/rescue and waiting separately); arm overhead (setup/import/repair/maintenance without double counting); blinded human supporting-span review; decision record with pending/default criteria, effort budget and recurrence evidence. Actual rows live in a private run directory outside Git. Protocol defines fields and transitions.

Decision states follow the normative protocol: `awaiting_real_tasks`, `in_progress`, `pending_review`, `confirmed_limited_go`, or `pause_expansion`. A freeze is a recorded prerequisite, not a separate verdict. Pending review includes pending recurrence evidence. Invalid/missing accounting or methodology is inconclusive, never GO. Historical frozen benchmark results are a separate immutable record.
