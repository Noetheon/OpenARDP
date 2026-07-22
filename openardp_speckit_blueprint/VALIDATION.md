# Blueprint validation status

Validated on 2026-07-22 in the artifact-generation environment.

## Passed offline checks

- Python source, tests and helper scripts compile successfully.
- Four scaffold tests pass with `PYTHONPATH=src python -m pytest -q`.
- All included JSON Schemas pass `Draft202012Validator.check_schema`.
- The Spec Kit overlay script was executed against a temporary `.specify/` directory.
- The generated constitution was byte-identical to `spec-kit/CONSTITUTION_SOURCE.md`.
- The overlay marker and source-of-truth map were created successfully.
- `scripts/bootstrap-speckit.sh` passes `bash -n` syntax validation.
- All relative Markdown links resolve to existing files.
- All 14 work packages have a corresponding bounded Spec Kit feature prompt.
- The repository contains no generated `__pycache__` directories.

## Checks deferred to the user's implementation environment

The full bootstrap attempted to install the pinned `specify-cli==0.13.3`, but the isolated artifact environment's internal
package gateway returned HTTP 503. Therefore the following could not be executed end-to-end here:

- installation of the pinned Spec Kit CLI;
- `specify init --here --force --integration codex`;
- verification of generated `.agents/skills/` files;
- `specify integration status` after real initialization;
- PowerShell parser validation because `pwsh` is not installed;
- `uv sync`, Ruff and strict mypy using downloaded project dependencies.

The failure was environmental rather than a detected project or script error. The bootstrap scripts stop on installation
failure and make no claim that Spec Kit was initialized.

## Required first-machine validation

Before implementation, run:

```bash
bash scripts/bootstrap-speckit.sh
specify version
specify integration status
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

On Windows, use `scripts/bootstrap-speckit.ps1` and inspect any PowerShell error before continuing.
