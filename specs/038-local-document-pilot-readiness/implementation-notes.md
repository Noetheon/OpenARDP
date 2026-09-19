# F038 implementation notes

Risk tier: high-assurance. Acceptance: explicit readable source-backed bundles, unchanged default/JSON and retrieval, a verified practical guide, a preregisterable manual three-arm pilot with pending judgments and no invented evidence, a bounded GO/pause decision, canonical focus freeze and full quality gates. Implementation in progress. F037 merged with all platform checks green before this branch began.

No new dependency, persisted format, public schema or architectural ADR trigger. Decisions, test-first results, smoke evidence, independent reviews, compaction and exact gates will be recorded here.

## Pre-implementation analysis corrections

Independent analysis reproduced that the existing human `safe_text` helper retains DEL, C1 and bidi controls, conflicting with the proposed broad output guarantee. Scope was explicitly amended before implementation for narrowly enumerated shared escaping (C0/DEL/C1 plus U+061C, U+200E–U+200F, U+202A–U+202E and U+2066–U+2069), with normal Unicode/umlaut preservation and focused tests. JSON and stored evidence remain unchanged. Manual verdict state names were aligned with the normative protocol. Multiple submitted final outputs now have an exact Q/S selection rule; earlier source/version incidents still block GO, and assigned-attempt retries cannot reset the 20-minute cumulative task cap.

Independent recheck closed all three findings: 8 FR and 4 SC mapped to 10 tasks, zero unresolved critical/high/medium findings. Full specify/clarify/plan/checklist/tasks/analyze completed before runtime/template changes.
