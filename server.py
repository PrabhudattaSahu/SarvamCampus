"""StudyNotes Studio — local server.

The desktop app is a single executable that starts this server and opens the
default browser at it. All state lives in the user's data directory
(`~/.studynotes`), so the app is portable and needs no install.

Endpoints cover three things:
  * the pipeline  — upload PDFs, run the study-kit generation
  * the library   — subjects, documents, moving things around
  * the organiser — reorder / rename / merge / tag topics, search, export
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response

from . import export
from .config import get_settings
from .library import UNFILED, Library
from .pipeline.languages import DEFAULT_LANGUAGE, LANGUAGES, is_supported
from .pipeline.organize import propose_order
from .pipeline.orchestrator import run_pipeline
from .providers.registry import build_providers

settings = get_settings()
library = Library(settings.data_dir / "library.json")
ARTIFACT_ROOT = settings.data_dir / "artifacts"
ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="StudyNotes Studio", version="0.2.0")


def _web_dir() -> Path:
    """Locate bundled web assets, whether running from source or a PyInstaller
    one-file bundle (which unpacks data into sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent.parent
    return root / "web"


class _Artifacts:
    """Minimal artifact sink the pipeline writes audio into."""

    def artifact_path(self, doc_id: str, name: str) -> str:
        d = ARTIFACT_ROOT / doc_id
        d.mkdir(parents=True, exist_ok=True)
        return str(d / name)


_artifacts = _Artifacts()


# --------------------------------------------------------------- pipeline job
def _run_job(doc_id: str, pdf_paths: list[str], target_lang: str,
             source_lang: str, make_audio: bool, default_title: str) -> None:
    library.update_document(doc_id, status="running", message="Starting")

    def on_progress(msg: str, pct: int) -> None:
        library.update_document(doc_id, message=msg, progress=pct)

    try:
        providers = build_providers(settings)
        bundle = run_pipeline(
            doc_id, pdf_paths, target_lang, source_lang,
            settings, providers, _artifacts,
            make_audio=make_audio, on_progress=on_progress,
        )
        notes = bundle["structured_notes"]
        topics = [
            Library._normalise_topic(
                {"heading": s.get("heading", ""), "points": s.get("points", []),
                 "detail": s.get("detail", "")},
                order=i,
            )
            for i, s in enumerate(notes.get("sections", []))
        ]
        title = default_title or notes.get("title") or "Untitled document"
        library.update_document(
            doc_id,
            status="done", progress=100, message="Done",
            title=title, pages=bundle["pages"], raw_text=bundle["raw_text"],
            topics=topics,
            key_terms=notes.get("key_terms", []),
            formulas=notes.get("formulas", []),
            questions_to_explore=notes.get("questions_to_explore", []),
            short_notes=bundle["short_notes"],
            flashcards=bundle["flashcards"],
            quiz=bundle["quiz"],
            audio_script=bundle["audio_script"],
            audio_file=bundle["audio_file"],
        )
    except Exception as exc:  # noqa: BLE001
        library.update_document(doc_id, status="failed", message="Failed", error=str(exc))


# --------------------------------------------------------------------- static
@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((_web_dir() / "index.html").read_text(encoding="utf-8"))


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": app.version,
        "data_dir": str(settings.data_dir),
        "providers": {
            "ocr": settings.ocr_provider,
            "llm": settings.llm_provider,
            "tts": settings.tts_provider,
        },
    }


@app.get("/api/languages")
def languages() -> dict:
    return {"default": DEFAULT_LANGUAGE,
            "languages": [{"code": c, "name": n} for c, n in LANGUAGES.items()]}


# --------------------------------------------------------------------- library
@app.get("/api/library")
def get_library() -> dict:
    return library.summary()


@app.post("/api/subjects")
def create_subject(name: str = Form(...), color: str = Form("#3ddc97")) -> dict:
    return library.create_subject(name, color)


@app.patch("/api/subjects/{sid}")
def update_subject(sid: str, name: str | None = Form(None), color: str | None = Form(None)) -> dict:
    subj = library.update_subject(sid, name, color)
    if subj is None:
        raise HTTPException(404, "Subject not found")
    return subj


@app.delete("/api/subjects/{sid}")
def delete_subject(sid: str) -> dict:
    if not library.delete_subject(sid):
        raise HTTPException(400, "Cannot delete this subject")
    return {"ok": True}


# ------------------------------------------------------------------- documents
@app.post("/api/documents")
async def create_document(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    subject_id: str = Form(UNFILED),
    target_language: str = Form(DEFAULT_LANGUAGE),
    source_language: str = Form("auto"),
    make_audio: bool = Form(True),
    title: str = Form(""),
) -> dict:
    if not is_supported(target_language):
        raise HTTPException(400, f"Unsupported target language: {target_language}")
    if not files:
        raise HTTPException(400, "No files uploaded")

    names: list[str] = []
    saved: list[str] = []
    for up in files:
        if not (up.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"Only PDF files are accepted (got {up.filename!r})")
        names.append(Path(up.filename).name)

    doc = library.create_document(title or names[0], subject_id, target_language, source_language, names)

    # Save uploads under the document id so re-runs / debugging are easy.
    doc_dir = settings.uploads_dir / doc["id"]
    doc_dir.mkdir(parents=True, exist_ok=True)
    for up in files:
        dest = doc_dir / Path(up.filename).name
        dest.write_bytes(await up.read())
        saved.append(str(dest))

    background.add_task(_run_job, doc["id"], saved, target_language, source_language, make_audio, title)
    return {"document_id": doc["id"], "status": "queued"}


@app.get("/api/documents/{did}")
def get_document(did: str) -> dict:
    doc = library.get_document(did)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@app.patch("/api/documents/{did}")
def update_document(did: str, title: str | None = Form(None), subject_id: str | None = Form(None)) -> dict:
    fields = {k: v for k, v in (("title", title), ("subject_id", subject_id)) if v is not None}
    doc = library.update_document(did, **fields)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@app.delete("/api/documents/{did}")
def delete_document(did: str) -> dict:
    if not library.delete_document(did):
        raise HTTPException(404, "Document not found")
    return {"ok": True}


@app.get("/api/documents/{did}/audio")
def get_audio(did: str) -> FileResponse:
    doc = library.get_document(did)
    if not doc or not doc.get("audio_file"):
        raise HTTPException(404, "No audio for this document")
    path = ARTIFACT_ROOT / did / doc["audio_file"]
    if not path.exists():
        raise HTTPException(404, "Audio not ready")
    media = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media, filename=doc["audio_file"])


@app.get("/api/documents/{did}/export")
def export_document(did: str, format: str = "md") -> Response:
    doc = library.get_document(did)
    if doc is None:
        raise HTTPException(404, "Document not found")
    fmt = format.lower()
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in doc.get("title", "notes")).strip() or "notes"
    if fmt == "md":
        return Response(export.to_markdown(doc), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.md"'})
    if fmt == "html":
        return Response(export.to_html(doc), media_type="text/html",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.html"'})
    if fmt == "json":
        return Response(export.to_json(doc), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.json"'})
    raise HTTPException(400, "format must be md, html or json")


# --------------------------------------------------------------------- topics
@app.post("/api/documents/{did}/topics")
def add_topic(did: str, heading: str = Form("New topic")) -> dict:
    doc = library.add_topic(did, heading)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@app.put("/api/documents/{did}/topics")
def set_topics(did: str, payload: dict) -> dict:
    doc = library.set_topics(did, payload.get("topics", []))
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@app.patch("/api/documents/{did}/topics/{tid}")
def update_topic(did: str, tid: str, payload: dict) -> dict:
    fields = {k: payload[k] for k in ("heading", "detail", "points", "tags") if k in payload}
    doc = library.update_topic(did, tid, **fields)
    if doc is None:
        raise HTTPException(404, "Document or topic not found")
    return doc


@app.delete("/api/documents/{did}/topics/{tid}")
def delete_topic(did: str, tid: str) -> dict:
    doc = library.delete_topic(did, tid)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@app.post("/api/documents/{did}/topics/{tid}/move")
def move_topic(did: str, tid: str, payload: dict) -> dict:
    doc = library.move_topic(did, tid, int(payload.get("index", 0)))
    if doc is None:
        raise HTTPException(404, "Document or topic not found")
    return doc


@app.post("/api/documents/{did}/topics/{tid}/merge")
def merge_topic(did: str, tid: str, payload: dict) -> dict:
    doc = library.merge_topics(did, tid, payload.get("into", ""))
    if doc is None:
        raise HTTPException(404, "Document or topic not found")
    return doc


@app.post("/api/documents/{did}/auto-organize")
def auto_organize(did: str) -> dict:
    doc = library.get_document(did)
    if doc is None:
        raise HTTPException(404, "Document not found")
    topics = doc.get("topics", [])
    if len(topics) < 2:
        return {"changed": False, "document": doc, "note": "Not enough topics to organise."}
    try:
        providers = build_providers(settings)
        proposal = propose_order(providers.llm, topics, doc.get("target_language", DEFAULT_LANGUAGE))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Organiser failed: {exc}")
    if not proposal:
        return {"changed": False, "document": doc, "note": "No usable suggestion (mock providers keep your order)."}
    by_id = {t["id"]: t for t in topics}
    reordered = [by_id[i] for i in proposal["order"]]
    for i, t in enumerate(reordered):
        t["order"] = i
        if proposal["tags"].get(t["id"]):
            t["tags"] = proposal["tags"][t["id"]]
    doc = library.set_topics(did, reordered)
    return {"changed": True, "document": doc}


# --------------------------------------------------------------------- search
@app.get("/api/search")
def search(q: str = "") -> dict:
    q = q.strip().lower()
    if not q:
        return {"results": []}
    results = []
    for doc in library.data["documents"].values():
        hits = []
        for t in doc.get("topics", []):
            blob = " ".join([t.get("heading", ""), t.get("detail", ""), " ".join(t.get("points", []))]).lower()
            if q in blob:
                hits.append({"topic_id": t["id"], "heading": t.get("heading", "")})
        if q in (doc.get("title", "") or "").lower() or hits:
            results.append({"document_id": doc["id"], "title": doc.get("title", ""), "topics": hits})
    return {"results": results}
