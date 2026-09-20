#!/usr/bin/env python3
"""Pruebas del motor, sin red ni interfaz. Se ejecuta directo: python3 tests/test_core.py"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aacyoutube import core  # noqa: E402

checks = []


def check(name, condition, detail=""):
    checks.append((name, bool(condition), detail))


# ── Rutas ─────────────────────────────────────────────────────────────────
music = core.default_music_dir()
check("la carpeta destino es absoluta", music.is_absolute(), str(music))
check("la carpeta destino termina en aacyoutube", music.name == "aacyoutube", str(music))
check("la carpeta destino cuelga del home", str(music).startswith(str(Path.home())), str(music))
check("la carpeta de ajustes es absoluta", core.config_dir().is_absolute())

# ── Dependencias ──────────────────────────────────────────────────────────
check("install_hint menciona el paquete", "ffmpeg" in core.install_hint("ffmpeg"))
check("find_binary encuentra python3", core.find_binary("python3") is not None)
check("find_binary devuelve None si no existe", core.find_binary("no-existe-xyz-123") is None)
check("check_dependencies devuelve una lista", isinstance(core.check_dependencies(), list))

# ── Modos y navegadores ───────────────────────────────────────────────────
check("hay un texto por cada modo", set(core.MODES) == set(core.MODE_HINTS), str(core.MODES))
check("«ninguno» es la primera opción de cookies", core.BROWSERS[0] == "ninguno")
check("Safari solo aparece en macOS", ("safari" in core.BROWSERS) == core.IS_MAC)

# ── Opciones de yt-dlp ────────────────────────────────────────────────────
if core.yt_dlp is not None:
    out = Path(tempfile.gettempdir()) / "aacy-test"

    maxi = core.build_options(out, mode="max")
    check("máxima calidad pide 256 kbps",
          maxi["postprocessors"][0].get("preferredquality") == "256")
    check("máxima calidad remuestrea a 44.1 kHz para el iPod",
          maxi["postprocessor_args"]["extractaudio"] == ["-ar", "44100", "-ac", "2"])

    copy = core.build_options(out, mode="copy")
    check("el modo copia no recomprime",
          "preferredquality" not in copy["postprocessors"][0])

    check("la salida es .m4a", maxi["postprocessors"][0]["preferredcodec"] == "m4a")
    check("nombres compatibles con FAT32 del iPod", maxi["windowsfilenames"] is True)
    check("la carpeta destino llega a yt-dlp", maxi["paths"]["home"] == str(out))

    # El interruptor de listas tiene que invertirse: playlists=False → noplaylist=True.
    check("sin listas, noplaylist activo", core.build_options(out, playlists=False)["noplaylist"] is True)
    check("con listas, noplaylist apagado", core.build_options(out, playlists=True)["noplaylist"] is False)

    square = core.build_options(out, square_cover=True)["postprocessor_args"]
    check("la portada cuadrada recorta", "crop=" in " ".join(square["thumbnailsconvertor+ffmpeg_o"]))
    plain = core.build_options(out, square_cover=False)["postprocessor_args"]
    check("sin portada cuadrada no se recorta",
          "crop=" not in " ".join(plain["thumbnailsconvertor+ffmpeg_o"]))

    check("las cookies del navegador se pasan tal cual",
          core.build_options(out, cookies_browser="firefox")["cookiesfrombrowser"] == ("firefox",))
    check("«ninguno» no pone cookies",
          "cookiesfrombrowser" not in core.build_options(out, cookies_browser="ninguno"))
else:
    check("yt-dlp instalado", False, "no se pudo importar yt_dlp")

# ── Ajustes ───────────────────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    original = core.CONFIG_FILE
    core.CONFIG_FILE = Path(tmp) / "sub" / "config.json"
    core.save_config({"mode": "copy", "dark": False})
    loaded = core.load_config()
    check("los ajustes van y vuelven", loaded == {"mode": "copy", "dark": False}, str(loaded))
    core.CONFIG_FILE = Path(tmp) / "no-existe.json"
    check("sin archivo, ajustes vacíos", core.load_config() == {})
    core.CONFIG_FILE = original

# ── Recursos ──────────────────────────────────────────────────────────────
check("el icono está donde se espera", (core.assets_dir() / "icon-128.png").is_file(),
      str(core.assets_dir()))

# ── Resultado ─────────────────────────────────────────────────────────────
failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f"  {'✔' if ok else '✖'} {name}" + (f"  — {detail}" if detail and not ok else ""))
print(f"\n{len(checks) - len(failed)}/{len(checks)} pruebas del núcleo correctas")
sys.exit(1 if failed else 0)
