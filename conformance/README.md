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
the contract. Feature 016 still owns that falsification test.
