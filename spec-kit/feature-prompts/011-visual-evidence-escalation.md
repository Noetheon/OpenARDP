# Feature 011 — Visual evidence escalation

## Goal
Retrieve exact page, image, table and crop evidence while keeping OCR/captions as untrusted derived interpretations.

## Requirements
CAS descriptors, bounds-checked deterministic crops, coordinate-system metadata, page rotation/scale handling, table-cell anchors, optional offline/provider-neutral OCR/caption ports, provenance/freshness and compiler escalation policy. Respect source licensing and export restrictions.

## Security/tests
Image/decompression bombs, malformed dimensions, huge pages, embedded deceptive text, EXIF/metadata abuse, cancellation and output-size bounds.
