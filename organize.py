"""Optional 'smart organise' — ask the LLM to re-order topics and suggest tags.

This is a convenience on top of manual organisation: the user can always drag
topics around by hand. If the model returns something unusable we simply leave
the current order untouched, so the feature can never damage a library.
"""
from __future__ import annotations

import json

from ..providers.llm import strip_code_fence
from .languages import lang_name

_SYSTEM = (
    "You are a study-notes organiser. You group and order topics so a student "
    "revises in the most logical sequence. Answer with a single valid JSON "
    "object and nothing else."
)


def propose_order(llm, topics: list[dict], target_lang: str) -> dict | None:
    """Return {'order': [topic_id, ...], 'tags': {topic_id: [tag, ...]}} or None.

    None means 'no usable suggestion' — the caller keeps the existing order.
    """
    if not topics:
        return None
    lang = lang_name(target_lang)
    listing = [
        {"id": t["id"], "heading": t.get("heading", ""), "points": t.get("points", [])[:3]}
        for t in topics
    ]
    prompt = f"""TASK:organize
Order these study topics into the most logical learning sequence, and give each
1-3 short topical tags in {lang}.

Return JSON exactly like:
{{"order": ["<topic id>", "..."], "tags": {{"<topic id>": ["tag1", "tag2"]}}}}

Every id from the input must appear exactly once in "order".

TOPICS:
{json.dumps(listing, ensure_ascii=False)}
"""
    try:
        data = json.loads(strip_code_fence(llm.complete(prompt, system=_SYSTEM, json_mode=True)))
    except (json.JSONDecodeError, TypeError):
        return None
    order = data.get("order")
    valid_ids = {t["id"] for t in topics}
    if not isinstance(order, list) or set(order) != valid_ids:
        return None
    tags = data.get("tags") if isinstance(data.get("tags"), dict) else {}
    return {"order": order, "tags": tags}
