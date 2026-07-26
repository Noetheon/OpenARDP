# Target architecture after Feature 005

**Status:** Planned architecture governed by accepted ADRs and the
[feature map](../spec-kit/FEATURE_MAP.md). Only behavior listed in the [README](../README.md) is currently delivered.

```text
Authoritative source bytes
        |
        v
Source snapshot + digest
        |
        +--> Native parser adapter (Docling first)
        |       |
        |       +--> immutable native representation in CAS
        |
        +--> Evidence projection builder
                |
                +--> blocks/anchors/trust labels
                +--> lexical index
                +--> optional derivation graph
                +--> context compiler
                +--> read-only MCP
```

## Invariants

- Native representation is immutable and provider-labelled.
- Evidence projection is thin and rebuildable.
- Search indexes are disposable accelerators, never authority.
- Every returned body is verified against CAS.
- Metadata used for authorization/trust is verified against authoritative records.
- Derived artifacts declare exact inputs and generator identity.
- Stale derived artifacts are never silently presented as current.
- Context compilation is deterministic for fixed corpus, policy, task and budget where ranking is deterministic.
- Source data cannot become executable instructions through ingestion.

## Docling boundary

OpenARDP stores Docling output as a native artifact and maintains pointers into it. It may normalize minimal evidence fields needed for cross-provider retrieval, but must not reproduce all Docling semantics in project-owned models.
