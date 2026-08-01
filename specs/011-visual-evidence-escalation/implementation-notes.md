# Implementation Notes: F011 Visual Evidence Escalation

## Acceptance-criteria reconciliation

1. Materialize only an accepted F006/F007 target bound to exact source, READY rich
   representation and verified CAS/native/projection facts.
2. Preserve source authority; page rasters/crops are reproducible derived evidence and
   OCR/captions remain separate model-derived untrusted interpretations.
3. Use one thin experimental descriptor and exact RFC 8785/SHA-256 identity without
   changing existing F006/F008/F009 contracts or creating a complete page model.
4. Resolve page/picture/table/cell regions only from accepted anchors and retained
   native facts; geometry inference is prohibited and coarse table fallback is labelled.
5. Render/crop explicitly through an optional local PDF worker with fixed deterministic
   profile, network denial, kill/reap cleanup and independent resource limits.
6. Reuse canonical page rasters across crops; publish page/crop/descriptor CAS objects
   before one idempotent transactional revision-8 catalog commit.
7. Select only verified current descriptor handles in ContextBundle 0.2.0; otherwise
   preserve `visual_evidence_required` and never embed image bytes.
8. Offer provider-neutral OCR/caption ports without a default provider and publish
   accepted bounded results through F010 using exact crop dependency/trust facts.
9. Default licensing/export policy to trusted local-only/export-denied and prevent
   document/native/EXIF/model metadata from relaxing it.
10. Prove geometry, identity, bombs/limits, faults, concurrency, migration, reachability,
    freshness, compatibility, packaging and three-platform quality before merge.

## Baseline and rollback

- Rollback commit: `57b9b6746724273e53670c563b91655c225ecba7`
- Branch: `codex/f011-visual-evidence-escalation`
- External v3.1 and repository prompt SHA-256:
  `4e76b0d80c502fce2a6a3262ac15a28b11f67bba2ae9678de999a788d4abf847`
- Python: 3.12.13; locked existing dev/all-extras environment.
- Rollback requires reverting F011 code and restoring a paired pre-revision-8 workspace
  backup; migration history and immutable CAS objects must never be hand-edited.

## Pre-implementation analysis

`analysis.md` records initial 100 percent coverage and five corrected findings. The
second pass contained zero unresolved critical/high/medium/low findings.

## Green pre-implementation baseline

The first baseline attempt occurred after `.specify/feature.json` correctly moved to
F011. Ruff, format and strict mypy passed; pytest reported 918 passed and one expected
governance failure because the prior repository test still hard-coded F010 as active.
Coverage was 86.87 percent. T004 corrects only that active-feature contract before the
authoritative baseline rerun; no runtime source had changed.

| Command | Result |
|---|---|
| `uv run ruff check .` | success |
| `uv run ruff format --check .` | success; 123 files |
| `uv run mypy src` | success; 49 source files |
| `uv run pytest` | success; 919 passed, 86.88% coverage |
| `uv build` | success; wheel and sdist |
| `uv run python scripts/generate_schemas.py --check` | success; all 11 schemas current |
| `uv run python scripts/validate_evidence_contracts.py conformance/evidence/v0.1.0/manifest.json` | success; 7 valid, 8 invalid, 1 record set, 6 vectors |
| `uv run python scripts/validate_repository.py` | success |

This is the authoritative green pre-runtime baseline: 919 tests and 86.88 percent
branch-aware coverage. The initially planned validator names were corrected to the
repository's actual `validate_evidence_contracts.py` and `validate_repository.py`
commands before implementation.

## Implementation evidence

### Delivered behavior and traceability

| Acceptance area | Implementation and executable evidence |
|---|---|
| Exact contract/identity/geometry (FR-003–FR-008, FR-026–FR-027) | Pure visual models and new identity domains; twelfth generated schema, valid/invalid fixtures, reviewed vectors, 100-case integer geometry and 20 fresh-process identity tests; prior-contract freeze. |
| Optional bounded rendering (FR-009–FR-013, FR-029) | Exact PDFium/Pillow extra; intrinsic-rotation-aware renderer; stripped RGB PNG; spawned offline bounded-chunk IPC; timeout/crash/cancellation/egress plus independent dimension/pixel/decoded/output/metadata/frame caps. |
| Atomic cache/persistence (FR-014–FR-016, FR-025) | Migration 8, CAS-first service and complete visual catalog rows; all seven transaction fault boundaries, revision failure/too-new/concurrent upgrade, exact cache reuse, 20-client convergence and reachability failure classification. |
| Visual context (FR-017–FR-019, FR-022) | Mutually exclusive internal handle candidates, verified descriptor/raster/crop discovery, exact descriptor-object cost/handle, honest pre-materialization notice, post-materialization selection, head-change exclusion and pinned replay. |
| Optional interpretation (FR-020–FR-023) | No registered provider; strict requests/results; exact crop OBJECT dependency through F010; READY/FAILED/supersession/cancellation, hostile text, low confidence and egress-attempt evidence with model-derived untrusted classification. |
| CLI/privacy/operations (FR-024, FR-028, FR-030) | Identifier-only materialize/inspect commands, real spawned PDF CLI success, stable body/path-free errors, conservative local-only/export-denied policy and complete security/operations/rollback documentation. |

### Measured focused evidence

- Contract/domain/identity/geometry/renderer/worker/security group: 58 cases after the
  strict IPC frame test was added, including twenty fresh worker pairs.
- Migration/catalog/reachability/service/context/interpretation/CLI group: 92 passed
  in 4.26 seconds.
- Synthetic PDF source: 612 bytes,
  `sha256:1c95c7b0f6c4a427559488b8f4825a424b6055bb201096ec28473ad4442a50e2`.
- Canonical macOS arm64 wheel recipe page raster: 1,224 × 1,584 RGB, 16,846 bytes,
  `sha256:b136450744e32dde4f9e800a8b3e3686c195ccdc7feb6afe1976085d6f5fd261`.
- The Linux native wheel produced the same geometry but a different page digest,
  `sha256:f3ca9c3ac0c7be08da479b0cbfb5a2556d744dfb84a5b15e3791daa1a6660079`;
  this CI finding led to exact wheel RECORD fingerprints in both recipe profiles so
  platform-native outputs cannot collide.
- Exact macOS test crop: 246 × 318 RGB, 671 bytes,
  `sha256:96484cc29d3e9d9a6a8e31dc2c25a69cf344875b1763afea565fe2ccf2145164`.
- Generated visual schema: 29,559 bytes,
  `sha256:f87e81f1eb5db133a53894cf12494c84776364182cfac95ce6bbe03c776ea7a6`.
- First request invokes one page render and crop; an exact repeat invokes neither;
  a second region on the same page performs only one additional crop.
- Twenty independent catalog/CAS clients converge to one descriptor; cancellation at
  every service checkpoint leaves zero reachable visual rows.

### Supply-chain and compatibility review

Core dependencies remain exactly Pydantic and RFC 8785. The only dependency surface
change is the optional `visual` group with exact `Pillow==12.3.0` and
`pypdfium2==5.12.1`; the Docling group is unchanged. Provider imports remain outside
domain/core import paths, runtime versions are checked exactly, and the canonical
recipe additionally fingerprints every hashed wheel RECORD entry. No download,
telemetry or network capability is registered. The lock diff and isolated core/visual
wheel probes are mandatory final-gate evidence.

All eleven prior schema bytes, F006 vectors/corpus, F007 profile/export facts, F008
identity fixtures and F009 descriptors remain frozen. F011 adds only
`visual-evidence-descriptor.schema.json`; application version remains `0.0.1` and
export profiles do not change.

The focused compatibility/repository gate passed 27 tests. The reviewed `uv.lock` diff
contains only the `visual` extra declaration plus its two exact requirements; both
packages were already present transitively in the all-extras lock, so no unrelated
package/version changed.

### Isolated distribution evidence

`uv build` produced `openardp-0.0.1-py3-none-any.whl` and the source archive. Installing
the wheel into a fresh core environment resolved seven packages and proved `PIL` and
`pypdfium2` absent while the visual domain/port imported successfully. Installing the
same wheel with `[visual]` into a second fresh environment resolved exactly the two
additional pinned providers and reproduced the canonical 1,224 × 1,584, 16,846-byte
page raster with the reviewed SHA-256 vector. No network was used by the runtime smoke;
uv installation used its normal package resolver/cache before the smoke.

### Commands run before final convergence

```text
uv run pytest <F011 contract/domain/renderer/worker/security group> --no-cov
uv run pytest <F011 integration/context/interpretation/CLI group> --no-cov
uv run pytest
```

The final complete network-disabled pre-commit run passed 1,027 tests with
86.37 percent branch-aware coverage. Ruff, formatting over 155 files, strict mypy over
56 source files, wheel/sdist build, all twelve generated schemas, F006 conformance and
repository validation passed. Full pre-commit is the last local gate below.

## Tradeoffs and residual risks

- PDF is the sole concrete visual renderer. DOCX/PPTX adapters satisfy the provider
  port only when implemented by a future reviewed feature; F011 returns unavailable.
- A spawned offline worker plus portable limits is defense in depth, not a strong
  cross-platform sandbox. PDFium/Pillow native defects and platform limit variance
  remain.
- Raster bytes are repeatable only inside an exact wheel-content-bound recipe. All three
  CI environments verify their own repeated output; native platform outputs are not
  claimed to be mutually byte-identical or visually identical to proprietary viewers.
- Table cells are exact only with explicit native cell geometry. Otherwise a
  `table_fallback` warning is retained; row/column inference is prohibited.
- Rights are unknown unless a trusted out-of-band policy says otherwise. The built-in
  policy permits local inspection but denies export, which F014 must enforce.
- CAS-first failure can leave complete unreachable immutable objects. They are not a
  partial logical record; F013 owns classification, quarantine and reclamation.
- OCR/caption engines are intentionally absent. Explicit provider output is useful
  untrusted data and cannot replace the exact crop for visual verification.

## Final convergence

The final Spec Kit convergence assessed 30 functional requirements, 10 buildable
success criteria, 16 acceptance scenarios, the five plan phases and all twelve
constitutional articles against the delivered code, tests, schema, ADR, migration,
CLI, documentation, changelog and validation evidence. The first pass found one
critical transport-boundary issue: multiprocessing object messages implied Pickle
deserialization from the renderer child. The implementation now uses bounded raw-byte
chunks and a closed JSON metadata plus PNG result frame with duplicate-key/non-finite/
unknown-field rejection. The follow-up pass found zero missing, partial, contradictory
or unrequested work and appended no convergence task.

Final local gate: 1,027 tests, 86.37 percent branch-aware coverage, full pre-commit,
Ruff, formatting, strict mypy, wheel/sdist, twelve schemas, F006 conformance,
repository validation and isolated core/visual wheel smoke all pass. Pull request
[#16](https://github.com/Noetheon/OpenARDP/pull/16) validated the complete feature in
[run 30677502891](https://github.com/Noetheon/OpenARDP/actions/runs/30677502891): macOS
passed in 4m13s, Ubuntu in 6m30s and Windows in 13m32s. The evidence-only amendment must
pass the same matrix before merge, and F012 remains blocked until post-merge `main` CI
is green.
