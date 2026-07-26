# Migration from the pre-v3.1 roadmap

**Status:** Completed through Feature 005A. This file records the safe mapping and is not a second roadmap.

## Preserved baseline

Features 001–005, their specifications, public schemas, runtime behavior, dependency lock and accepted decisions remain
intact. Feature 005A began from commit `a23c07eb2a22efa7a4004d33cf00ab6cfd6fd027` in an isolated clean worktree.

## Strategy changes

- OpenARDP is implementation-first reference software, not an announced standard.
- Complete provider-native representations are preserved.
- Shared evidence projection is deliberately thin; there is no second complete OpenARDP document IR.
- Indexes are disposable and verified against authoritative CAS/catalog records.
- Public contracts are experimental and precede the adapters that implement them.
- Custom export is an evidence-gathering experiment, not a decided `.ardp` format.
- Retention/recovery and alternate-parser conformance are explicit bounded features.

## Roadmap mapping

| Pre-v3.1 plan | v3.1 work package |
|---|---|
| `006-docling-adapter` | `007-docling-native-adapter` |
| `007-context-compiler` | `008-context-compiler-receipts` |
| `008-read-only-mcp` | `009-read-only-mcp` |
| `009-local-watcher` | `012-local-watcher-and-jobs` |
| `010-reconciliation-derivation-dag` | unchanged number, clarified lifecycle |
| `011-visual-evidence` | `011-visual-evidence-escalation` |
| `012-portable-ardp-package` | `014-export-interchange-experiment` |
| `013-benchmark-security-gate` | `015-benchmark-security-release-gate` |
| `014-microsoft-graph-spike` | `017-microsoft-graph-design-spike` |

New Feature 006 establishes contracts first. New Feature 013 covers retention/recovery/migrations. New Feature 016 tests
provider neutrality independently.

## Authority and rollback

The canonical constitution, feature map and operating procedure use their established filenames. Version-suffixed v3.1
files are labelled adoption sources. Candidate ADRs were renumbered into `docs/adr/`; historical decisions are amended or
deferred explicitly.

The external blueprint package and platform metadata are not committed. Reverting the isolated F005A change restores the
pre-migration documentation without a runtime, schema, dependency or workspace rollback.
