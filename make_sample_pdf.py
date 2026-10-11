#!/usr/bin/env python3
"""Generate a sample 'handwritten-looking' PDF so you can try the app instantly.

    python scripts/make_sample_pdf.py            # -> samples/handwritten_sample.pdf

It renders typed text with a hand-drawn slant and jitter to *stand in* for real
handwriting — the mock OCR ignores the pixels anyway. Point the app at a real
scanned handwriting PDF when you want to test an actual OCR engine.
"""
from __future__ import annotations

import random
from pathlib import Path

import pymupdf

LINES = [
    "Cell Biology - handwritten notes",
    "",
    "The cell is the basic unit of life.",
    "First observed by Robert Hooke (1665).",
    "",
    "Plasma membrane:",
    "  - selectively permeable phospholipid bilayer",
    "  - fluid-mosaic model",
    "",
    "Organelles:",
    "  Nucleus  -> stores DNA, controls the cell",
    "  Mitochondria -> produce ATP by respiration",
    "  Ribosomes -> build proteins",
    "  ER + Golgi -> process and ship proteins",
    "",
    "More energy needed => more mitochondria!",
]


def main() -> int:
    rng = random.Random(7)
    out = Path("samples")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "handwritten_sample.pdf"

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 at 72 dpi
    y = 70
    for line in LINES:
        if line:
            # small jitter + a slight shear so it reads as "handwritten-ish"
            x = 60 + rng.uniform(-2, 2)
            yy = y + rng.uniform(-1, 1)
            shear = rng.uniform(0.10, 0.22)
            try:
                page.insert_text(
                    (x, yy), line, fontsize=15, fontname="times-italic",
                    morph=(pymupdf.Point(x, yy), pymupdf.Matrix(1, 0, shear, 1, 0, 0)),
                )
            except Exception:  # never let cosmetics break the generator
                page.insert_text((x, yy), line, fontsize=15, fontname="times-italic")
        y += 26
    doc.save(str(path))
    doc.close()
    print(f"Wrote {path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
