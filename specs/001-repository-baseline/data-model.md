# Phase 1 Data Model: Repository Baseline

Feature 001 introduces no runtime domain entity, persisted identifier, document record, state transition or storage
contract. Creating one here would violate the explicit scope boundary and Article IX of the Constitution.

The feature manages only version-controlled engineering artifacts:

| Artifact | Authoritative fields | Validation rule | Lifecycle |
|---|---|---|---|
| Project metadata | package name, version, Python range, license, build backend, tool configuration | Parseable and internally consistent with package/version/license files | Changed only through reviewed repository maintenance |
| Dependency lock | Python requirement and exact resolved package graph | Must exist and pass locked synchronization against project metadata | Regenerated only when dependency metadata intentionally changes |
| Package boundary | namespace name, typing marker and module docstring | Exactly the five boundaries required by `AGENTS.md`; no product behavior | Extended by later analyzed features |
| Quality-gate contract | command, purpose and success/failure status | Same command families locally, in pre-commit and CI | Updated with toolchain/contract changes |
| CI policy | triggers, permissions, matrix, immutable action revisions | Read-only, non-persistent credentials, Linux/macOS/Windows, Python 3.12 | Reviewed on action/tool upgrades |
| Governance artifact | license, contribution, security, validation and changelog content | Required file exists and agrees with project metadata/docs | Updated when governance or evidence changes |

These artifacts are not OpenARDP interchange schemas. Existing public JSON Schemas remain project-level blueprint inputs
and are syntax-validated but are not implemented as Python domain models in this feature.
