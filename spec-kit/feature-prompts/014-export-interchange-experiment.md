# Feature 014 — Export/interchange experiment

## Goal
Determine whether RO-Crate, OCFL, BagIt or a minimal project archive can satisfy real exchange needs without a universal `.ardp` claim.

## Requirements
Decision ADR and test vectors. Export records contract versions, integrity inventory, source/reference policy, native assets only when licensed/permitted, projections, derivations and trust labels; excludes secrets and absolute paths. Import verifies before publication, limits expansion/count/size, rejects traversal/digest conflict and preserves or rejects extensions by declared policy. Imported content remains untrusted. A “no custom format” conclusion is valid.
