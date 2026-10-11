#!/usr/bin/env python3
"""StudyNotes Studio — single-executable entry point.

Starts the local server on a free port and opens the app in the default
browser. Close the console window (or press Ctrl+C) to stop it.

    python launcher.py                # from source
    ./StudyNotes                      # built with PyInstaller
"""
from __future__ import annotations

import argparse
import multiprocessing
import socket
import threading
import webbrowser


def _free_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    multiprocessing.freeze_support()  # required for frozen (PyInstaller) builds

    ap = argparse.ArgumentParser(description="StudyNotes Studio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = ap.parse_args()

    import uvicorn

    from app.server import app  # imported here so freeze_support runs first

    port = _free_port(args.port)
    url = f"http://{args.host}:{port}/"

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print("=" * 60)
    print("  StudyNotes Studio is running")
    print(f"  Open:  {url}")
    print("  Close this window to stop the app.")
    print("=" * 60)

    uvicorn.run(app, host=args.host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
