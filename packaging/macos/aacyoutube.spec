# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para el .app de macOS.

Se compila una vez por arquitectura (x86_64 en un runner Intel, arm64 en uno
Apple Silicon): así el binario es nativo en ambos y no hace falta Rosetta.

Variables de entorno que acepta:
  AACY_FFMPEG_DIR  carpeta con ffmpeg/ffprobe estáticos para empotrar
  AACY_VERSION     versión que se escribe en el Info.plist
  AACY_ARCH        'x86_64' o 'arm64' (solo para la versión mínima del sistema)
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = os.environ.get("AACY_VERSION", "2.0.0")
ARCH = os.environ.get("AACY_ARCH", os.uname().machine)
FFMPEG_DIR = os.environ.get("AACY_FFMPEG_DIR", "")

binaries = []
if FFMPEG_DIR:
    for name in ("ffmpeg", "ffprobe"):
        candidate = Path(FFMPEG_DIR) / name
        if candidate.is_file():
            binaries.append((str(candidate), "."))

datas = [(str(ROOT / "aacyoutube" / "assets"), "assets")]

a = Analysis(
    [str(ROOT / "packaging" / "macos" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["yt_dlp", "aacyoutube.app", "aacyoutube.cli", "aacyoutube.core"],
    hookspath=[],
    runtime_hooks=[],
    # Nada de esto lo usa la app; fuera para que el .app no pese de más.
    excludes=["numpy", "matplotlib", "PIL", "pytest", "setuptools", "pip", "test"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="aacyoutube",
    debug=False,
    strip=False,
    upx=False,          # UPX rompe la firma de código en macOS
    console=False,
    target_arch=None,   # cada runner compila para el suyo
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="aacyoutube")

app = BUNDLE(
    coll,
    name="aacyoutube.app",
    icon=str(ROOT / "packaging" / "macos" / "aacyoutube.icns"),
    bundle_identifier="com.thlcorporation.aacyoutube",
    version=VERSION,
    info_plist={
        "CFBundleName": "aacyoutube",
        "CFBundleDisplayName": "aacyoutube",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.music",
        # Catalina es el mínimo razonable en Intel; Apple Silicon nace en Big Sur.
        "LSMinimumSystemVersion": "11.0" if ARCH == "arm64" else "10.15",
        "NSRequiresAquaSystemAppearance": False,  # respeta el modo oscuro del sistema
        "CFBundleDevelopmentRegion": "es",
    },
)
