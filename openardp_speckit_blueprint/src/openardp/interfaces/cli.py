"""CLI placeholder for Work Package 0/1.

The implementation is deliberately small. Follow docs/09_CODEX_EXECUTION_PLAN.md rather than
adding ad-hoc features here.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from openardp import __version__
from openardp.core import file_sha256

app = typer.Typer(no_args_is_help=True, help="OpenARDP reference CLI")


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@app.command()
def hash(path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True)) -> None:
    """Compute the source identity primitive used by later ingestion work packages."""
    digest, length = file_sha256(path)
    typer.echo(json.dumps({"path": str(path), "sha256": digest, "byte_length": length}))


if __name__ == "__main__":
    app()
