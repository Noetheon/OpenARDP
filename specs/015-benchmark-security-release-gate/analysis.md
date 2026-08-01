# Convergence Analysis: Benchmark, Security and v0.1 Release Gate

## Scope reviewed

The review compares the constitution, repository instructions, F015 specification,
plan, contracts, checklists and tasks against code, tests, generated schema/corpus/SBOM/
evidence, CLI behavior, documentation and CI. Persisted workspace formats and prior
public contract bytes remain outside the feature change.

## Convergence finding summary

The first implementation pass exposed seven real gaps: incomplete lifecycle and quality
measurements, narrow hostile coverage, caller-asserted suite passes, unintegrated privacy
and recovery evidence, absent executable upgrade reproduction and an all-unavailable
committed bundle. T091-T097 close those gaps with bound raw identities, exact required
check registries, broader frozen controls, actual artifact/install/recovery execution and
one immutable local reference capture. No critical or high contradiction remains. The
binding result stays intentionally `NO-GO`; final full gates and remote CI remain before
merge.

A final post-hardening convergence pass rechecked all 35 functional requirements,
12 success criteria, the constitution, plan, contracts, both completed checklists and
all 97 completed tasks against the generated artifacts and executable tests. It found
no remaining critical, high or actionable medium inconsistency. Remote three-platform
evidence remains the publication step, not an unresolved implementation contradiction.

## Requirement trace

- Fair baselines, 4,222 identity-bound raw outcomes and exact corpus: benchmark
  adapter/service and frozen corpus registry.
- Mechanical judgments and uncertainty: release-gate scoring/statistics and focused
  correctness tests.
- Security/privacy: closed JUnit-backed manifest, five hostile surfaces, five canary
  classes and negative boundary tests.
- Dependency/artifact/reproduction: explicit component review state, normalized SBOM,
  bounded archive inspector, clean offline install and executable prior-open,
  migration/backup/restore evidence.
- Decision/report/claims: release domain/schema, immutable evidence store, gate service,
  three CLI commands and generated release directory.

## Invariants challenged

- Missing evidence yields a failed check and cannot disappear from blockers.
- Unknown check IDs and passed checks without evidence identities cannot satisfy a suite.
- There is no waiver field in the policy/model and no force/ignore CLI option.
- Generated output and Git metadata cannot enter the candidate source-tree identity.
- Source/document bodies, hostnames, usernames and absolute paths do not enter committed
  evidence.
- `NO-GO` leaves the candidate at `0.1.0rc1`; no tag/release/publication action exists.

## Remaining non-blocking risk

The evidence machinery is capable of a synthetic complete `GO` test, but the committed
real candidate remains `NO-GO` until independent missing evidence is produced. This is
the required fail-closed outcome and does not block merging the gate capability itself.
