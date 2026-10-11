#!/usr/bin/env python3
"""End-to-end smoke test for StudyNotes Studio (mock providers).

Covers: upload -> pipeline -> topics -> organise (move/merge/edit/delete) ->
search -> export -> subject moves. Uses a throwaway data dir.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="studynotes-test-")
os.environ.setdefault("OCR_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("TTS_PROVIDER", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from app.server import app  # noqa: E402

c = TestClient(app)


def main() -> int:
    assert c.get("/api/health").status_code == 200
    print("health ok, data dir:", c.get("/api/health").json()["data_dir"])

    assert "StudyNotes" in c.get("/").text
    print("index ok")

    lib = c.get("/api/library").json()
    assert any(s["id"] == "unfiled" for s in lib["subjects"])
    print("default Unfiled subject ok")

    subj = c.post("/api/subjects", data={"name": "Biology", "color": "#3ddc97"}).json()
    print("subject:", subj["name"])

    pdf = Path("samples/handwritten_sample.pdf")
    with pdf.open("rb") as fh:
        r = c.post("/api/documents",
                   files={"files": (pdf.name, fh, "application/pdf")},
                   data={"title": "", "subject_id": subj["id"], "target_language": "hi-IN",
                         "source_language": "auto", "make_audio": "true"})
    assert r.status_code == 200, r.text
    did = r.json()["document_id"]
    doc = c.get(f"/api/documents/{did}").json()
    assert doc["status"] == "done", doc
    print(f"document {did}: '{doc['title']}' | topics={len(doc['topics'])} status={doc['status']}")

    topics = doc["topics"]
    assert len(topics) >= 2

    # --- organise: add, rename, edit points, move, merge, delete ---
    doc = c.post(f"/api/documents/{did}/topics", data={"heading": "Revision checklist"}).json()
    new_id = doc["topics"][-1]["id"]
    print("added topic, now:", len(doc["topics"]))

    doc = c.patch(f"/api/documents/{did}/topics/{new_id}",
                  json={"heading": "Exam checklist", "points": ["Revise organelles", "Re-read summary"],
                        "tags": ["revision", "exam"]}).json()
    t = next(x for x in doc["topics"] if x["id"] == new_id)
    assert t["heading"] == "Exam checklist" and t["tags"] == ["revision", "exam"]
    print("edited topic ->", t["heading"], t["tags"])

    doc = c.post(f"/api/documents/{did}/topics/{new_id}/move", json={"index": 0}).json()
    assert doc["topics"][0]["id"] == new_id
    print("moved topic to top ok")

    first_id = topics[0]["id"]
    before = len(doc["topics"])
    doc = c.post(f"/api/documents/{did}/topics/{new_id}/merge", json={"into": first_id}).json()
    assert len(doc["topics"]) == before - 1
    print("merged topic ok, now:", len(doc["topics"]))

    victim = doc["topics"][-1]["id"]
    doc = c.delete(f"/api/documents/{did}/topics/{victim}").json()
    print("deleted topic ok, now:", len(doc["topics"]))

    # --- reorder via PUT ---
    ids = [t["id"] for t in doc["topics"]][::-1]
    payload = {"topics": [next(t for t in doc["topics"] if t["id"] == i) for i in ids]}
    doc = c.put(f"/api/documents/{did}/topics", json=payload).json()
    assert [t["id"] for t in doc["topics"]] == ids
    print("reorder via PUT ok")

    # --- auto-organize (mock: no change) ---
    r = c.post(f"/api/documents/{did}/auto-organize").json()
    print("auto-organize:", r["changed"], "-", r.get("note", ""))

    # --- search ---
    res = c.get("/api/search?q=cell").json()["results"]
    print("search 'cell' ->", len(res), "document(s)")

    # --- export ---
    assert c.get(f"/api/documents/{did}/export?format=md").status_code == 200
    assert c.get(f"/api/documents/{did}/export?format=html").status_code == 200
    assert c.get(f"/api/documents/{did}/export?format=json").status_code == 200
    print("exports ok (md/html/json)")

    # --- move document between subjects + audio ---
    c.patch(f"/api/documents/{did}", data={"subject_id": "unfiled"})
    assert c.get(f"/api/documents/{did}").json()["subject_id"] == "unfiled"
    assert c.get(f"/api/documents/{did}/audio").status_code == 200
    print("move + audio ok")

    # --- delete subject falls back to Unfiled; delete doc ---
    c.delete(f"/api/subjects/{subj['id']}")
    assert c.delete(f"/api/documents/{did}").status_code == 200
    print("cleanup ok")

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
