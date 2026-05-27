"""Split a multi-page PDF into per-page PNG images.

PyMuPDF handles all major PDF dialects including scanned exam papers.
Pages are rasterized at 200 DPI by default — high enough for handwriting
OCR, low enough to keep crops under a few hundred KB each.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import fitz  # PyMuPDF


def split_pdf_to_pages(pdf_path: str, output_dir: str, dpi: int = 200) -> list[str]:
    """Rasterize each page of a PDF and write to output_dir.

    Returns a list of page image paths in page order.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    paths: list[str] = []
    zoom = dpi / 72.0  # PyMuPDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)
    prefix = uuid.uuid4().hex[:8]

    try:
        for page_idx in range(doc.page_count):
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out = output_dir / f"{pdf_path.stem}_{prefix}_p{page_idx + 1:03d}.png"
            pix.save(str(out))
            paths.append(str(out))
    finally:
        doc.close()
    return paths
