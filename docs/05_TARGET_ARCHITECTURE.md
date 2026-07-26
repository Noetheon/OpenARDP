# Target architecture after Feature 007

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

Feature 007 delivers an exact optional `docling==2.114.0` adapter. Source paths never
enter the worker: verified bytes cross bounded IPC into a spawned process after offline
environment, resource limits and socket denial are active. DOCX/PPTX use local
declarative backends; PDF requires a reviewed local model bundle before provider
execution.

OpenARDP stores complete canonical Docling JSON as an immutable native artifact and
maintains versioned opaque pointers into it. Only fixed, reviewed evidence fields are
projected into F006 records. Docling's unsafe unsigned `origin.binary_hash` is
losslessly represented as a decimal string; every other non-I-JSON value fails closed.
The isolation boundary is defense-in-depth, not a portable strong sandbox.

Catalog revision 5 atomically joins the base READY representation, canonical rich
attempt, complete evidence inventory, head and event. Forced reparses append
converged/diverged attempts and never silently replace accepted evidence.
