"""PDF → page images.

Handwriting OCR engines take images, not PDFs, so every uploaded PDF is first
rasterised page by page with PyMuPDF. We keep images in memory as PNG bytes;
for very large jobs you would stream them to object storage instead.
"""
from __future__ import annotations

import pymupdf


def pdf_page_count(path: str) -> int:
    with pymupdf.open(path) as doc:
        return doc.page_count


def pdf_to_png_pages(path: str, dpi: int = 200, max_pages: int = 40) -> list[bytes]:
    """Render the first `max_pages` pages of a PDF to PNG bytes.

    200 DPI is a good default for handwriting: enough detail for the OCR model
    without exploding payload size. Raise it for faint pencil.
    """
    images: list[bytes] = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
    return images
