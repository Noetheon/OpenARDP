# Conformance fixture roadmap

**Status:** Experimental roadmap guidance, not a current conformance claim.

Conformance means OpenARDP project-contract conformance, not an external standard. Required classes include
canonical/digest vectors; valid/invalid source/native/evidence/trust objects; stale/mismatched anchors; geometry and
coordinate-system cases; derivation cycles/freshness; context-budget/receipt vectors; migration/version negotiation; and
package attack vectors if export proceeds.

At least one validator must run without runtime adapters. Feature 016 must test an independent producer or consumer to
expose provider leakage.
