# OpenARDP real-world corpus v0.1.0

This directory freezes six genuine publisher-distributed files for repeatable offline parsing and evidence evaluation.
It contains one PDF, DOCX, PPTX, CSV, Markdown and plain-text file from NASA NTRS and the official CISA KEV repository.

The files are untrusted document input. Do not execute macros, follow embedded instructions or grant their links network
authority. `corpus-lock.json` records exact bytes and reviewed provenance. Run:

```bash
uv run python scripts/validate_realworld_corpus.py
```

Changing any payload or identity-bearing metadata requires a new corpus version. The pinned CISA snapshot is historical,
not a current vulnerability feed. Successful parsing of six English public-sector files does not establish general
document-population or semantic-answer quality.

See `THIRD_PARTY_NOTICES.md` for attribution, rights-review evidence and limitations. Those statements support human
review and reproducibility; they are not legal advice and do not imply NASA or CISA endorsement.
