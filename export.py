"""Export a document's organised study kit to Markdown / HTML / JSON."""
from __future__ import annotations

import html as _html
import json


def to_markdown(doc: dict) -> str:
    lines: list[str] = [f"# {doc.get('title', 'Study notes')}\n"]
    if doc.get("source_files"):
        lines.append(f"_Source: {', '.join(doc['source_files'])}_\n")
    if doc.get("topics"):
        lines.append("\n## Topics\n")
        for i, t in enumerate(doc["topics"], 1):
            tags = ("  `" + "` `".join(t.get("tags", [])) + "`") if t.get("tags") else ""
            lines.append(f"\n### {i}. {t.get('heading', '')}{tags}\n")
            for p in t.get("points", []):
                lines.append(f"- {p}")
            if t.get("detail"):
                lines.append(f"\n{t['detail']}")
    if doc.get("key_terms"):
        lines.append("\n## Key Terms\n")
        for kt in doc["key_terms"]:
            lines.append(f"- **{kt.get('term', '')}** — {kt.get('definition', '')}")
    sn = doc.get("short_notes") or {}
    if sn.get("bullets"):
        lines.append("\n## Short Notes\n")
        for b in sn["bullets"]:
            lines.append(f"- {b}")
    cards = (doc.get("flashcards") or {}).get("cards", [])
    if cards:
        lines.append("\n## Flashcards\n")
        for c in cards:
            lines.append(f"- **{c.get('front', '')}** → {c.get('back', '')}")
    qs = (doc.get("quiz") or {}).get("questions", [])
    if qs:
        lines.append("\n## Quiz\n")
        for i, q in enumerate(qs, 1):
            lines.append(f"\n**{i}. {q.get('question', '')}**")
            for j, opt in enumerate(q.get("options", [])):
                lines.append(f"   - {'ABCD'[j] if j < 4 else j}. {opt}")
            ai = q.get("answer_index", 0)
            opts = q.get("options", [])
            lines.append(f"   - _Answer: {'ABCD'[ai] if ai < 4 else ai} — {opts[ai] if ai < len(opts) else ''}_")
    audio = doc.get("audio_script") or {}
    if audio.get("script"):
        lines.append("\n## Audio Script\n")
        lines.append(audio["script"])
    return "\n".join(lines) + "\n"


def to_html(doc: dict) -> str:
    e = _html.escape
    parts = [f"<h1>{e(doc.get('title', 'Study notes'))}</h1>"]
    if doc.get("topics"):
        parts.append("<h2>Topics</h2>")
        for i, t in enumerate(doc["topics"], 1):
            parts.append(f"<h3>{i}. {e(t.get('heading', ''))}</h3>")
            if t.get("points"):
                parts.append("<ul>" + "".join(f"<li>{e(p)}</li>" for p in t["points"]) + "</ul>")
            if t.get("detail"):
                parts.append(f"<p>{e(t['detail'])}</p>")
    if doc.get("key_terms"):
        parts.append("<h2>Key Terms</h2><ul>" + "".join(
            f"<li><b>{e(k.get('term', ''))}</b> — {e(k.get('definition', ''))}</li>" for k in doc["key_terms"]
        ) + "</ul>")
    cards = (doc.get("flashcards") or {}).get("cards", [])
    if cards:
        parts.append("<h2>Flashcards</h2>")
        for c in cards:
            parts.append(f"<div class='fc'><b>{e(c.get('front', ''))}</b><div>{e(c.get('back', ''))}</div></div>")
    qs = (doc.get("quiz") or {}).get("questions", [])
    if qs:
        parts.append("<h2>Quiz</h2>")
        for i, q in enumerate(qs, 1):
            opts = "".join(f"<div class='opt'>{'ABCD'[j] if j < 4 else j}. {e(o)}</div>" for j, o in enumerate(q.get("options", [])))
            ai = q.get("answer_index", 0)
            parts.append(f"<div class='q'><b>{i}. {e(q.get('question', ''))}</b>{opts}<div class='ans'>Answer: {'ABCD'[ai] if ai < 4 else ai}</div></div>")
    style = (
        "body{font:16px/1.6 system-ui,sans-serif;max-width:820px;margin:40px auto;padding:0 20px;color:#1a1a1a}"
        "h1{border-bottom:2px solid #eee;padding-bottom:8px}.fc,.q{background:#f6f7fb;border:1px solid #e3e6ef;"
        "border-radius:8px;padding:12px;margin:8px 0}.opt{color:#555}.ans{color:#0a7d4f;margin-top:6px}"
    )
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{e(doc.get('title',''))}</title><style>{style}</style></head><body>{''.join(parts)}</body></html>"


def to_json(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2)
