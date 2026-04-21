# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(__file__).resolve().parent
FFMPEG_DIR = ROOT / "ffmpeg-bin"
ffmpeg_binaries = []
for binary_name in ("ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"):
    binary_path = FFMPEG_DIR / binary_name
    if binary_path.exists():
        ffmpeg_binaries.append((str(binary_path), "ffmpeg-bin"))

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=ffmpeg_binaries,
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YTDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
