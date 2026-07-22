#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="$(tr -d '[:space:]' < spec-kit/PINNED_VERSION.txt)"

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is required. Install uv first, then rerun this script." >&2
  exit 1
fi

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Warning: the Git working tree has changes. Commit or back them up before continuing." >&2
  fi
else
  echo "Warning: initialize and commit a Git repository before implementation for full traceability." >&2
fi

echo "Installing GitHub Spec Kit specify-cli==$VERSION ..."
uv tool install "specify-cli==$VERSION" --force

echo "Initializing Spec Kit for Codex in the existing repository ..."
specify init --here --force --integration codex --ignore-agent-tools

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Error: Python is required to apply the OpenARDP overlay." >&2
  exit 1
fi

"$PYTHON_BIN" scripts/apply-speckit-overlay.py

echo
echo "Spec Kit version:"
specify version

echo
echo "Integration status:"
specify integration status || {
  echo "Spec Kit reported an integration error. Review the output before using Codex." >&2
  exit 1
}

echo
echo "Bootstrap complete."
echo "Next: open Codex in this repository and paste spec-kit/FIRST_CODEX_SESSION.md."
