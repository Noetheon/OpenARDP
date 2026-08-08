# F030 semantic product-surface benchmark v0.1.0

This frozen operational benchmark measures the exact F029 semantic profile through the F030 product composition. It
runs two independently initialized provider lifecycles; each lifecycle executes one cold and one warm compilation over
fresh workspace state while reusing only the provider's disposable passage cache.

The committed result contains body-free observations, a deterministic summary and decision, a human report and an exact
manifest. `scripts/validate_semantic_surface_benchmark.py` uses only the Python standard library and recomputes every
identity, aggregate, gate, privacy restriction and file digest.

The decision is ready only when both runs preserve timing-free projection identity, warm cache reuse is at least 90%,
warm wall time does not exceed cold wall time, peak provider-worker RSS is no more than 1.5 GiB and offline execution is
declared. These operational gates do not change or re-evaluate F029 retrieval quality.

See `specs/030-semantic-retrieval-product-surface/quickstart.md` for exact commands. External model bundles remain outside
Git and must match their committed source locks.
