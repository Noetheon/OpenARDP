"""Apply OpenARDP project-specific files after GitHub Spec Kit initialization."""

from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    """Copy the reviewed OpenARDP overlay into an initialized Spec Kit tree."""
    root = Path(__file__).resolve().parents[1]
    specify_dir = root / ".specify"
    if not specify_dir.is_dir():
        raise SystemExit(
            "Spec Kit is not initialized. Run `specify init --here --force "
            "--integration codex` first."
        )

    source = root / "spec-kit" / "CONSTITUTION_SOURCE.md"
    target = specify_dir / "memory" / "constitution.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

    source_map = specify_dir / "memory" / "openardp-source-map.md"
    source_map.write_text(
        "# OpenARDP source-of-truth map\n\n"
        "This file is project-specific and is not a replacement for the constitution.\n\n"
        "1. `.specify/memory/constitution.md`, legal/security constraints\n"
        "2. accepted ADRs and public schemas\n"
        "3. project requirements and architecture in `docs/`\n"
        "4. active feature `spec.md` and `plan.md`\n"
        "5. `tasks.md`\n"
        "6. implementation\n\n"
        "Conflicts are fixed at their originating level and propagated downstream.\n",
        encoding="utf-8",
    )

    marker = specify_dir / "OPENARDP_OVERLAY_APPLIED"
    marker.write_text(
        "OpenARDP Spec Kit overlay applied.\n"
        "Authoritative source: spec-kit/CONSTITUTION_SOURCE.md\n",
        encoding="utf-8",
    )

    print(f"Copied constitution to {target.relative_to(root)}")
    print(f"Wrote {source_map.relative_to(root)}")
    print(f"Wrote {marker.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
