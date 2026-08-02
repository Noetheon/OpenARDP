# Implementation Notes: Redistributable Real-World Corpus

**Feature**: `024-redistributable-realworld-corpus`

**Branch**: `codex/f024-redistributable-realworld-corpus`

**Date**: 2026-08-02

## Restated acceptance criteria

1. Commit exactly one genuine PDF, DOCX, PPTX, CSV, Markdown and plain-text publisher original.
2. Preserve exact byte identities, source metadata, immutable revisions where possible and reviewed rights evidence.
3. Keep validation and all ordinary use offline; make source reproduction explicit, bounded and atomic.
4. Reject every missing, extra, unsafe, colliding, mismatching or incompletely mapped corpus tree.
5. Reproduce exact bytes twice or retain upstream failure/drift without accepting changed data.
6. Parse all six formats through existing isolated/deterministic provider boundaries with sockets denied.
7. Retain body-free identity, anchor, count, timing and memory facts with unfavorable evidence.
8. Independently regenerate the complete baseline result and fail-closed decision.
9. Preserve F020/F023 history and make no semantic, representative-quality, endorsement or legal-certainty claim.
10. Complete full Spec Kit, local quality, build and private three-platform release gates before F025.

## Baseline

F024 begins from F023 closeout merge `8164684d505515e5f5764dc9687d356ce05f6917`. F023 proved its synthetic PDF
fixture `PDF_OFFLINE_READY` using the external five-file 384,428,156-byte Docling bundle. Real-world and semantic quality
remained explicitly unmeasured.

## Evidence log

### Selection and exact reproduction

- The frozen corpus contains six publisher originals/6,634,970 bytes and all required formats. Its identity is
  `sha256:5e505148c7e9004a9c1ae7bd68c66addfc9ae3377be7e3057a81d7a1996649bd`.
- NASA NTRS 20210012886, 20210014231 and 20210025005 retain public-use determinations, final-download facts and false
  third-party-material flags. Official CISA `kev-data` commit
  `564b8c59f9039926e2d9548ba5b334db45cb6b50` retains exact Git blobs and CC0 text.
- Two explicit connected reproductions into fresh `/Users/Shared` roots matched every file and corpus identity. Measured
  durations were 11,750,031,917 ns and 10,802,469,792 ns. Both independent offline validations passed afterward.

### Test-first corpus boundary

The first focused corpus contract run passed 25 tests after two test fixtures were corrected to recompute the lock
identity before targeting lower-level ordering/collision failures. The implementation itself correctly rejected the
mutated identity first. Coverage includes closed files/directories, links/hard links, exact bytes, mapping completeness,
case collisions, redirects, schemes, media, truncation, oversize, transport errors, no-network validation and legal-
overclaim wording.

### First binding result and findings

The first actual run completed as `REALWORLD_BASELINE_NOT_READY` and remains under
`/Users/Shared/openardp-f024-initial-not-ready`. TXT, Markdown, DOCX and the 35-page PDF passed, while:

1. The 932,085-byte CISA CSV caused the F016 complete-artifact producer to exceed its deliberate 1 MiB response bound.
2. The PPTX exposed a 101-unit rounding overshoot on a 5,143,500-unit slide, a shape extending 347,025 units beyond a
   9,144,000-unit slide and a zero-area provider box.

No threshold or observation was hidden. F024 added a separate isolated stdlib CSV probe that parses all 1,656 rows but
emits only body-free hashes/counts. The rich projection now clips the visible page intersection with explicit
`provider_bbox_clamped`/`provider_bbox_clipped` warnings and falls back to an opaque native pointer with
`provider_bbox_unusable` when a truthful region does not exist. Direct coordinate conversion remains fail-closed, and
the complete provider-native value is unchanged.

### Binding accepted result

The corrected 44,105,787,042 ns run produced `REALWORLD_BASELINE_READY`; the independent validator regenerated all 12
observations, summaries, decision, report, file hashes and run identity with zero failures.

| Asset | Format | Units | Pages | Tables | Wall p50 / p95 ns | Peak RSS bytes |
|---|---:|---:|---:|---:|---:|---:|
| cisa-kev-license | TXT | 14 | 0 | 0 | 143,250 / 184,458 | 69,353,472 |
| cisa-kev-readme | MD | 17 | 0 | 0 | 105,104 / 134,375 | 69,369,856 |
| cisa-known-exploited-vulnerabilities | CSV | 1,656 | 1 | 1 | 85,084,625 / 85,113,500 | 69,435,392 |
| nasa-ai-strategic-planning-workshop | DOCX | 678 | 0 | 8 | 3,245,755,854 / 3,296,945,375 | 479,248,384 |
| nasa-ethical-ai-framework | PDF | 632 | 35 | 6 | 15,606,485,958 / 15,719,788,416 | 1,725,415,424 |
| nasa-open-science-and-ai | PPTX | 209 | 13 | 0 | 2,824,012,604 / 2,969,379,208 | ≤1,725,415,424 |

The PPTX contains one native picture subtree over the existing 8 MiB per-body retrieval limit. Pointer targeting reaches
the correct node and bounded materialization rejects it; the small evidence projection remains retrievable. The result
retains `pointer_bounded_count = 1`. PPTX RSS is a conservative process-family high-water upper bound inherited after
PDF, not an allocation claim for that document alone.

### Claim boundary

The accepted decision proves exact selection, reviewed redistribution evidence, reproducibility and structural offline
processing for this corpus. CSV remains a benchmark-only probe. Six English public-sector sources do not establish
general parsing quality, and no semantic question, relevance, answer, citation or source-quality judgment occurs before
F025.

### Quickstart and local convergence

- Both previously executed connected reproductions and their follow-up independent validations matched the committed
  6,634,970-byte corpus exactly. Reproduction was not repeated after the evidence was frozen because the destinations
  are intentionally publish-once and the command is the sole connected F024 operation.
- The binding external result and its committed copy both independently validate as `REALWORLD_BASELINE_READY` with
  zero failures.
- The focused F024 set passed with one intentionally skipped opt-in external-bundle test.
- Ruff, format, strict mypy for native and Windows targets, maintainability audit, repository validation and build pass.
- The first full local suite reached 85.01% coverage with 1,562 passed and two skipped. Its three failures identified one
  stale F023 active-feature assertion, now corrected, plus two pre-existing untracked ` 2.py` duplicate files. Those
  user files are deliberately neither changed nor staged. The clean staged-tree rerun is the binding local result:
  1,550 passed, two skipped and 85.24% coverage, with Ruff, format, native/Windows mypy, repository validation and build
  all passing.
- `uv run pre-commit run --all-files` passed every configured hook in the same clean staged tree, including the complete
  no-network Pytest hook.
- Final analysis covers 26/26 functional requirements and 10/10 success criteria with zero unresolved critical/high
  findings. The feature is converged; T065 release evidence is recorded below.

### Remote release evidence

- Private PR [#31](https://github.com/Noetheon/OpenARDP/pull/31) reviewed feature commit
  `e1db1f352be207ff4e0a654593ad4f2508a0caba` and passed trusted CI run
  [30761078961](https://github.com/Noetheon/OpenARDP/actions/runs/30761078961): preflight 43 seconds, macOS 4
  minutes 55 seconds, Ubuntu 9 minutes 14 seconds including authoritative coverage/build, and Windows 11 minutes 32
  seconds.
- PR #31 merged as `0c7eaa1fba9934f7a5fa4332946a75f4d36481e9` on 2026-08-02.
- Post-merge run [30761568800](https://github.com/Noetheon/OpenARDP/actions/runs/30761568800) initially failed before
  execution because GitHub refused to allocate a runner. Its annotation states that recent account payments failed or
  the spending limit needed increasing; runner ID was zero and no workflow step executed. This remains retained as an
  external billing boundary rather than being misreported as a product or workflow failure.
- After the repository owner restored runner allocation, attempt 2 executed the same historical merge SHA
  `0c7eaa1fba9934f7a5fa4332946a75f4d36481e9` on 2026-08-08. Its post-merge preflight passed in 45 seconds; the Linux,
  macOS and Windows quality jobs were correctly skipped by the governed `main`-push policy instead of duplicating the
  already successful exact-SHA pull-request matrix.
- The successful pull-request matrix and successful exact-merge-SHA post-merge preflight close T065 without hiding the
  original external billing failure or spending additional all-platform runner minutes.
