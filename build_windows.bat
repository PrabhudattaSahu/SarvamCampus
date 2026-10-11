@echo off
REM Build StudyNotes.exe on Windows. Run from the project root.
REM   build\build_windows.bat
setlocal

echo === Creating virtual environment ===
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo === Installing dependencies ===
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt

echo === Building single-file executable ===
pyinstaller --clean --noconfirm build\studynotes.spec

echo.
echo === Done ===
echo Your app is at:  dist\StudyNotes.exe
echo Double-click it to run. It opens in your browser.
endlocal
