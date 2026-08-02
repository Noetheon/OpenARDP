# Data Model: Redistributable Real-World Corpus

## Corpus lock

`corpus-lock.json` is a closed JSON object containing:

- `schema_version`, `corpus_name`, `corpus_version`, `corpus_id`
- `payload_root`, aggregate size and exact required format list
- sorted `assets`, each with stable key/path, media/format, byte facts, descriptive metadata, source record/download facts,
  one `rights_id` and optional immutable revision
- sorted `rights`, each with basis, evidence URL, reviewed publisher facts, required notice, restrictions and explicit
  review-not-legal-advice status
- sorted `evidence_files` with relative path, media type, SHA-256 and byte length
- namespaced extensions only

`corpus_id` is SHA-256 over the RFC 8785 canonical lock projection with `corpus_id` removed. Therefore paths, source facts,
rights facts and evidence-file identities all advance the corpus identity; absolute roots and creation times never enter it.

## Corpus asset

An asset is one exact regular file under `sources/`. Its SHA-256 is both its byte identity and source-version identity.
Assets are immutable within one corpus version, sorted by relative path and unique under byte, POSIX path, case-fold and
Unicode-normalization identities. Multiple files may originate from one source revision but remain distinct assets.

## Rights record

A rights record declares:

- identifier and reviewed basis (`NASA-NTRS-PUBLIC-USE` or `CC0-1.0`)
- authoritative evidence URL and publisher
- mechanically retained publisher fields
- attribution/notice text and non-endorsement/trademark limitations
- `review_assertion`, fixed to `human_review_required_not_legal_advice`

Validation proves presence and consistency, not ownership or legal certainty.

## Evidence file

An evidence file is a minimal metadata or licence snapshot under `evidence/`. It is not document payload and is never
parsed for product-quality measurements. Its exact bytes are bound into the corpus ID through the lock.

## Reproduction result

A connected reproduction result contains only corpus ID, payload count/bytes, stable per-source outcomes and duration.
The producer stages bytes in a sibling directory, verifies the complete tree, then atomically publishes an absent
destination. Response bodies, redirects, absolute paths and exceptions are never retained.

## Baseline observation

One observation per asset and repetition contains:

- corpus/asset/source/recipe/native/ordered-block identities
- format and parser profile
- block/evidence/anchor/page/table counts
- retrievability and pointer-resolution booleans
- wall/CPU time and peak process/child RSS
- socket/cache/model-boundary facts
- stable outcome/error category

No source text, extracted block body, native document or provider exception is retained.

## Baseline result

The result directory contains canonical `observations.json`, `summary.json`, `decision.json`, deterministic `report.md`
and `run-manifest.json`. The decision is `REALWORLD_BASELINE_READY` only when exact corpus coverage, offline authority,
successful retrieval, deterministic identities and resource bounds all pass. Result identity excludes run duration while
the run manifest may retain it as a non-comparison measurement.
