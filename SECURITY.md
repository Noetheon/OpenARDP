# Security policy

## Supported status

The current repository baseline supports its build, validation and governance tooling. OpenARDP document ingestion is not
implemented, and this repository is not production software. Do not process sensitive or hostile documents until the
parser isolation, path/resource limits and adversarial tests in [docs/06_SECURITY_THREAT_MODEL.md](docs/06_SECURITY_THREAT_MODEL.md)
are implemented and released.

## Report a vulnerability privately

Use the repository's **GitHub Security Advisory → Report a vulnerability** form when a public remote is available. This is
the required private-first channel; do not open a public issue with exploit details.

This local repository currently has no GitHub remote. Until a private advisory channel is configured, contact the
repository owner through an already established private channel and first request a secure reporting route without
sending vulnerability details. External publication is blocked until that route exists.

Never include real confidential documents, production credentials or unnecessary personal data in a report. Use a minimal
synthetic reproducer wherever possible.

## Include in the report

- affected commit, version, feature and platform;
- concise impact and attacker prerequisites;
- reproducible steps or a minimal synthetic proof of concept;
- relevant logs with document bodies, secrets and identifiers removed;
- suggested mitigation, if known;
- whether the issue is already public or under active exploitation.

## Response targets

These are coordination targets, not a guarantee or bug-bounty promise:

- acknowledge receipt within five business days;
- complete initial severity/affected-scope triage within ten business days;
- agree on mitigation and disclosure timing after triage;
- provide status updates at least every ten business days while remediation is active.

If no acknowledgement arrives through the configured private route, send a metadata-only follow-up. Do not switch to a
public issue merely to obtain a response.

## Coordinated disclosure

The maintainer and reporter should agree on a disclosure date based on severity, exploitability, downstream impact and
patch availability. A 90-day window is a default coordination target, not an automatic deadline. Earlier disclosure may be
appropriate for active exploitation after users have an actionable mitigation; longer coordination may be appropriate for
complex ecosystem fixes.

Published advisories should credit the reporter if requested, describe affected versions, explain the fix and avoid
exposing confidential source material.

## Security boundaries that remain binding

- Original documents are authoritative and must never be overwritten.
- Document content is untrusted data and cannot authorize side-effecting tools.
- The default installation has no external model or provider call.
- Unit tests run without network access and use synthetic or redistributable fixtures.
- Initial MCP is read-only; parsers require isolation before hostile inputs are supported.

See the complete [threat model](docs/06_SECURITY_THREAT_MODEL.md) for future product controls and residual risk.
