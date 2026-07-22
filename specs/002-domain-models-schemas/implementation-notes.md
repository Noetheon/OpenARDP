# Implementation Notes: Domain Models and Interchange Schemas

## Work-package acceptance criteria restatement

F002 is complete only when all of the following are true:

1. Manifest, Block, Derivation, Relation and Context Bundle have strict Pydantic v2 models that enforce every documented schema-expressible and record-semantic invariant.
2. Each root record has a committed JSON Schema 2020-12 contract and at least one synthetic golden JSON fixture that validates and round-trips losslessly.
3. RFC 8785 canonical serialization and SHA-256 identity helpers match independent golden vectors and remain stable across process runs, mapping construction order, hash seeds and the three-platform CI matrix.
4. Unsupported/malformed schema versions, unsafe trust flags, malformed identities and all other F002 negative classes fail clearly at every validation layer capable of expressing the rule.
5. Public schemas regenerate deterministically and unreviewed model/schema drift fails tests.
6. Model, schema, fixture, compatibility, identity and changelog changes remain traceable.
7. Persistence, parsing, retrieval, CLI, provider calls and other later-feature behavior are absent.
8. Spec Kit analysis reports no unresolved critical contradiction, convergence reports no remaining work, all repository gates pass locally and the GitHub Linux/macOS/Windows matrix is green.

## Selected trade-offs

- A small pinned RFC 8785 dependency is preferred over maintaining a custom ECMAScript-compatible number serializer.
- Attribute-level frozen Pydantic records and tuple core collections are delivered; nested JSON mappings are validated snapshots, not claimed as deeply immutable containers.
- Standard JSON Schema remains honest: dynamic equality/recomputed-hash rules live in model validators and are explicitly classified rather than encoded as proprietary keywords.
- The pre-stable Manifest retains `spec_version`; changing that established field solely for naming uniformity is not worth a contract break.
- Existing `.example` schema identifiers remain stable for release `0.1.0`; identifiers cause no network access. A future resolvable namespace requires a versioned compatibility decision.

## Test-first and contract evidence

- Foundation tests were authored before `common.py` and `identity.py`; their first collection failed because the modules did not yet exist. After the smallest implementation, 25 focused tests passed.
- The five golden records plus model/schema negatives were authored before the five root modules and schema generator; their first collection likewise failed on the missing public modules. After implementation, all 35 US1 tests passed.
- F002's final focused domain/contract acceptance command passed 144 tests at 100 percent statement and branch coverage. It includes the RFC main and UTF-16 sort vectors, fixed OpenARDP digests, unsupported-value cases and 20 fresh-process executions with varied order and `PYTHONHASHSEED`.
- The compatibility matrix exercises malformed, well-formed-but-uninstalled and unsupported-major versions for each of the five roots. Generator check mode is tested as byte- and modification-time preserving.
- The narrow package/repository scope suite passed 24 tests with `--no-cov`; the repository-wide 147-test run separately enforces and passes the global coverage threshold. This avoids misrepresenting coverage from a deliberately partial test selection.

## Locked dependencies

- `pydantic==2.12.5`
- `pydantic-core==2.41.5`
- `rfc8785==0.1.4`

`pyproject.toml` constrains the reviewed Pydantic 2.12 and rfc8785 0.1 minor series; `uv.lock` pins the exact distributions.

## Reviewed schema digests

All values are SHA-256 over the committed UTF-8 schema file bytes:

| Schema | SHA-256 |
|---|---|
| `block.schema.json` | `413d725016a9f4f261e384efff3f82906a08c7e3b73a25bc8f96963a10861562` |
| `context-bundle.schema.json` | `e6cea129f58bd11ec52e1f63ef87258d8ec9c01ac37ff7fa933b08e96790a31a` |
| `derivation.schema.json` | `56e8fc17050584b6d4bfc430d5f8d24de03237e5ef2b96fc7d9f6afd61f3e88a` |
| `manifest.schema.json` | `1995cc1062e5322405a00adba8e47c7f3bed9fa294de6920dc27476c5a36dfd4` |
| `relation.schema.json` | `00b581b077089e6534f4cc0c3af511fa2caa8ede6b81649ee5094f0b60bca142` |

Two consecutive `uv run --locked python scripts/generate_schemas.py --check` executions reported all five schemas current. Tests independently rebuild, validate and compare every schema byte-for-byte without writing.

## Spec Kit evidence

- Clarification resolved schema-release compatibility, JCS numeric equivalence, identity projection ownership, representation pinning and schema-versus-semantic enforcement before planning.
- Final pre-implementation analysis mapped all 27 functional requirements and nine success criteria to 48 tasks, with zero critical, high or medium findings and zero unmapped requirements.
- Both feature checklists are complete: 16/16 requirements-quality items and 30/30 domain-contract items.
- The first convergence review found three subtle gaps: endpoint extensions entering relation identity, incomplete explicit invariant-branch coverage and a non-schema-visible content-role rule. Append-only tasks T049–T051 closed all three.
- Final local convergence rechecked all 27 requirements, nine success criteria, 51 tasks, five models/schemas/fixtures, higher-level documentation and the F003+ scope boundary. It found zero unresolved or unrequested implementation gaps. T048 remains intentionally open until the live PR matrix and post-merge `main` run are recorded.

## Local gate evidence

Observed on macOS with CPython 3.12.13 and uv 0.11.31:

| Command | Result |
|---|---|
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed; 25 files already formatted |
| `uv run mypy src` | Passed; 13 source files, zero issues |
| `uv run pytest` | Passed; 185 tests, 100 percent statement and branch coverage |
| `uv run --locked pre-commit run --all-files` | Passed all four hooks, including the final staged-file rerun |
| `uv build` | Built wheel and source distribution successfully |
| `git diff --check` | Passed |
| `UV_OFFLINE=true uv run --locked pytest` | Passed; 185 tests, 100 percent statement and branch coverage |

The recurring workspace file-provider warning about replacing the `.venv` discovery link remains non-fatal; uv resolves the configured centralized environment and every command above exits successfully.

## Deferred aggregate invariants and residual risk

- F002 validates only invariants within one record. Parent-block existence, cross-record reference existence, relation graph properties and graph-wide deduplication remain explicit aggregate/service responsibilities in later work packages.
- Frozen Pydantic models prevent attribute replacement, but nested JSON extension/structured mappings are validated snapshots rather than deeply immutable containers. Identity helpers construct fresh explicit preimages and do not hash entire models.
- SHA-256 content identity proves integrity/equality under the documented projection, not authorship, authorization or trust.
- Three-platform portability is not claimed from local evidence; the publication fields below must be populated from the actual pull-request and post-merge workflow runs.

### Publication evidence fields

- Pull request: pending publication after local convergence
- Pull-request matrix run: pending publication after local convergence
- Linux job: pending publication after local convergence
- macOS job: pending publication after local convergence
- Windows job: pending publication after local convergence
- Post-merge `main` run: pending merge
