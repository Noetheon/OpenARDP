# Supply-chain requirements checklist: Secure development test runner

**Purpose**: Review the quality and completeness of the security-maintenance requirements before tasks are implemented.
**Created**: 2026-09-23
**Audience**: Maintainer and independent reviewer
**Feature**: [spec.md](../spec.md)

## Version and scope

- [x] CHK001 Is the vulnerable-to-patched boundary explicit and tied to a named advisory? [FR-001, SC-001]
- [x] CHK002 Is the development-only scope distinct from runtime and optional dependencies? [FR-004, Non-Goals]
- [x] CHK003 Does the spec require a reproducible lock and prohibit unrelated package-version drift? [FR-002, SC-003]
- [x] CHK004 Are unchanged product contracts, identifiers and release/pilot decisions explicit? [FR-004]

## Validation and exceptions

- [x] CHK005 Does the spec require the complete existing suite without weakening socket or coverage controls? [FR-003, SC-002]
- [x] CHK006 Is plugin/Python incompatibility handled with a stop condition rather than a hidden workaround? [Edge Cases, FR-003]
- [x] CHK007 Does acceptance distinguish local validation from later Linux/macOS/Windows CI evidence? [US1/AC2, SC-002]
- [x] CHK008 Does the spec define what happens if lock regeneration changes unrelated versions? [Edge Cases, FR-002]

## Security claims and operation

- [x] CHK009 Is the exact pytest-CVE closure claim tied to a fresh audit? [FR-005, SC-004]
- [x] CHK010 Does the spec prohibit a graph-wide clean claim while optional advisories remain? [FR-005, Edge Cases]
- [x] CHK011 Are the tested version, residual risks and rollback route required in durable evidence? [FR-005]
- [x] CHK012 Does the boundary avoid security-scanner, provider, pilot and release expansion? [Non-Goals, FR-004]

## Review outcome

All 12 requirements-quality questions have explicit traceability and pass. No high-impact ambiguity remains; implementation verification is separate from this checklist.
