"""Central, env-driven configuration.

Everything the app needs to run is read from the environment so the same code
works locally, in Docker, or on a server with no edits. The defaults point at
`mock` providers, which means a fresh clone runs end-to-end offline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Load a `.env` if present, so the packaged app can be configured by
    dropping keys into ~/.studynotes/.env (or a .env beside the executable).
    Values already set in the real environment always win."""
    candidates = [
        Path.cwd() / ".env",
        Path.home() / ".studynotes" / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            for line in path.read_text("utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
        except OSError:
            pass


_load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # --- provider selection ---
    ocr_provider: str = field(default_factory=lambda: _get("OCR_PROVIDER", "mock"))
    llm_provider: str = field(default_factory=lambda: _get("LLM_PROVIDER", "mock"))
    tts_provider: str = field(default_factory=lambda: _get("TTS_PROVIDER", "mock"))

    # --- LLM: any OpenAI-compatible /chat/completions endpoint ---
    llm_base_url: str = field(default_factory=lambda: _get("LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_api_key: str = field(default_factory=lambda: _get("LLM_API_KEY"))
    llm_model: str = field(default_factory=lambda: _get("LLM_MODEL", "gpt-4o-mini"))
    llm_vision_model: str = field(default_factory=lambda: _get("LLM_VISION_MODEL") or _get("LLM_MODEL", "gpt-4o-mini"))

    # --- TTS: OpenAI-compatible /audio/speech endpoint ---
    tts_base_url: str = field(default_factory=lambda: _get("TTS_BASE_URL", "https://api.openai.com/v1"))
    tts_api_key: str = field(default_factory=lambda: _get("TTS_API_KEY") or _get("LLM_API_KEY"))
    tts_model: str = field(default_factory=lambda: _get("TTS_MODEL", "tts-1"))
    tts_voice: str = field(default_factory=lambda: _get("TTS_VOICE", "alloy"))

    # --- processing ---
    render_dpi: int = field(default_factory=lambda: _get_int("RENDER_DPI", 200))
    max_pages: int = field(default_factory=lambda: _get_int("MAX_PAGES", 40))
    # Desktop default: a per-user data dir so the app is portable and always
    # has somewhere writable to live, however it was launched.
    data_dir: Path = field(
        default_factory=lambda: Path(_get("DATA_DIR", str(Path.home() / ".studynotes")))
    )
    request_timeout: int = field(default_factory=lambda: _get_int("REQUEST_TIMEOUT", 120))

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    def ensure_dirs(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Process-wide settings singleton (directories created on first use)."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
