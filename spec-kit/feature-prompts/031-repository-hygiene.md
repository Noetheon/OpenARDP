# F031 — Repository Hygiene and Bounded Refactoring

## Intent

Recover a trustworthy repository state after local synchronization conflicts, encode deterministic prevention, and
reduce selected measured function-level complexity without changing runtime contracts, persisted identities or storage
architecture.

## Required evidence

- Pre-clean classification of every candidate and post-clean zero-finding audit.
- Test-first equivalence evidence for each selected hotspot.
- Before/after maintainability measurements and all ten F031 quality gates.
- Full local and three-platform repository gates before normal merge.

## Boundaries

- Detection is read-only; cleanup is a one-time explicitly reviewed operation.
- Ambiguous or newer files are preserved.
- No SQLite rewrite, contract migration, new framework, runtime dependency or automatic deletion.
- “10/10” means all ten measurable F031 gates pass, with residual debt reported honestly.
