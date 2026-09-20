"""Modo terminal: `aacyoutube URL [URL …]`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aacyoutube import __version__, core


def run_cli(argv):
    p = argparse.ArgumentParser(
        prog="aacyoutube",
        description="Descarga audio AAC (.m4a) para iPod desde YouTube / YouTube Music.")
    p.add_argument("urls", nargs="*", help="enlaces de YouTube o YouTube Music")
    p.add_argument("-o", "--out", default=None, help="carpeta destino")
    p.add_argument("--copy", action="store_true",
                   help="AAC original de YouTube, sin recomprimir (~128 kbps)")
    p.add_argument("--cookies", choices=core.BROWSERS, default="ninguno",
                   help="lee las cookies de este navegador (Premium / contenido restringido)")
    p.add_argument("--playlists", action="store_true",
                   help="descarga la lista completa, no solo la canción del enlace")
    p.add_argument("--no-square", action="store_true", help="no recortar la portada a cuadrado")
    p.add_argument("--gui", action="store_true", help="abre la ventana aunque haya argumentos")
    p.add_argument("--doctor", action="store_true", help="revisa las dependencias y sale")
    p.add_argument("-V", "--version", action="version", version=f"aacyoutube {__version__}")
    a = p.parse_args(argv)

    if a.doctor:
        return doctor()
    if a.gui or not a.urls:
        from aacyoutube.app import run_gui
        return run_gui()

    problems = core.check_dependencies()
    if problems:
        for problem in problems:
            print("✖", problem, file=sys.stderr)
        return 1

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            pct = d.get("downloaded_bytes", 0) * 100 / total if total else 0
            name = Path(d.get("filename", "")).stem[:48]
            print(f"\r  {pct:5.1f}%  {name:<48}", end="", flush=True)
        elif d["status"] == "finished":
            print(f"\r  ↓ {Path(d['filename']).stem[:60]:<60}")

    out = Path(a.out or core.default_music_dir()).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    code = core.download(a.urls, out_dir=out, mode="copy" if a.copy else "max",
                         cookies_browser=a.cookies, square_cover=not a.no_square,
                         playlists=a.playlists, progress_hook=hook)
    if code == 0:
        print("✔ Listo en", out)
    else:
        print("✖ Terminó con errores", file=sys.stderr)
    return code


def doctor():
    """Informe rápido del entorno: útil para pedir ayuda o reportar un fallo."""
    print(f"aacyoutube {__version__}")
    print(f"  python       {sys.version.split()[0]} ({sys.executable})")
    print(f"  plataforma   {sys.platform} {core.mac_arch() or ''}".rstrip())
    if core.yt_dlp is not None:
        print(f"  yt-dlp       {core.yt_dlp.version.__version__}")
    else:
        print("  yt-dlp       NO INSTALADO")
    print(f"  ffmpeg       {core.find_binary('ffmpeg') or 'NO ENCONTRADO'}")
    runtimes = core.js_runtimes() or {}
    print(f"  runtime JS   {', '.join(runtimes) if runtimes else 'ninguno (YouTube puede fallar)'}")
    try:
        import tkinter
        print(f"  tkinter      Tk {tkinter.TkVersion}")
    except ImportError:
        print(f"  tkinter      NO INSTALADO — {core.install_hint('python3-tkinter')}")
    print(f"  destino      {core.default_music_dir()}")
    print(f"  ajustes      {core.CONFIG_FILE}")

    problems = core.check_dependencies()
    for problem in problems:
        print("\n✖", problem)
    return 1 if problems else 0
