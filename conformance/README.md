# Conformance fixture roadmap

**Status:** F006 project-contract fixture family delivered; this is not an external
standard or cross-provider conformance claim.

Conformance means OpenARDP project-contract conformance, not an external standard. Required classes include
canonical/digest vectors; valid/invalid source/native/evidence/trust objects; stale/mismatched anchors; geometry and
coordinate-system cases; derivation cycles/freshness; context-budget/receipt vectors; migration/version negotiation; and
package attack vectors if export proceeds.

At least one validator must run without runtime adapters. Feature 016 must test an independent producer or consumer to
expose provider leakage.

## Evidence family 0.1.0

[`evidence/v0.1.0/`](evidence/v0.1.0/) contains synthetic valid and invalid roots for
native representations, evidence references, thin projections, and trust
classifications. Its manifest also covers all four anchor variants, source/native scope,
fixed-point page geometry, opaque pointer syntax, version negotiation, namespaced
extensions, trust escalation, canonical identity vectors, and one coherent record set.

Run it offline:

```bash
uv run --locked python scripts/validate_evidence_contracts.py \
  conformance/evidence/v0.1.0/manifest.json
```

The validator confines manifest paths to the fixture tree and imports only strict domain
contracts. It does not import adapters, dereference provider pointers, read source
documents, contact a network service, or claim that a second provider has implemented
the contract.

## Alternate parser conformance spike 0.1.0

[`alternate-parser/v0.1.0/`](alternate-parser/v0.1.0/) binds the complete F006 corpus to
an independently executed standard-library consumer and binds deterministic synthetic TXT
and CSV inputs to a non-Docling producer. The alternate executable runs under Python
isolated/no-site mode, imports neither OpenARDP nor third-party packages, covers text,
page-region, table-cell and opaque-provider-pointer anchors, and is consumed in turn by the
OpenARDP reference contracts.

Regenerate or check the evidence offline:

```bash
uv run --locked python scripts/validate_alternate_conformance.py --write
uv run --locked python scripts/validate_alternate_conformance.py --check
```

The generated decision is `supported_for_scoped_claim`: the measured thin identity,
navigation, retrieval, trust and lifecycle shapes interoperate in this bounded spike. This
does **not** establish arbitrary parser interchangeability, cross-provider semantic anchor
equivalence, production readiness, external adoption or a stable standard. Evidence contract
`0.1.0` remains experimental.

## Experimental interchange profile 0.1.0

[`interchange/v0.1.0/`](interchange/v0.1.0/) contains three valid deterministic BagIt
profile packages and thirty-eight invalid packages covering malformed ZIPs, compression,
comments, traversal/absolute/reserved/non-normalized/colliding paths,
duplicate/missing/undeclared members, link/device/encryption/descriptor metadata,
payload digests, profile and record versions, local-reference and permission/license/trust rules,
extensions, relationships, nested archives and resource bounds.

Run the drift check and the workspace-independent validator offline:

```bash
uv run python scripts/generate_interchange_vectors.py --check
uv run python scripts/validate_interchange_package.py \
  conformance/interchange/v0.1.0/valid/minimal.zip
```

This is OpenARDP experimental-profile evidence, not a claim that arbitrary BagIt or
RO-Crate packages conform.
