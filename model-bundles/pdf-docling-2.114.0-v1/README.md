# OpenARDP Docling PDF bundle v1

This directory commits only the immutable source lock, canonical runtime manifest, review notices and license texts. The
five model files and generated ZIP remain outside Git.

The supported profile is Docling `2.114.0` with Heron layout and accurate TableFormer enabled. OCR, remote services,
external plugins, picture/chart/code/formula enrichment and every unrelated model are excluded.

Provision explicitly with `scripts/provision_pdf_bundle.py`, then verify/package/install with the offline commands in
`docs/22_OFFLINE_PDF_MODEL_BUNDLE.md`. Offline verification must always receive this committed
`source-lock.json` independently; a self-consistent untrusted package is not its own trust root.
