# Research: Redistributable Real-World Corpus

## Selection method

Candidate sources were admitted only when an authoritative publisher exposed the exact original format, a stable record,
machine-checkable bytes and an explicit redistribution basis. Content usefulness alone was insufficient. The selected
set is deliberately small, English-language and public-sector; it is realistic but not statistically representative.

## Selected NASA NTRS records

| Format | NTRS ID | Title | Reviewed rights facts |
|---|---:|---|---|
| PDF | 20210012886 | NASA Framework for the Ethical Use of Artificial Intelligence (AI) | `PUBLIC_USE_PERMITTED`; third-party material false; final PDF |
| DOCX | 20210014231 | Report on Workshop on Artificial Intelligence in Strategic Planning and Science Prioritization | `GOV_PUBLIC_USE_PERMITTED`; third-party material false; final DOCX |
| PPTX | 20210025005 | Open Science and AI | `GOV_PUBLIC_USE_PERMITTED`; third-party material false; final PPTX |

NTRS per-record metadata is retained as the primary selection evidence. NASA names and insignia remain subject to
separate agency-mark and non-endorsement limits; the corpus documentation does not turn public-use evidence into a
general trademark licence or legal opinion.

## Selected CISA KEV revision

The official `cisagov/kev-data` repository revision
`564b8c59f9039926e2d9548ba5b334db45cb6b50` supplies the exact CSV, README Markdown and CC0 plain-text licence. Pinning a
full commit freezes operational data that otherwise changes frequently. The snapshot is a historical evaluation input,
not a current-vulnerability feed.

## Rejected alternatives

- NASA NTRS 20240005839 was rejected because its record reports possible copyright material and third-party content,
  even though permissions were also recorded.
- NIST publication samples were not selected because reusable PDF guidance did not also provide original DOCX/PPTX
  assets with equally direct per-record rights facts.
- UK Open Government Licence sources were not needed after one authoritative CISA revision covered the three open-text
  formats coherently.
- Generated PDF/Office conversions were rejected because they are derived fixtures, not authentic publisher originals.
- A live CISA URL without a commit pin was rejected because repeat runs would silently change the corpus.

## Exact measured selection

The six selected payloads total 6,634,970 bytes. The PDF has 35 pages; both Office packages pass ZIP structural checks.
The exact SHA-256 and length facts belong to the corpus lock and are independently rechecked rather than copied into
benchmark prose.

## Reproduction and drift policy

- Vendored source bytes remain authoritative for the frozen corpus version.
- Connected reproduction is an explicit maintenance operation into an absent external destination.
- Exact SHA-256 and byte length reject upstream drift; no tool blesses changed bytes automatically.
- Immutable CISA raw URLs use the full commit. NTRS record/download URLs are stable identifiers but not content-
  addressed, so byte locks provide the decisive drift boundary.
- Ordinary validation, tests, parsing and evaluation remain network-free.

## Parsing boundary

- Markdown and plain text use the shipped deterministic text parser.
- The F016 isolated CSV producer was evaluated first, but its deliberate 1 MiB response cap rejects this 932,085-byte
  real input because complete native/retrieval artifacts amplify beyond the cap. F024 therefore uses a new isolated
  standard-library probe that parses every row but emits only body-free identities, counts and anchor classes. It is a
  benchmark harness, not a stable core CSV ingestion API.
- PDF, DOCX and PPTX use the F007 isolated Docling profile; PDF additionally requires the validated external F023 bundle.
- Baseline results retain identifiers, counts, anchor classes and resource facts, never extracted document bodies.
- F024 proves selection, exactness and structural parsing only. Semantic relevance, answer correctness and source quality
  are separate F025 judgments.

## First binding-run findings

The first retained run was `REALWORLD_BASELINE_NOT_READY`. It exposed the F016 CSV response cap and two genuine PowerPoint
geometry cases: a shape slightly/partly outside the slide and a text item with a zero-area provider box. The rich
projection now clips only the visible intersection with explicit `provider_bbox_clamped`/`provider_bbox_clipped` warnings
and falls back to an exact opaque pointer with `provider_bbox_unusable` when no honest region exists. Native provenance
remains unchanged. One picture pointer correctly exceeds the existing 8 MiB per-body retrieval limit; the benchmark
retains that bounded rejection while confirming the small evidence projection remains retrievable.

## Decision

Adopt the six-file NASA/CISA snapshot as `realworld/v0.1.0`. Commit exact payloads and review evidence because a corpus
that disappears with a remote host is not a dependable offline benchmark. Keep download tooling explicit and fail closed,
and require a new version for any byte or identity-bearing metadata change.
