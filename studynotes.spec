# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds the single-file StudyNotes executable.

    pyinstaller --clean --noconfirm build/studynotes.spec

Output: dist/StudyNotes.exe (Windows) or dist/StudyNotes (Linux/macOS).
Must be run on the target OS: PyInstaller does not cross-compile.
"""
from PyInstaller.utils.hooks import collect_submodules
import os

# Resolve the project root regardless of where pyinstaller is invoked from.
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + collect_submodules("starlette")
    + collect_submodules("pydantic")
    + collect_submodules("anyio")
    + [
        "app.server",
        "app.library",
        "app.export",
        "app.pipeline.orchestrator",
        "app.pipeline.organize",
        "app.providers.registry",
        "app.providers.llm",
        "app.providers.ocr",
        "app.providers.tts",
        # uvicorn resolves these dynamically at runtime
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
    ]
)

a = Analysis(
    [os.path.join(ROOT, "launcher.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, "web"), "web")],          # bundle the UI
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy.testing", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="StudyNotes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # keeps a small window showing the local URL + logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
