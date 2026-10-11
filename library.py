"""Persistent study library: subjects -> documents -> topics.

Everything the user organises lives in a single JSON file in the user's data
directory, so the app is self-contained and portable. Thread-safe: the server
mutates it from background worker threads, so every read-modify-write goes
through a lock and an atomic replace.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from threading import RLock
from typing import Any

UNFILED = "unfiled"


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


class Library:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = RLock()
        self.data: dict[str, Any] = self._load()
        self._ensure_defaults()

    # ------------------------------------------------------------------ io
    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"subjects": [], "documents": {}}

    def _ensure_defaults(self) -> None:
        if not any(s["id"] == UNFILED for s in self.data["subjects"]):
            self.data["subjects"].insert(
                0, {"id": UNFILED, "name": "Unfiled", "color": "#6c8cff"}
            )
        self.save()

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), "utf-8")
            tmp.replace(self.path)

    # -------------------------------------------------------------- subjects
    def list_subjects(self) -> list[dict]:
        return self.data["subjects"]

    def create_subject(self, name: str, color: str = "#3ddc97") -> dict:
        with self._lock:
            subj = {"id": _new_id(), "name": name.strip() or "New subject", "color": color}
            self.data["subjects"].append(subj)
            self.save()
            return subj

    def update_subject(self, sid: str, name: str | None = None, color: str | None = None) -> dict | None:
        with self._lock:
            for s in self.data["subjects"]:
                if s["id"] == sid:
                    if name is not None:
                        s["name"] = name.strip() or s["name"]
                    if color is not None:
                        s["color"] = color
                    self.save()
                    return s
        return None

    def delete_subject(self, sid: str) -> bool:
        """Delete a subject; its documents fall back to Unfiled (never lost)."""
        if sid == UNFILED:
            return False
        with self._lock:
            self.data["subjects"] = [s for s in self.data["subjects"] if s["id"] != sid]
            for doc in self.data["documents"].values():
                if doc.get("subject_id") == sid:
                    doc["subject_id"] = UNFILED
            self.save()
            return True

    # ------------------------------------------------------------- documents
    def create_document(
        self, title: str, subject_id: str, target_language: str,
        source_language: str, file_names: list[str],
    ) -> dict:
        with self._lock:
            did = _new_id()
            doc = {
                "id": did,
                "title": title,
                "subject_id": subject_id or UNFILED,
                "target_language": target_language,
                "source_language": source_language,
                "created_at": time.time(),
                "updated_at": time.time(),
                "source_files": file_names,
                "status": "queued",
                "progress": 0,
                "message": "Queued",
                "error": None,
                "pages": 0,
                "raw_text": "",
                "topics": [],
                "key_terms": [],
                "formulas": [],
                "questions_to_explore": [],
                "short_notes": None,
                "flashcards": None,
                "quiz": None,
                "audio_script": None,
                "audio_file": None,
            }
            self.data["documents"][did] = doc
            self.save()
            return doc

    def get_document(self, did: str) -> dict | None:
        return self.data["documents"].get(did)

    def update_document(self, did: str, **fields) -> dict | None:
        with self._lock:
            doc = self.data["documents"].get(did)
            if doc is None:
                return None
            doc.update(fields)
            doc["updated_at"] = time.time()
            self.save()
            return doc

    def delete_document(self, did: str) -> bool:
        with self._lock:
            if did in self.data["documents"]:
                del self.data["documents"][did]
                self.save()
                return True
        return False

    def move_document(self, did: str, subject_id: str) -> dict | None:
        return self.update_document(did, subject_id=subject_id)

    # ---------------------------------------------------------------- topics
    def set_topics(self, did: str, topics: list[dict]) -> dict | None:
        """Replace the ordered topic list (used for drag/drop reordering)."""
        cleaned = []
        for i, t in enumerate(topics):
            cleaned.append(self._normalise_topic(t, order=i))
        return self.update_document(did, topics=cleaned)

    def add_topic(self, did: str, heading: str = "New topic") -> dict | None:
        with self._lock:
            doc = self.data["documents"].get(did)
            if doc is None:
                return None
            doc["topics"].append(self._normalise_topic({"heading": heading}, order=len(doc["topics"])))
            self.save()
            return doc

    def update_topic(self, did: str, tid: str, **fields) -> dict | None:
        with self._lock:
            doc = self.data["documents"].get(did)
            if doc is None:
                return None
            for t in doc["topics"]:
                if t["id"] == tid:
                    for k in ("heading", "detail", "points", "tags"):
                        if k in fields:
                            t[k] = fields[k]
                    self.save()
                    return doc
        return None

    def delete_topic(self, did: str, tid: str) -> dict | None:
        with self._lock:
            doc = self.data["documents"].get(did)
            if doc is None:
                return None
            doc["topics"] = [t for t in doc["topics"] if t["id"] != tid]
            for i, t in enumerate(doc["topics"]):
                t["order"] = i
            self.save()
            return doc

    def move_topic(self, did: str, tid: str, index: int) -> dict | None:
        with self._lock:
            doc = self.data["documents"].get(did)
            if doc is None:
                return None
            topics = doc["topics"]
            cur = next((i for i, t in enumerate(topics) if t["id"] == tid), None)
            if cur is None:
                return None
            item = topics.pop(cur)
            index = max(0, min(index, len(topics)))
            topics.insert(index, item)
            for i, t in enumerate(topics):
                t["order"] = i
            self.save()
            return doc

    def merge_topics(self, did: str, source_id: str, into_id: str) -> dict | None:
        """Fold one topic into another (appends its points) and drop the source."""
        if source_id == into_id:
            return self.get_document(did)
        with self._lock:
            doc = self.data["documents"].get(did)
            if doc is None:
                return None
            src = next((t for t in doc["topics"] if t["id"] == source_id), None)
            dst = next((t for t in doc["topics"] if t["id"] == into_id), None)
            if src is None or dst is None:
                return None
            dst["points"] = list(dst.get("points", [])) + list(src.get("points", []))
            if src.get("detail") and not dst.get("detail"):
                dst["detail"] = src["detail"]
            dst["tags"] = sorted(set(dst.get("tags", [])) | set(src.get("tags", [])))
            doc["topics"] = [t for t in doc["topics"] if t["id"] != source_id]
            for i, t in enumerate(doc["topics"]):
                t["order"] = i
            self.save()
            return doc

    @staticmethod
    def _normalise_topic(t: dict, order: int = 0) -> dict:
        return {
            "id": t.get("id") or _new_id(),
            "heading": t.get("heading", "Untitled topic"),
            "points": list(t.get("points", []) or []),
            "detail": t.get("detail", ""),
            "tags": list(t.get("tags", []) or []),
            "order": order,
        }

    # --------------------------------------------------------------- summary
    def summary(self) -> dict:
        """Compact view for the sidebar tree."""
        docs = []
        for doc in sorted(self.data["documents"].values(), key=lambda d: d.get("created_at", 0), reverse=True):
            docs.append({
                "id": doc["id"],
                "title": doc["title"],
                "subject_id": doc.get("subject_id", UNFILED),
                "status": doc.get("status"),
                "progress": doc.get("progress", 0),
                "message": doc.get("message", ""),
                "topics": len(doc.get("topics", [])),
                "language": doc.get("target_language"),
                "created_at": doc.get("created_at"),
            })
        return {"subjects": self.data["subjects"], "documents": docs}
