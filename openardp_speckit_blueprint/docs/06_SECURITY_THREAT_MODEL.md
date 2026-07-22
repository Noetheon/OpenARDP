# Security threat model

## 1. Assets

- source documents and embedded files;
- extracted confidential text and assets;
- credentials for model/cloud/Microsoft Graph access;
- tenant permissions and ACL snapshots;
- derived summaries/embeddings;
- integrity and provenance records;
- agent tool authority.

## 2. Trust boundaries

```text
untrusted file bytes
→ sandboxed parser worker
→ validated normalized IR
→ derived enrichment providers
→ catalog/artifact store
→ retrieval/context compiler
→ agent client
```

Each crossing requires validation and least privilege.

## 3. Primary threats and controls

### Malicious document/parser exploitation

Threats: malformed PDF, decompression bomb, parser RCE, memory exhaustion, infinite recursion.

Controls:

- file size, page, object, nesting and decompressed-size limits;
- process/container isolation;
- no macro execution;
- no external link fetching by default;
- CPU/memory/time quotas;
- supported media allowlist;
- dependency patching and fuzz/regression corpus.

### Path traversal and unsafe sources

- canonicalize paths;
- restrict local roots;
- reject symlink escapes unless explicitly configured;
- never interpret archive paths without safe extraction checks;
- source connectors return streams, not arbitrary shell commands.

### Indirect prompt injection

Threat: document text tells an agent to ignore policy, disclose data or use tools.

Controls:

- all source content labelled `role=data`, `instruction_execution_allowed=false`;
- separate system instructions from document evidence;
- no document-driven tool dispatch;
- constrain MCP to read-only tools initially;
- render untrusted content with explicit boundaries;
- require confirmation/policy checks for future side effects;
- adversarial fixtures in CI;
- do not store unvalidated document instructions in agent memory.

### Poisoned derived artifacts

- preserve exact source separately;
- derived artifact records include generator and dependencies;
- summaries cannot overwrite canonical blocks;
- model outputs pass schema and claim/evidence validation;
- low-confidence artifacts are excluded from high-assurance modes.

### Stale or mixed versions

- every bundle pins exact source versions;
- no cross-version block mixing unless requested and declared;
- freshness policy enforced before retrieval;
- atomic version commits.

### Data leakage

- local provider default;
- explicit per-provider data egress policy;
- secrets via OS keychain/env/managed identity, never config files;
- tenant/user namespace isolation;
- encrypt transport and enterprise storage;
- redact bodies from logs and traces;
- permission check at query time in enterprise mode.

### Supply chain

- lock dependencies;
- generate SBOM;
- dependency review and automated security updates;
- signed releases and SLSA provenance later;
- pin CI actions by commit SHA;
- REUSE/SPDX-compatible licensing metadata.

## 4. Security modes

### `standard`

Local trusted documents, read-only agent access.

### `untrusted`

Parser sandbox required, no external fetching, strict limits, model enrichment disabled by default.

### `high_assurance`

Only exact source/OCR with confidence threshold; summaries cannot satisfy evidence requirements; signed package verification;
all external providers disabled unless policy-approved.

## 5. Security acceptance tests

- prompt injection in visible text, white-on-white text, notes and image OCR;
- ZIP/path traversal payloads;
- oversized images and recursive archives;
- corrupt PDF/Office package;
- symlink escape;
- cross-document/tenant ID enumeration;
- stale derived artifact after source edit;
- malicious filenames/log injection;
- tool response size exhaustion;
- parser timeout and crash recovery.

## 6. Residual risk

No prompt-injection filter can guarantee that a general-purpose model will never be influenced by untrusted natural
language. The architecture reduces authority and separates data from instructions; it does not claim perfect prevention.
