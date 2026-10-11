"""OCR providers — turn page images into text.

Handwriting is the hard part of this product. Two things matter when you pick
an engine: (1) does it handle *handwriting*, not just printed text, and (2) does
it cover your Indic scripts. Options, roughly in order of handwriting quality:

  * A multimodal LLM (GPT-4o / Gemini / Sarvam Vision) — best on messy
    handwriting and mixed scripts; this is what `VisionLLMOCR` uses.
  * Cloud document-AI APIs (Google Document AI, Azure Document Intelligence,
    AWS Textract) — strong, but handwriting support varies by script.
  * Classic engines (Tesseract) — fast and free, weak on handwriting.

`MockOCR` returns canned text so the app runs offline.
"""
from __future__ import annotations

from ..config import Settings

_OCR_SYSTEM = (
    "You are an expert OCR engine for handwritten study notes. Transcribe the "
    "handwriting exactly as written, preserving headings, bullet points, "
    "numbered lists, formulas and diagrams-as-text. Do not summarise, correct, "
    "translate or add anything. If a word is illegible, write [illegible]. "
    "Return plain text only."
)


class MockOCR:
    name = "mock"

    def __init__(self, settings: Settings):
        self.s = settings

    def ocr_pages(self, images, lang: str = "auto") -> list[str]:
        base = (
            "Handwritten notes (mock OCR). Cell Biology.\n"
            "The cell is the basic structural and functional unit of life; "
            "first observed by Robert Hooke in 1665.\n"
            "Plasma membrane: selectively permeable phospholipid bilayer "
            "(fluid-mosaic model).\n"
            "Organelles:\n"
            "- Nucleus: stores DNA, controls the cell.\n"
            "- Mitochondria: produce ATP by respiration.\n"
            "- Ribosomes: build proteins.\n"
            "- ER and Golgi: process and ship proteins and lipids."
        )
        return [f"{base}\n\n(page {i + 1})" for i in range(len(images))]


class VisionLLMOCR:
    """OCR via the LLM provider's vision capability (same endpoint as the LLM).

    Sends one page image at a time — handwriting recognition is more accurate
    page-by-page than batched, and it keeps requests within token limits.
    """

    name = "vision_llm"

    def __init__(self, settings: Settings, llm):
        self.s = settings
        self.llm = llm

    def ocr_pages(self, images, lang: str = "auto") -> list[str]:
        out: list[str] = []
        for i, img in enumerate(images):
            hint = "" if lang in ("auto", "") else f" The notes may be in {lang}."
            prompt = (
                f"Transcribe page {i + 1} of these handwritten notes.{hint}\n\n"
                "Output only the transcribed text."
            )
            out.append(self.llm.complete_vision(prompt, [img], system=_OCR_SYSTEM).strip())
        return out
