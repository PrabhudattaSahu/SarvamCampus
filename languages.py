"""Supported output languages and helpers.

Indic-first: the default set covers English plus the major Indian languages,
which is where handwriting-OCR + translation quality is hardest and where a
product like this earns its keep.
"""
from __future__ import annotations

# code -> human name used in prompts
LANGUAGES: dict[str, str] = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "bn-IN": "Bengali",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "pa-IN": "Punjabi",
    "or-IN": "Odia",
    "as-IN": "Assamese",
    "ur-IN": "Urdu",
}

DEFAULT_LANGUAGE = "en-IN"


def lang_name(code: str) -> str:
    """Human-readable name for a language code, falling back to the code."""
    return LANGUAGES.get(code, code)


def is_supported(code: str) -> bool:
    return code in LANGUAGES
