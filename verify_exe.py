#!/usr/bin/env python3
"""Verify the built executable end-to-end: launch it, upload a PDF, check the
study kit is produced, then shut it down. Assumes dist/StudyNotes exists.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

EXE = "./dist/StudyNotes"
PORT = "8791"
BASE = f"http://127.0.0.1:{PORT}"


def main() -> int:
    env = dict(os.environ)
    env["DATA_DIR"] = tempfile.mkdtemp(prefix="studynotes-exe-")
    env["OCR_PROVIDER"] = env["LLM_PROVIDER"] = env["TTS_PROVIDER"] = "mock"

    proc = subprocess.Popen(
        [EXE, "--no-browser", "--port", PORT],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        # wait for the server to come up (one-file bundles unpack first)
        for _ in range(120):
            if proc.poll() is not None:
                print("EXE exited early:\n", proc.stdout.read())
                return 1
            try:
                if httpx.get(BASE + "/api/health", timeout=2).status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        else:
            print("server never came up")
            return 1

        h = httpx.get(BASE + "/api/health").json()
        print("health:", h["status"], h["providers"])
        print("index ok:", "StudyNotes" in httpx.get(BASE + "/").text)

        pdf = Path("samples/handwritten_sample.pdf")
        with pdf.open("rb") as fh:
            r = httpx.post(
                BASE + "/api/documents",
                files={"files": (pdf.name, fh, "application/pdf")},
                data={"title": "", "subject_id": "unfiled", "target_language": "hi-IN",
                      "source_language": "auto", "make_audio": "true"},
                timeout=120,
            )
        did = r.json()["document_id"]
        # the pipeline runs on a background thread — poll until it finishes
        doc = {}
        for _ in range(120):
            doc = httpx.get(f"{BASE}/api/documents/{did}", timeout=30).json()
            if doc.get("status") in ("done", "failed"):
                break
            time.sleep(0.5)
        print(f"document: '{doc.get('title')}' status={doc.get('status')} topics={len(doc.get('topics', []))}")
        assert doc.get("status") == "done", doc

        assert httpx.get(f"{BASE}/api/documents/{did}/export?format=md").status_code == 200
        assert httpx.get(f"{BASE}/api/documents/{did}/audio").status_code == 200
        print("export + audio ok")
        print("\nEXECUTABLE OK")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
