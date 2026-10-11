#!/usr/bin/env bash
# Build the single-file StudyNotes executable on Linux or macOS.
#   bash build/build_unix.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Creating virtual environment ==="
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt

echo "=== Building single-file executable ==="
pyinstaller --clean --noconfirm build/studynotes.spec

echo
echo "=== Done ==="
echo "Your app is at:  dist/StudyNotes"
echo "Run it with:     ./dist/StudyNotes"
