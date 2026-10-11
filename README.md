<div align="center">

# StudyNotes Studio

**Turn handwritten PDFs into complete, multilingual study kits — as a single desktop app.**

Upload your handwritten notes → get structured notes, short notes, flashcards,
a quiz and an audio overview, in the language you choose, organised into
subjects and topics you can rearrange.


</div>

---

## What it is

StudyNotes Studio is a **single-executable desktop app**. It starts a small
local server on your machine and opens the app in your browser — everything
runs locally, and your notes never leave your computer unless you point it at a
cloud AI provider.

You give it the messy stuff: a PDF of handwritten lecture notes. It gives you
back a complete study kit — written in the language you want.

> **Handwriting in, study kit out.** English + 12 Indian languages.

---

## Features

### 📥 Upload everything at once
Select **all your PDFs in one go** — they become a single study kit. Choose the
output language and the language the notes are written in, and file the whole
thing under a subject as you upload.

### 🧠 What it builds (all in your chosen language)
| Artifact | What you get |
|---|---|
| **Structured notes** | Titled sections with bullet points and a short detail paragraph |
| **Short notes** | Crisp, exam-eve revision bullets |
| **Flashcards** | Active-recall front/back cards |
| **Quiz** | Multiple-choice questions with answers and explanations |
| **Audio overview** | A spoken narration you can play in-app |

### 🗂️ Organise your topics properly
- Every generated section becomes an editable **topic** — rename, edit points
  and detail, add tags.
- **Drag to reorder**, or use ↑ / ↓ buttons.
- **Merge** two topics, **delete**, or **add** new ones.
- **Smart organise** — asks the model to put topics in the best learning order
  and suggest tags.
- **Search** across every topic in every document.
- Group documents into **subjects**; move them around any time. Deleting a
  subject never deletes notes — they fall back to *Unfiled*.

### 💾 Export & autosave
Download any study kit as **Markdown**, **HTML** (printable) or **JSON**.
Everything auto-saves as you work.

---

## Screenshots

> Add your own screenshots here once you run it — drop images into `docs/` and
> reference them, e.g. `![Library view](docs/screenshot-library.png)`.

---

## Getting the executable

> **Important:** a Windows `.exe` must be built on Windows. PyInstaller cannot
> cross-compile, so it can't be produced from Linux or macOS. Pick one of three
> routes:

### 1. Build it yourself on Windows (one command)
```bat
build\build_windows.bat
```
Creates `dist\StudyNotes.exe`. Double-click it — the app opens in your browser.

### 2. Let GitHub build it for you (no Windows machine needed)
Push this repo to GitHub. The included workflow
[`.github/workflows/build.yml`](.github/workflows/build.yml) builds **Windows,
Linux and macOS** executables on every push. Download `StudyNotes.exe` from the
run's **Artifacts** section — or trigger it by hand from the **Actions** tab.

### 3. Run from source (any OS, no build)
```bash
pip install -r requirements.txt
python launcher.py            # opens http://127.0.0.1:8765
```

On Linux/macOS you can also build a native single-file binary:
```bash
bash build/build_unix.sh      # -> dist/StudyNotes
```

---

## Quickstart

The app starts with **mock providers**, so you can click through the entire flow
with **no API keys and no network**.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/make_sample_pdf.py     # create a sample PDF to try
python launcher.py                    # start the app
```

Create a subject → add a document → upload the sample PDF → watch the study kit
build.

---

## Configuration

To use real engines, drop a `.env` file into `~/.studynotes/` (or beside the
executable). Copy [`.env.example`](.env.example) and fill it in. The three
switches that matter:

```dotenv
OCR_PROVIDER=vision_llm          # handwriting OCR via a multimodal model
LLM_PROVIDER=openai_compatible   # structuring / generation
TTS_PROVIDER=openai_compatible   # audio overview

LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_VISION_MODEL=gpt-4o-mini
```

The LLM and TTS adapters speak the standard **OpenAI-compatible** shapes, so
the same settings work for OpenAI, **Sarvam AI** (Indic-first), Groq, Together,
a local vLLM server, and more — you only change the base URL, key and model.
Restart the app after editing `.env`.

---

## Architecture

```
  PDF(s) ──► rasterise ──► OCR ──► structure ──┬─► short notes
             (PyMuPDF)   (provider)  (LLM)     ├─► flashcards
                                               ├─► quiz
                                               └─► audio script ──► TTS ──► audio
                          everything written in the target language
```

Three provider protocols — `OCRProvider`, `LLMProvider`, `TTSProvider` — sit
behind the pipeline, so you can swap any engine without touching pipeline code.
See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full breakdown.

**Design choice worth knowing:** notes are structured **directly in the target
language** by prompting the model in-language, rather than writing English and
translating after. It gives noticeably more idiomatic Hindi/Tamil/Bengali study
material.

---

## API

The local server exposes a small REST API (handy for scripting):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | active providers + data dir |
| `GET` | `/api/languages` | supported output languages |
| `POST` | `/api/documents` | upload PDF(s) + options → `document_id` |
| `GET` | `/api/documents/{id}` | full document with topics + study kit |
| `PATCH` | `/api/documents/{id}` | rename / move to another subject |
| `GET` | `/api/documents/{id}/export?format=md\|html\|json` | export the kit |
| `POST` | `/api/documents/{id}/topics` | add a topic |
| `PUT` | `/api/documents/{id}/topics` | replace ordered topic list (reorder) |
| `PATCH` | `/api/documents/{id}/topics/{tid}` | edit a topic |
| `POST` | `/api/documents/{id}/topics/{tid}/move` | move a topic to an index |
| `POST` | `/api/documents/{id}/topics/{tid}/merge` | merge into another topic |
| `DELETE` | `/api/documents/{id}/topics/{tid}` | delete a topic |
| `POST` | `/api/documents/{id}/auto-organize` | smart reorder + tags |
| `GET` | `/api/search?q=` | search across all topics |

---

## Project structure

```
studynotes-desktop/
├── launcher.py                  entry point (start server + open browser)
├── app/
│   ├── server.py                FastAPI: pipeline + library + organiser APIs
│   ├── library.py               persistent subjects → documents → topics
│   ├── export.py                Markdown / HTML / JSON export
│   ├── config.py                env-driven settings (+ .env loading)
│   ├── providers/               swappable OCR / LLM / TTS engines
│   └── pipeline/                rasterise → OCR → structure → generate → narrate
├── web/index.html               the whole UI (no build step)
├── build/
│   ├── studynotes.spec          PyInstaller one-file spec
│   ├── build_windows.bat        one-command Windows build
│   └── build_unix.sh            one-command Linux/macOS build
├── scripts/                     smoke tests + sample generator
├── docs/                        architecture notes + GitHub Pages site
└── .github/workflows/build.yml  CI that builds the .exe for you
```

---

## Notes & limits

- **Handwriting OCR is the hard part.** The `vision_llm` path (a multimodal
  model reading each page) is the quickest start and handles messy handwriting
  and mixed scripts best. For production Indic handwriting, evaluate cloud
  document-AI APIs (Google Document AI, Azure Document Intelligence) on your own
  scans — accuracy varies a lot.
- **Verify provider endpoints** against current docs; providers move paths and
  fields over time. The adapters follow the public OpenAI-compatible shapes.
- The pipeline runs on a background thread per document. For many concurrent
  users you'd move it to a proper job queue — for a single-user desktop app this
  is the right amount of machinery.
- First launch of the packaged binary takes a few seconds while it unpacks
  itself; later runs are faster.

---

## Roadmap

- [ ] DOCX / Anki `.apkg` export
- [ ] Human review + edit of OCR text before generation
- [ ] Spaced-repetition study mode
- [ ] Per-language OCR accuracy evaluation harness

---

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). This project
follows the [Contributor Covenant](CODE_OF_CONDUCT.md).

---

## License

[MIT](LICENSE) © 2026 Prabhudatta Sahu
