"""Generate deterministic redistributable rich-document fixtures for F007."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

GENERATOR_VERSION = "1"
FIXED_TIME = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _normalized_zip(path: Path) -> bytes:
    """Return a ZIP with stable ordering, metadata and compression."""
    with zipfile.ZipFile(path) as source:
        members = [(name, source.read(name)) for name in sorted(source.namelist())]
    with tempfile.SpooledTemporaryFile() as stream:
        with zipfile.ZipFile(
            stream,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as target:
            for name, payload in members:
                info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                target.writestr(info, payload)
        stream.seek(0)
        return stream.read()


def _docx_bytes(work: Path) -> bytes:
    """Build one title, paragraph and table with python-docx."""
    from docx import Document

    document = Document()
    document.core_properties.author = "OpenARDP"
    document.core_properties.created = FIXED_TIME
    document.core_properties.modified = FIXED_TIME
    document.core_properties.title = "Synthetic DOCX"
    document.add_heading("Synthetic DOCX", level=1)
    document.add_paragraph("A deterministic paragraph for native evidence.")
    table = document.add_table(rows=2, cols=2)
    for row_index, row in enumerate(table.rows):
        for column_index, cell in enumerate(row.cells):
            cell.text = f"R{row_index + 1}C{column_index + 1}"
    raw = work / "raw.docx"
    document.save(raw)
    return _normalized_zip(raw)


def _pptx_bytes(work: Path) -> bytes:
    """Build one title slide and one table slide with python-pptx."""
    from pptx import Presentation
    from pptx.util import Inches

    presentation = Presentation()
    presentation.core_properties.author = "OpenARDP"
    presentation.core_properties.created = FIXED_TIME
    presentation.core_properties.modified = FIXED_TIME
    presentation.core_properties.title = "Synthetic PPTX"

    title_slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    title_slide.shapes.title.text = "Synthetic PPTX"
    title_slide.placeholders[1].text = "A deterministic paragraph for native evidence."

    table_slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    table_slide.shapes.title.text = "Deterministic Table"
    table = table_slide.shapes.add_table(
        2,
        2,
        Inches(1),
        Inches(2),
        Inches(8),
        Inches(2),
    ).table
    for row_index in range(2):
        for column_index in range(2):
            table.cell(row_index, column_index).text = f"R{row_index + 1}C{column_index + 1}"
    raw = work / "raw.pptx"
    presentation.save(raw)
    return _normalized_zip(raw)


def _pdf_bytes() -> bytes:
    """Build one minimal deterministic redistributable PDF without model assets."""
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length 68 >>\nstream\n"
            b"BT /F1 18 Tf 72 720 Td (Synthetic PDF evidence fixture.) Tj ET\n"
            b"endstream"
        ),
    )
    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{number} 0 obj\n".encode())
        payload.extend(body)
        payload.extend(b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode())
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(payload)


def generate(output: Path) -> dict[str, object]:
    """Generate all fixtures and return their deterministic provenance manifest."""
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="openardp-rich-fixtures-") as directory:
        work = Path(directory)
        fixtures = {
            "synthetic.docx": _docx_bytes(work),
            "synthetic.pdf": _pdf_bytes(),
            "synthetic.pptx": _pptx_bytes(work),
        }
    records = []
    for name, payload in sorted(fixtures.items()):
        (output / name).write_bytes(payload)
        records.append(
            {
                "byte_length": len(payload),
                "license": "CC0-1.0",
                "name": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest: dict[str, object] = {
        "generated_at": "2026-07-26T12:00:00Z",
        "generator": "tests/fixtures/rich/generate_fixtures.py",
        "generator_version": GENERATOR_VERSION,
        "records": records,
    }
    (output / "fixture-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    """Generate fixtures into the requested or adjacent directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    arguments = parser.parse_args()
    generate(arguments.output)


if __name__ == "__main__":
    main()
