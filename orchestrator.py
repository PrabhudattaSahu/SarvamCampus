"""Pipeline orchestration: PDF → structured, multilingual study kit.

This is the one function the API and the CLI both call. It is deliberately
plain synchronous code — for production you would run each job on a worker
(Celery / RQ / arq) and stream progress over WebSockets; here progress is
reported through a callback and persisted by the store.
"""
from __future__ import annotations

from typing import Any, Callable

from ..config import Settings
from ..providers.registry import Providers
from . import steps
from .languages import lang_name
from .pdf import pdf_to_png_pages

ProgressFn = Callable[[str, int], None]


def run_pipeline(
    job_id: str,
    pdf_paths: list[str],
    target_lang: str,
    source_lang: str,
    settings: Settings,
    providers: Providers,
    store,
    make_audio: bool = True,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Run the full pipeline and return the artifact bundle.

    Steps: rasterise → OCR → structure → short notes / flashcards / quiz →
    audio script → speech. Everything is written in `target_lang`.
    """

    def progress(msg: str, pct: int) -> None:
        if on_progress:
            on_progress(msg, pct)

    # 1. Rasterise every uploaded PDF into page images.
    progress("Rendering PDF pages", 5)
    images: list[bytes] = []
    for path in pdf_paths:
        images.extend(
            pdf_to_png_pages(path, dpi=settings.render_dpi, max_pages=settings.max_pages)
        )
    if not images:
        raise ValueError("No pages found in the uploaded PDF(s).")

    # 2. OCR the handwriting.
    progress(f"Reading handwriting across {len(images)} page(s)", 20)
    page_texts = providers.ocr.ocr_pages(images, lang=source_lang)
    raw_text = "\n\n".join(page_texts).strip()

    # 3. Structure the notes, written directly in the target language.
    progress(f"Structuring notes in {lang_name(target_lang)}", 45)
    notes = steps.structure_notes(providers.llm, raw_text, target_lang)

    # 4. Derive the rest of the study kit from the structured notes.
    progress("Writing short notes", 60)
    short_notes = steps.make_short_notes(providers.llm, notes, target_lang)

    progress("Building flashcards", 70)
    flashcards = steps.make_flashcards(providers.llm, notes, target_lang)

    progress("Writing quiz", 78)
    quiz = steps.make_quiz(providers.llm, notes, target_lang)

    progress("Writing audio script", 85)
    audio_script = steps.make_audio_script(providers.llm, notes, target_lang)

    # 5. Text-to-speech.
    audio_file = None
    if make_audio:
        progress("Generating audio overview", 92)
        out_name = "audio_overview.mp3"
        out_path = store.artifact_path(job_id, out_name)
        providers.tts.synthesize(audio_script.get("script", ""), target_lang, out_path)
        audio_file = out_name

    progress("Done", 100)
    return {
        "job_id": job_id,
        "language": target_lang,
        "language_name": lang_name(target_lang),
        "pages": len(images),
        "raw_text": raw_text,
        "structured_notes": notes,
        "notes_markdown": steps.notes_to_markdown(notes),
        "short_notes": short_notes,
        "flashcards": flashcards,
        "quiz": quiz,
        "audio_script": audio_script,
        "audio_file": audio_file,
    }
