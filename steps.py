"""The LLM steps: raw text → structured notes → study kit.

Each function is one focused prompt that returns JSON. Prompts begin with a
`TASK:` marker so the offline MockLLM can return the right canned payload, and
they instruct the model to answer directly in the target language — structuring
in-language beats translating afterwards.
"""
from __future__ import annotations

import json
from typing import Any

from ..providers.llm import strip_code_fence
from .languages import lang_name

_SYSTEM = (
    "You are an expert teacher and study-notes editor. You turn messy "
    "handwritten notes into clean, well-organised study material. Always "
    "answer with a single valid JSON object and nothing else."
)


def _parse(text: str) -> dict[str, Any]:
    try:
        return json.loads(strip_code_fence(text))
    except json.JSONDecodeError:
        # Last resort: hand back the raw text so the job does not hard-fail.
        return {"_raw": text, "_error": "model did not return valid JSON"}


def structure_notes(llm, raw_text: str, target_lang: str) -> dict[str, Any]:
    lang = lang_name(target_lang)
    prompt = f"""TASK:structure
Rewrite the raw notes below into structured study notes, written entirely in {lang}.

Return JSON with this exact shape:
{{
  "title": "short descriptive title",
  "language": "{target_lang}",
  "summary": "2-3 sentence overview",
  "sections": [{{"heading": "...", "points": ["..."], "detail": "a short paragraph"}}],
  "key_terms": [{{"term": "...", "definition": "..."}}],
  "formulas": ["... (omit if none)"],
  "questions_to_explore": ["..."]
}}

Rules: keep the author's meaning; fix obvious spelling; organise into logical
sections; do not invent facts that are not in the notes.

RAW NOTES:
\"\"\"
{raw_text}
\"\"\"
"""
    return _parse(llm.complete(prompt, system=_SYSTEM, json_mode=True))


def make_short_notes(llm, notes: dict, target_lang: str) -> dict[str, Any]:
    lang = lang_name(target_lang)
    prompt = f"""TASK:short_notes
From the structured notes below, write crisp revision bullets in {lang} —
the kind a student reads the night before an exam.

Return JSON: {{"title": "...", "bullets": ["...", "..."]}}
Aim for 6-12 bullets, one idea each, no fluff.

STRUCTURED NOTES:
{json.dumps(notes, ensure_ascii=False)}
"""
    return _parse(llm.complete(prompt, system=_SYSTEM, json_mode=True))


def make_flashcards(llm, notes: dict, target_lang: str) -> dict[str, Any]:
    lang = lang_name(target_lang)
    prompt = f"""TASK:flashcards
Create active-recall flashcards from the structured notes below, in {lang}.

Return JSON: {{"cards": [{{"front": "question or term", "back": "concise answer"}}]}}
Make 8-15 cards. One fact per card. Questions on the front, answers on the back.

STRUCTURED NOTES:
{json.dumps(notes, ensure_ascii=False)}
"""
    return _parse(llm.complete(prompt, system=_SYSTEM, json_mode=True))


def make_quiz(llm, notes: dict, target_lang: str, n: int = 8) -> dict[str, Any]:
    lang = lang_name(target_lang)
    prompt = f"""TASK:quiz
Write a {n}-question multiple-choice quiz from the structured notes below, in {lang}.

Return JSON:
{{"questions": [{{"question": "...", "options": ["A","B","C","D"],
  "answer_index": 0, "explanation": "why the answer is correct"}}]}}
Each question must have exactly 4 options and one correct answer_index (0-3).

STRUCTURED NOTES:
{json.dumps(notes, ensure_ascii=False)}
"""
    return _parse(llm.complete(prompt, system=_SYSTEM, json_mode=True))


def make_audio_script(llm, notes: dict, target_lang: str) -> dict[str, Any]:
    lang = lang_name(target_lang)
    prompt = f"""TASK:audio_script
Write a spoken-word audio overview of the notes below, in {lang}, for a student
listening on the go. Conversational, warm, 2-4 minutes when read aloud.

Return JSON: {{"title": "...", "script": "the full narration text"}}
No stage directions, no markdown — plain sentences meant to be read aloud.

STRUCTURED NOTES:
{json.dumps(notes, ensure_ascii=False)}
"""
    return _parse(llm.complete(prompt, system=_SYSTEM, json_mode=True))


def translate_payload(llm, payload: dict, target_lang: str) -> dict[str, Any]:
    """Translate any artifact to another language, preserving JSON structure."""
    lang = lang_name(target_lang)
    prompt = f"""TASK:translate
Translate every string value in this JSON into {lang}. Keep the JSON keys and
structure exactly the same; translate only the values.

JSON:
{json.dumps(payload, ensure_ascii=False)}
"""
    return _parse(llm.complete(prompt, system=_SYSTEM, json_mode=True))


def notes_to_markdown(notes: dict) -> str:
    """Render structured notes as a clean Markdown file for download."""
    if "_raw" in notes:
        return notes["_raw"]
    lines: list[str] = []
    title = notes.get("title", "Study Notes")
    lines.append(f"# {title}\n")
    if notes.get("summary"):
        lines.append(f"_{notes['summary']}_\n")
    for sec in notes.get("sections", []):
        lines.append(f"\n## {sec.get('heading', '')}\n")
        for p in sec.get("points", []):
            lines.append(f"- {p}")
        if sec.get("detail"):
            lines.append(f"\n{sec['detail']}")
    if notes.get("key_terms"):
        lines.append("\n## Key Terms\n")
        for kt in notes["key_terms"]:
            lines.append(f"- **{kt.get('term', '')}** — {kt.get('definition', '')}")
    if notes.get("formulas"):
        lines.append("\n## Formulas\n")
        for f in notes["formulas"]:
            lines.append(f"- {f}")
    if notes.get("questions_to_explore"):
        lines.append("\n## Questions to Explore\n")
        for q in notes["questions_to_explore"]:
            lines.append(f"- {q}")
    return "\n".join(lines) + "\n"
