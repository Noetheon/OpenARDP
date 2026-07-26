# Quickstart: Validate Feature 005A

## Prerequisites

- Clean checkout of `codex/f005a-strategic-realignment`
- Python 3.12
- Repository-constrained `uv`
- No network access is required after locked dependencies are available

## 1. Confirm feature selection

```bash
uv run --locked python - <<'PY'
import json
from pathlib import Path

value = json.loads(Path(".specify/feature.json").read_text(encoding="utf-8"))
assert value == {"feature_directory": "specs/005A-strategic-realignment"}
PY
```

Expected: the command exits successfully.

## 2. Run focused governance contracts

```bash
uv run --locked pytest tests/test_repository_contract.py
```

Expected: constitution, roadmap, prompt, ADR, contract-example, claim-discipline, offline, and baseline repository checks pass.

## 3. Run authoritative quality gates

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked pytest
uv build
```

Expected: every command exits successfully, coverage remains at or above the repository threshold, and both distribution artifacts are produced.

## 4. Validate repository hygiene and JSON

```bash
git diff --check
uv run --locked python -m json.tool contracts/example-selection-receipt.json >/dev/null
git ls-files | grep -E '(^|/)(\\.DS_Store|openardp_codex_blueprint_v3_1)(/|$)' && exit 1 || true
```

Expected: no whitespace error, valid example JSON, and no blueprint package/platform metadata in tracked files.

## 5. Prove runtime neutrality

```bash
git diff --exit-code a23c07eb2a22efa7a4004d33cf00ab6cfd6fd027 -- \
  src schemas pyproject.toml uv.lock
```

Expected: no output and a zero exit status.

## 6. Review the authoritative sequence

```bash
uv run --locked python - <<'PY'
from pathlib import Path

feature_map = Path("spec-kit/FEATURE_MAP.md").read_text(encoding="utf-8")
expected = [
    "005A-strategic-realignment",
    "006-evidence-contract-foundation",
    "007-docling-native-adapter",
    "008-context-compiler-receipts",
    "009-read-only-mcp",
    "010-reconciliation-derivation-dag",
    "011-visual-evidence-escalation",
    "012-local-watcher-and-jobs",
    "013-retention-recovery-migrations",
    "014-export-interchange-experiment",
    "015-benchmark-security-release-gate",
    "016-alternate-parser-conformance-spike",
    "017-microsoft-graph-design-spike",
]
positions = [feature_map.index(name) for name in expected]
assert positions == sorted(positions)
PY
```

Expected: the feature order is present exactly in dependency order.

## 7. Convergence review

Run the feature analysis and convergence checks against `spec.md`, `plan.md`, `tasks.md`, the amended constitution, accepted ADRs, canonical roadmap, active prompts, and repository diff. No critical or high finding may remain.
