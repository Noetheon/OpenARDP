# Changelog

All notable OpenARDP changes are documented here. The format follows Keep a Changelog principles, and releases use
semantic versioning once the public package lifecycle begins.

## Unreleased

### Added

- GitHub Spec Kit 0.13.3 integration for Codex with the reviewed OpenARDP Constitution.
- Python 3.12/uv repository baseline with a committed lock, strict local gates and commit-time checks.
- Least-privilege Linux/macOS/Windows CI contract with immutable third-party Action revisions.
- Offline repository validator for local Markdown evidence and governance consistency.
- Apache-2.0 license, contribution process, security policy and feature-local implementation evidence.

### Changed

- Moved the extracted Blueprint from its accidental nested folder to the repository root without altering its content.
- Limited feature 001 to package metadata and architecture namespaces.
- Pinned uv 0.11.31 and enabled its bounded centralized-project-environment preview after both 0.11.16 and 0.11.31 local
  `.venv` directories reproduced a macOS file-provider hidden-`.pth` failure.

### Removed

- Premature hashing, chunking, domain-model and CLI scaffold behavior that belongs to later bounded features.
- Placeholder runtime dependencies and extras for Docling, MCP, watchers and other later work packages.

### Security

- Unit tests block socket access.
- CI uses read-only permissions, non-persistent checkout credentials and full-SHA Action pins.

## Blueprint history

Pre-implementation package revision details remain in [REVISION_NOTES.md](REVISION_NOTES.md).
