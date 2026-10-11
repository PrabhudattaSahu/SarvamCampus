"""Text-to-speech providers for the audio overview.

`OpenAICompatibleTTS` posts to the standard `/audio/speech` shape, which OpenAI,
Sarvam AI and several others expose. `MockTTS` writes a short silent WAV so the
pipeline produces a real, playable file with no API key.
"""
from __future__ import annotations

import struct
import wave

import httpx

from ..config import Settings


class MockTTS:
    name = "mock"

    def __init__(self, settings: Settings):
        self.s = settings

    def synthesize(self, text: str, lang: str, out_path: str) -> str:
        # A quiet, valid WAV whose length scales with the script so the UI has
        # something real to play. Replace with a real engine for actual speech.
        seconds = max(2.0, min(30.0, len(text) / 15.0))
        rate = 16000
        frames = int(seconds * rate)
        with wave.open(out_path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"\x00\x00" * frames)
        return out_path


class OpenAICompatibleTTS:
    name = "openai_compatible"

    def __init__(self, settings: Settings):
        self.s = settings
        if not settings.tts_api_key:
            raise RuntimeError(
                "TTS_API_KEY (or LLM_API_KEY) is empty. Set it, or use TTS_PROVIDER=mock."
            )

    def synthesize(self, text: str, lang: str, out_path: str) -> str:
        url = f"{self.s.tts_base_url.rstrip('/')}/audio/speech"
        payload = {
            "model": self.s.tts_model,
            "voice": self.s.tts_voice,
            "input": text,
            "response_format": "mp3",
        }
        # Some Indic-first TTS endpoints expect an explicit target language.
        if lang and lang not in ("auto", ""):
            payload["target_language_code"] = lang
        headers = {"Authorization": f"Bearer {self.s.tts_api_key}"}
        with httpx.Client(timeout=self.s.request_timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            with open(out_path, "wb") as fh:
                fh.write(resp.content)
        return out_path
