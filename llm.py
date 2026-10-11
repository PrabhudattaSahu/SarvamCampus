"""LLM providers.

`OpenAICompatibleLLM` speaks the standard OpenAI `/chat/completions` shape, so
the same class drives OpenAI, Azure, Sarvam AI, Groq, Together, Fireworks, a
local vLLM server, Ollama, and anything else that mimics it — you only change
`LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`.

`MockLLM` returns canned-but-realistic output so the pipeline runs with no keys.
"""
from __future__ import annotations

import base64
import json

import httpx

from ..config import Settings


def strip_code_fence(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences; unwrap before parsing."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
        t = t.lstrip("json").strip() if t.lstrip().startswith("json") else t.strip()
    return t.strip()


class OpenAICompatibleLLM:
    name = "openai_compatible"

    def __init__(self, settings: Settings):
        self.s = settings
        if not settings.llm_api_key:
            raise RuntimeError(
                "LLM_API_KEY is empty. Set it in .env, or use LLM_PROVIDER=mock."
            )

    def _url(self) -> str:
        return f"{self.s.llm_base_url.rstrip('/')}/chat/completions"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.s.llm_api_key}"}

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.s.llm_model, "messages": messages, "temperature": 0.2}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        with httpx.Client(timeout=self.s.request_timeout) as client:
            resp = client.post(self._url(), headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def complete_vision(self, prompt: str, images, system: str = "") -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            b64 = base64.b64encode(img).decode("ascii")
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})
        payload = {"model": self.s.llm_vision_model, "messages": messages, "temperature": 0.1}
        with httpx.Client(timeout=self.s.request_timeout) as client:
            resp = client.post(self._url(), headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Offline mock
# ---------------------------------------------------------------------------

_MOCK_STRUCTURE = {
    "title": "Cell Biology — Handwritten Notes",
    "language": "en",
    "summary": (
        "An introduction to the cell: its basic structure, the role of the "
        "plasma membrane, and the major organelles with their functions."
    ),
    "sections": [
        {
            "heading": "What is a Cell",
            "points": [
                "The cell is the smallest unit of life that can function on its own.",
                "All living organisms are made of one or more cells.",
                "Cells were first observed by Robert Hooke in 1665.",
            ],
            "detail": (
                "Cells are the basic structural and functional unit of every "
                "living thing. Unicellular organisms are a single cell; "
                "multicellular organisms contain many specialised cells."
            ),
        },
        {
            "heading": "Plasma Membrane",
            "points": [
                "A selectively permeable barrier around the cell.",
                "Made of a phospholipid bilayer with embedded proteins.",
                "Controls what enters and leaves the cell.",
            ],
            "detail": (
                "The plasma membrane follows the fluid-mosaic model: a "
                "phospholipid bilayer studded with proteins and cholesterol "
                "that regulates transport into and out of the cell."
            ),
        },
        {
            "heading": "Key Organelles",
            "points": [
                "Nucleus — stores DNA and directs activity.",
                "Mitochondria — produce ATP, the cell's energy currency.",
                "Ribosomes — build proteins from amino acids.",
                "Endoplasmic reticulum — transports and folds proteins and lipids.",
            ],
            "detail": (
                "Each organelle has a specialised job. Mitochondria carry out "
                "cellular respiration to make ATP, ribosomes synthesise "
                "proteins, and the endoplasmic reticulum and Golgi apparatus "
                "process and ship those proteins."
            ),
        },
    ],
    "key_terms": [
        {"term": "Cell", "definition": "The basic structural and functional unit of life."},
        {"term": "Plasma membrane", "definition": "A selectively permeable phospholipid bilayer around the cell."},
        {"term": "Mitochondria", "definition": "Organelles that carry out respiration to produce ATP."},
        {"term": "Ribosome", "definition": "The site of protein synthesis in the cell."},
        {"term": "ATP", "definition": "Adenosine triphosphate — the cell's energy currency."},
    ],
    "formulas": [],
    "questions_to_explore": [
        "How does the fluid-mosaic model explain selective permeability?",
        "Why do cells with high energy demand contain more mitochondria?",
    ],
}

_MOCK_SHORT = {
    "title": "Cell Biology — Short Notes",
    "bullets": [
        "Cell = smallest self-functioning unit of life; seen by Hooke (1665).",
        "Plasma membrane: phospholipid bilayer, selectively permeable, fluid-mosaic model.",
        "Nucleus → DNA + control; Mitochondria → ATP; Ribosomes → proteins.",
        "ER + Golgi → process and ship proteins and lipids.",
        "More energy demand ⇒ more mitochondria.",
    ],
}

_MOCK_FLASHCARDS = {
    "cards": [
        {"front": "What is a cell?", "back": "The basic structural and functional unit of life."},
        {"front": "Who first observed cells?", "back": "Robert Hooke, in 1665."},
        {"front": "What is the plasma membrane made of?", "back": "A phospholipid bilayer with embedded proteins (fluid-mosaic model)."},
        {"front": "Function of mitochondria?", "back": "Cellular respiration to produce ATP, the energy currency."},
        {"front": "Function of ribosomes?", "back": "Protein synthesis — they assemble proteins from amino acids."},
        {"front": "What does ATP stand for?", "back": "Adenosine triphosphate."},
    ],
}

_MOCK_QUIZ = {
    "questions": [
        {
            "question": "Which organelle produces ATP through cellular respiration?",
            "options": ["Ribosome", "Mitochondria", "Nucleus", "Golgi apparatus"],
            "answer_index": 1,
            "explanation": "Mitochondria carry out respiration to generate ATP.",
        },
        {
            "question": "The plasma membrane is best described as:",
            "options": ["A rigid cellulose wall", "A selectively permeable phospholipid bilayer", "A protein-only shell", "A single lipid layer"],
            "answer_index": 1,
            "explanation": "It is a selectively permeable phospholipid bilayer (fluid-mosaic model).",
        },
        {
            "question": "Where are proteins synthesised in a cell?",
            "options": ["Ribosomes", "Lysosomes", "Vacuoles", "Centrioles"],
            "answer_index": 0,
            "explanation": "Ribosomes are the site of protein synthesis.",
        },
        {
            "question": "Who first observed cells under a microscope?",
            "options": ["Charles Darwin", "Robert Hooke", "Louis Pasteur", "Gregor Mendel"],
            "answer_index": 1,
            "explanation": "Robert Hooke observed cork cells in 1665.",
        },
    ],
}

_MOCK_AUDIO = {
    "title": "Cell Biology — Audio Overview",
    "script": (
        "Welcome to your audio overview of Cell Biology. "
        "First, the cell. A cell is the smallest unit of life that can function "
        "on its own, and it was first observed by Robert Hooke in sixteen sixty-five. "
        "Next, the plasma membrane. It is a selectively permeable phospholipid "
        "bilayer, described by the fluid-mosaic model, and it controls what enters "
        "and leaves the cell. "
        "Finally, the organelles. The nucleus stores DNA and directs the cell. "
        "Mitochondria carry out respiration to make ATP, the cell's energy currency. "
        "Ribosomes build proteins, while the endoplasmic reticulum and Golgi "
        "apparatus process and ship them. "
        "Remember the rule: the more energy a cell needs, the more mitochondria it "
        "contains. That's your overview — revise the flashcards next."
    ),
}


class MockLLM:
    """Deterministic offline stand-in. Dispatches on the `TASK:` marker that
    every pipeline prompt begins with."""

    name = "mock"

    def __init__(self, settings: Settings):
        self.s = settings

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        task = ""
        for line in prompt.splitlines():
            if line.strip().upper().startswith("TASK:"):
                task = line.split(":", 1)[1].strip().lower()
                break
        table = {
            "structure": _MOCK_STRUCTURE,
            "short_notes": _MOCK_SHORT,
            "flashcards": _MOCK_FLASHCARDS,
            "quiz": _MOCK_QUIZ,
            "audio_script": _MOCK_AUDIO,
        }
        if task == "translate":
            return json.dumps({"translated": "（mock translation）" + prompt[-200:]})
        return json.dumps(table.get(task, {"note": "mock"}))

    def complete_vision(self, prompt: str, images, system: str = "") -> str:
        return (
            "Handwritten notes (mock OCR). Cell Biology. "
            "The cell is the basic unit of life; first observed by Robert Hooke in 1665. "
            "The plasma membrane is a selectively permeable phospholipid bilayer "
            "(fluid-mosaic model). Key organelles: nucleus stores DNA and controls the "
            "cell; mitochondria produce ATP by respiration; ribosomes make proteins; "
            "the endoplasmic reticulum and Golgi process and transport proteins."
        )
