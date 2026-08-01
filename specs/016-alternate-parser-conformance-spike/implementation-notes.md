# Implementation Notes: Alternate Parser Conformance Spike

**Feature**: `016-alternate-parser-conformance-spike`

**Branch**: `codex/f016-alternate-parser-conformance-spike`

**Date**: 2026-08-01
**Rollback/base commit**: `a1619d93a6ff071e172dcc257c377870d5bc1843`
**Authoritative prompt SHA-256**: `f0af6e7414ca9144f41498ab07db9e0177ccabc0a7138accff9360cf1ef479e7`

## Restated acceptance criteria

1. Run a genuinely independent producer or consumer outside OpenARDP runtime/adapters.
2. Cover text plus page-region and table-cell anchors without Docling-shaped output.
3. Validate the complete F006 valid/invalid/record-set corpus and every identity vector.
4. Produce deterministic non-Docling TXT/CSV native artifacts and thin evidence records.
5. Exercise both directions: reference fixtures into the alternate consumer and alternate
   output into the OpenARDP reference contracts.
6. Confine all untrusted inputs, bound process/files/bytes/time and emit body-free failures.
7. Preserve source/native provenance, trust non-escalation and instruction-as-data behavior.
8. Generate a deterministic fail-closed decision with exact evidence identities.
9. Report friction, provider leakage, required changes, limitations and prohibited claims.
10. Do not stabilize the experimental contract or claim universal parser equivalence.
11. Keep every existing public contract, workspace and application version unchanged unless
    falsification proves a governed breaking change necessary.
12. Complete all Spec Kit, local repository, build and three-platform remote quality gates.

## Baseline

F016 begins from F015 merge commit `a1619d93a6ff071e172dcc257c377870d5bc1843`.
Post-merge workflow
[30702672000](https://github.com/Noetheon/OpenARDP/actions/runs/30702672000)
passed all seven Linux, macOS, Windows and aggregate release-evidence jobs.

## Clarification and design result

No critical ambiguity required user input. The prompt explicitly permits another language
or process; Python 3.12 `-I -S` provides an auditable cross-platform process boundary without
a new runtime dependency. The producer deliberately handles only deterministic UTF-8 text
and RFC 4180-style CSV. Its declared grid geometry is provider-profile data, not physical
document truth.

## Test-first evidence

Foundation, consumer, producer, decision and boundary tests were written around the frozen
manifest/profile. The first focused run exposed one test assumption: synthetic hostile text
is intentionally retained inside hex-encoded native artifact bytes rather than exposed as a
top-level diagnostic string. The test was corrected to inspect the retained artifact itself;
the implementation boundary did not change.

## Implemented boundary

- Standard-library-only independent process with exact self-check, closed command framing,
  safe canonical JSON subset and stable failure categories.
- Complete F006 root, semantic, record-set and golden-vector validation without importing
  reference code.
- Non-Docling `stdlib-text-csv` / `deterministic-grid` producer with retained canonical
  native artifacts and all four anchor classes.
- Reference-side artifact digest/length and Pydantic contract validation for the reverse
  direction.
- Exact executable/input/observation/decision identities, three-run byte determinism and
  no-waiver decision generation.
- Generated record set and decision registered in the offline repository validator.

## Current evidence

| Evidence | Result |
|---|---|
| Independent self-check | `openardp`, `pydantic`, `rfc8785` unavailable; isolated/no-site true |
| F006 consumer | 7 valid, 8 invalid, 1 record set, 6 identity vectors pass |
| Alternate producer | 2 sources; text/page/table/pointer coverage; reference validation pass |
| Repeat determinism | 3 subprocess runs byte-identical |
| Focused F016 tests | 25 passed with `--no-cov` |
| Decision | `supported_for_scoped_claim` |
| Decision identity | `sha256:bd71ad5756c2971e16a00138c628c236df88f7d5989eb6c9beb762719ab96a50` |

## Full local validation

| Gate | Result |
|---|---|
| `uv run ruff check .` | pass |
| `uv run ruff format --check .` | pass; 232 files |
| `uv run mypy src` | pass; 77 source files |
| `uv run mypy src --platform win32` | pass; 77 source files |
| `uv run pytest` | pass; 1,342 tests, 85.13% branch coverage |
| alternate conformance drift check | pass; 2 sources, scoped claim supported |
| repository/schema/F006/interchange/F015 drift checks | pass |
| `uv build` | pass; wheel and source distribution |
| wheel SHA-256 | `e1bba06468be2b172210a3c3b38d55fae3c310d20b678a2b275aaedd6fc308ae` |
| sdist SHA-256 | `624b3092dea6a152c6e9a6c682e094a2511b2b76d69b91c4914fb86cce27c177` |
| artifact member inspection | pass; deterministic wheel timestamps and expected package/governance members |
| `uv run pre-commit run --all-files` | pass |
| `git diff --check` | pass |

The first full suite run exposed only the expected active-feature meta-test drift from F015
to F016; the originating test was updated and passed. A later run encountered one transient
pre-existing F013 20-thread retention race (`managed object changed while opening`). The
exact test passed five consecutive isolated reruns, no F013 behavior was changed in this
feature, and the subsequent complete regression gate passed.

The first pull-request workflow, run
[30705200034](https://github.com/Noetheon/OpenARDP/actions/runs/30705200034), passed six of
seven jobs but exposed eight Windows-only assertions: Python text-mode stderr translated
the contract's LF terminator to CRLF. The independent process now writes ASCII diagnostics
through `sys.stderr.buffer`, preserving the same exact body-free bytes on every platform.
The resulting executable digest is
`sha256:9ab9be10ba0726dccc3f0843e0a61c84513280f153187f3367e3b82231085c49`;
all generated evidence was regenerated before the replacement workflow.

Three-platform pull-request and post-merge evidence is appended after publication.

## Friction, leakage and required changes

- **Friction**: schema-only validation is insufficient; semantic identity, scope, trust and
  record-set rules must be implemented independently.
- **Friction**: purpose-specific JCS allowlists must be reproduced. The independent safe
  subset intentionally rejects floats and unsafe integers because current identities do not
  need them.
- **Friction**: page geometry and table/provider pointers need provider-profile semantics.
- **Provider leakage**: none observed in contract fields or alternate output.
- **Required contract changes**: none.
- **Stability**: unchanged `experimental`; external-use and migration-practice evidence are
  still absent.

## Tradeoffs and residual risks

- A separate Python process is a meaningful independent implementation but shares the base
  language/runtime. Another-language adoption would add stronger portability evidence.
- The alternate parser is intentionally tiny and does not evaluate production parsing
  quality, OCR, PDF/Office layout or malformed-document breadth.
- The canonicalizer fully covers current identity vectors and rejects floats rather than
  claiming a general RFC 8785 number implementation.
- `-I -S`, path confinement and time/byte limits are bounded isolation, not a universal
  security sandbox.
- Synthetic declared geometry proves contract shape interoperability, not equivalent visual
  interpretation between providers.

## Rollback

Revert the isolated F016 commit or merge commit. No workspace migration, runtime adapter,
dependency or source mutation exists. All alternate records and decisions are disposable
derived evidence and may be removed and regenerated.
