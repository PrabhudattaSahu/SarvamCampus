"""Provider registry — build the OCR / LLM / TTS engines named in settings.

This is the single place that knows which concrete classes exist. To add an
engine: write the class, add a branch here, and set the matching env var.
"""
from __future__ import annotations

from ..config import Settings
from .base import LLMProvider, OCRProvider, TTSProvider
from .llm import MockLLM, OpenAICompatibleLLM
from .ocr import MockOCR, VisionLLMOCR
from .tts import MockTTS, OpenAICompatibleTTS


class Providers:
    def __init__(self, llm: LLMProvider, ocr: OCRProvider, tts: TTSProvider):
        self.llm = llm
        self.ocr = ocr
        self.tts = tts


def build_llm(settings: Settings) -> LLMProvider:
    name = settings.llm_provider.lower()
    if name == "mock":
        return MockLLM(settings)
    if name == "openai_compatible":
        return OpenAICompatibleLLM(settings)
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")


def build_tts(settings: Settings) -> TTSProvider:
    name = settings.tts_provider.lower()
    if name == "mock":
        return MockTTS(settings)
    if name == "openai_compatible":
        return OpenAICompatibleTTS(settings)
    raise ValueError(f"Unknown TTS_PROVIDER: {settings.tts_provider!r}")


def build_ocr(settings: Settings, llm: LLMProvider) -> OCRProvider:
    name = settings.ocr_provider.lower()
    if name == "mock":
        return MockOCR(settings)
    if name == "vision_llm":
        return VisionLLMOCR(settings, llm)
    raise ValueError(f"Unknown OCR_PROVIDER: {settings.ocr_provider!r}")


def build_providers(settings: Settings) -> Providers:
    llm = build_llm(settings)
    return Providers(llm=llm, ocr=build_ocr(settings, llm), tts=build_tts(settings))
