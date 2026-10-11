"""Provider interfaces.

The pipeline only ever talks to these three protocols, so you can swap the OCR
engine, the LLM, or the TTS voice without touching any pipeline code. Add a new
engine by writing a class that satisfies the relevant protocol and registering
it in `registry.py`.
"""
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class OCRProvider(Protocol):
    name: str

    def ocr_pages(self, images: Sequence[bytes], lang: str = "auto") -> list[str]:
        """Recognise text on each page image; return one string per page,
        in the same order. `lang` is a BCP-47 hint like 'en-IN' or 'hi-IN'."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        """Single-turn text completion. With json_mode=True the response is
        expected to be a JSON object."""
        ...

    def complete_vision(self, prompt: str, images: Sequence[bytes], system: str = "") -> str:
        """Completion that also sees one or more PNG images (used for OCR)."""
        ...


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, lang: str, out_path: str) -> str:
        """Render `text` to speech, write audio to `out_path`, return the path."""
        ...
