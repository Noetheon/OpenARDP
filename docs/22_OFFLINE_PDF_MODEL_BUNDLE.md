# Offline PDF model bundle

Feature 023 turns the previously unavailable PDF path into an explicit, local and independently verifiable capability.
Nothing downloads during import, normal tests, startup or PDF parsing. A connected operator must deliberately provision
the bundle first; every later verification, packaging, installation and conversion step is offline.

## Exact profile and trust boundary

The supported profile is Docling `2.114.0`, Heron layout and accurate TableFormer, with OCR and every unrelated
enrichment/model disabled. `source-lock.json` fixes five source paths, byte lengths, SHA-256 digests, destination paths,
full upstream revisions and reviewed license assertions. The installed `manifest.json` is derived from that lock. Offline
verification always receives the committed lock independently, so a self-consistent hostile package cannot redefine its
own accepted contents.

The five runtime files total 384,428,156 bytes. Generated installations and ZIPs are disposable external artifacts and
are excluded from Git. Original PDFs remain authoritative; model output remains derived and invalidatable.

## Lifecycle and failure behavior

Provisioning downloads one pinned file at a time into a sibling staging directory, verifies its exact length/digest,
materializes canonical controls/notices and publishes only after closed-tree verification. Packaging first re-verifies
the installation and writes a sorted `ZIP_STORED` archive with fixed timestamp, mode and prefix. Installation rejects
compression, encryption, links/devices, traversal, duplicates, case/Unicode aliases, missing/extra entries, overflow,
trailing bytes and all digest drift before atomic publication.

The actual spawned Docling worker receives only the verified `assets/` root and bundle ID. Every worker establishes
offline flags, fresh private Hugging Face/XDG cache roots and socket denial before provider import. Errors remain a fixed
body-free taxonomy; URLs, credentials, provider bodies, local paths and tracebacks are not result fields.

## Measured result and limitations

The binding Apple-silicon result is `PDF_OFFLINE_READY`. The portable package is 384,450,807 bytes with 2,310 bytes
overhead. Three retained fresh workers converted the synthetic one-page PDF with identical native output, two anchored
evidence candidates and complete native pointers. Wall p50/p95 was 4.169/4.271 seconds and peak child RSS was about
1.474 GB. Three complete installation validations measured 0.150/0.155-second p50/p95 and about 68.1 MB peak RSS;
the measured successful connected provision took 191.254 seconds.

Verified facts are byte identity, exact source mapping, mechanical license-text presence, closed offline execution and
synthetic projection correctness. License identifiers remain reviewed upstream assertions, not legal advice or proof of
all training-data rights. This feature does not validate OCR, arbitrary layouts, scanned PDFs, real-world quality,
semantic answers or source-ranking quality; F024 and F025 own those questions.
