# Architecture

StudyNotes Studio is deliberately small and layered so that each heavy,
swappable dependency (OCR, LLM, TTS) lives behind an interface.

## The pipeline

```
  PDF(s) ──► rasterise ──► OCR ──► structure ──┬─► short notes
             (PyMuPDF)   (provider)  (LLM)     ├─► flashcards
                                               ├─► quiz
                                               └─► audio script ──► TTS ──► audio
                          everything written in the target language
```

1. **Rasterise** — `app/pipeline/pdf.py` renders each PDF page to PNG with
   PyMuPDF at `RENDER_DPI` (default 200).
2. **OCR** — `app/providers/ocr.py` transcribes the handwriting. The
   `vision_llm` engine sends one page at a time to a multimodal model.
3. **Structure** — `app/pipeline/steps.py` asks the LLM for a JSON object with
   `title`, `summary`, `sections`, `key_terms`, `formulas` and
   `questions_to_explore`, written **directly in the target language**.
4. **Generate** — further prompts derive short notes, flashcards and the quiz
   from the structured notes.
5. **Narrate** — an audio script is written, then rendered to speech by the TTS
   provider.

## Providers

Three protocols in `app/providers/base.py`:

| Protocol | Method(s) | Built-in engines |
|---|---|---|
| `OCRProvider` | `ocr_pages(images, lang)` | `vision_llm`, `mock` |
| `LLMProvider` | `complete`, `complete_vision` | `openai_compatible`, `mock` |
| `TTSProvider` | `synthesize(text, lang, path)` | `openai_compatible`, `mock` |

`app/providers/registry.py` builds the concrete engines from settings. **The
pipeline only ever imports the protocols**, so adding an engine means writing a
class and one branch in the registry — no pipeline changes.

The `openai_compatible` adapters use the standard `/chat/completions` and
`/audio/speech` request shapes, which is why one class covers OpenAI, Sarvam AI,
Groq, Together, Fireworks and a local vLLM/Ollama server.

## Data model

`app/library.py` holds everything the user organises:

```
Library
└── subjects[]            { id, name, color }
    └── documents{}       id -> Document
        └── topics[]      { id, heading, points[], detail, tags[], order }
```

A `Document` also carries the generated study kit (`short_notes`, `flashcards`,
`quiz`, `audio_script`, `audio_file`) plus `raw_text` and `key_terms`.

The library is a single JSON file at `~/.studynotes/library.json`, written with
an atomic replace under a lock — safe because the server mutates it from
background worker threads.

## Server

`app/server.py` is a FastAPI app with three groups of endpoints:

- **pipeline** — `POST /api/documents` saves uploads, creates a document and
  runs the pipeline on a background task, reporting progress into the library.
- **library** — subjects and documents CRUD, moving documents between subjects.
- **organiser** — topics CRUD, reorder (`PUT` / `move`), `merge`, and
  `auto-organize` (an LLM proposal that is validated before it is applied, so a
  bad suggestion can never corrupt the library).

## Packaging

`build/studynotes.spec` bundles `launcher.py` plus the `web/` assets into a
single-file executable. `launcher.py` finds a free port, starts uvicorn, and
opens the default browser. At runtime, bundled data is read from
`sys._MEIPASS`; user data always lives under `~/.studynotes`.

## Why a local server instead of a native window?

A browser UI gives drag-and-drop topic reordering, rich card rendering and audio
playback for free, works identically on every OS, and keeps the whole thing
testable headlessly. The user still double-clicks one file.
