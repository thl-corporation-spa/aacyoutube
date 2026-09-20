"""Motor de descarga: rutas por plataforma, dependencias y opciones de yt-dlp.

Este módulo no importa Tk ni nada de la interfaz: lo usan por igual la GUI
(`aacyoutube.app`) y la terminal (`aacyoutube.cli`).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:  # pragma: no cover - depende del entorno del usuario
    yt_dlp = None

IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
IS_WINDOWS = os.name == "nt"

# Apple Silicon (M1/M2/M3/M4…) vs. Intel. Bajo Rosetta 2 un binario x86_64
# ve "x86_64" aunque el equipo sea Apple Silicon; sysctl lo desmiente.
def mac_arch() -> str:
    """'arm64', 'x86_64' o 'x86_64 (Rosetta)' en macOS; '' en el resto."""
    if not IS_MAC:
        return ""
    machine = platform.machine()
    if machine == "x86_64" and _sysctl("sysctl.proc_translated") == "1":
        return "x86_64 (Rosetta)"
    return machine


def _sysctl(key: str) -> str:
    try:
        out = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, timeout=2)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


MODES = {
    # Mejor fuente disponible. Si hay AAC 256k (YouTube Music Premium) se copia tal cual;
    # si no, se toma el Opus ~160k y se codifica a AAC-LC 256k (libfdk_aac si existe).
    "max": "Máxima calidad",
    # El AAC que YouTube ya sirve (~128k), sin recomprimir: cero pérdida generacional.
    "copy": "Original sin recomprimir",
}

MODE_HINTS = {
    "max": "AAC 256 kbps desde la mejor fuente disponible",
    "copy": "El AAC que sirve YouTube (~128 kbps), sin pérdida generacional",
}

# Navegadores de los que yt-dlp sabe leer cookies. Safari solo existe en macOS.
_COMMON_BROWSERS = ["chrome", "chromium", "brave", "edge", "firefox", "opera", "vivaldi"]
BROWSERS = ["ninguno"] + (["safari"] if IS_MAC else []) + _COMMON_BROWSERS

# Carpeta por playlist/álbum con número de pista; archivo suelto como "Artista - Título".
OUTTMPL = (
    "%(playlist_title|.)s/"
    "%(playlist_index&{:02d} - |)s"
    "%(artist,uploader)s - %(track,title)s.%(ext)s"
)

# Recorta la miniatura al centro en cuadrado (portada de álbum) y la guarda como JPEG.
SQUARE_JPEG = ["-c:v", "mjpeg", "-q:v", "2",
               "-vf", "crop='if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)',scale='min(1000,iw)':-2"]


# ───────────────────────────── Rutas por plataforma ─────────────────────────────

def _xdg_music_dir() -> Path | None:
    """Carpeta de música según XDG: respeta «Música», «Musik», «Musique»…"""
    try:
        out = subprocess.run(["xdg-user-dir", "MUSIC"], capture_output=True, text=True, timeout=2)
        path = Path(out.stdout.strip())
        if out.returncode == 0 and path != Path.home() and path.is_absolute():
            return path
    except (OSError, subprocess.SubprocessError):
        pass
    # Sin xdg-user-dir (imagen mínima de Ubuntu/Fedora): leer el archivo a mano.
    conf = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "user-dirs.dirs"
    try:
        for line in conf.read_text(encoding="utf-8").splitlines():
            if line.startswith("XDG_MUSIC_DIR="):
                value = line.split("=", 1)[1].strip().strip('"')
                return Path(value.replace("$HOME", str(Path.home())))
    except OSError:
        pass
    return None


def default_music_dir() -> Path:
    """Dónde guardar por omisión, en la carpeta de música real de cada sistema."""
    if IS_LINUX:
        base = _xdg_music_dir()
        if base is None:
            base = next((Path.home() / n for n in ("Música", "Music", "Musik", "Musique")
                         if (Path.home() / n).is_dir()), Path.home() / "Music")
    else:  # macOS y Windows usan un nombre estable en inglés en disco.
        base = Path.home() / "Music"
    return base / "aacyoutube"


def config_dir() -> Path:
    """Carpeta de ajustes siguiendo la convención de cada sistema."""
    if IS_MAC:
        return Path.home() / "Library" / "Application Support" / "aacyoutube"
    if IS_WINDOWS:
        return Path(os.environ.get("APPDATA", Path.home())) / "aacyoutube"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "aacyoutube"


CONFIG_FILE = config_dir() / "config.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(data: dict) -> None:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # Los ajustes son una comodidad; no vale la pena romper por ellos.


# ───────────────────────────── Dependencias externas ─────────────────────────────

def _bundled_dir() -> Path | None:
    """Carpeta de recursos cuando corremos dentro de un .app/ejecutable PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else None


def assets_dir() -> Path:
    """Carpeta de iconos, tanto en el repo como dentro de un .app empaquetado."""
    bundled = _bundled_dir()
    if bundled:
        for candidate in (bundled / "assets", bundled / "aacyoutube" / "assets"):
            if candidate.is_dir():
                return candidate
    return Path(__file__).resolve().parent / "assets"


def _extra_bin_paths() -> list[Path]:
    """Sitios donde buscar ffmpeg además del PATH.

    Una .app de macOS lanzada desde Finder hereda un PATH mínimo que no incluye
    Homebrew, así que hay que mirar sus dos prefijos: /opt/homebrew (Apple
    Silicon) y /usr/local (Intel).
    """
    paths = []
    bundled = _bundled_dir()
    if bundled:
        paths += [bundled, bundled / "bin"]
    if IS_MAC:
        paths += [Path("/opt/homebrew/bin"), Path("/usr/local/bin"),
                  Path("/opt/local/bin"), Path("/sw/bin")]
    paths += [Path("/usr/bin"), Path("/usr/local/bin"), Path.home() / ".local" / "bin"]
    return paths


def find_binary(name: str) -> str | None:
    """Ruta a un ejecutable, mirando el PATH y los prefijos habituales."""
    found = shutil.which(name)
    if found:
        return found
    for folder in _extra_bin_paths():
        candidate = folder / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def ffmpeg_location() -> str | None:
    """Carpeta que contiene ffmpeg, en el formato que espera yt-dlp."""
    found = find_binary("ffmpeg")
    return str(Path(found).parent) if found else None


def install_hint(package: str) -> str:
    """Cómo instalar algo en el sistema donde estamos corriendo ahora."""
    if IS_MAC:
        return f"brew install {package}"
    if IS_LINUX:
        if shutil.which("dnf"):
            return f"sudo dnf install {package}"
        if shutil.which("apt"):
            return f"sudo apt install {package}"
        if shutil.which("pacman"):
            return f"sudo pacman -S {package}"
        if shutil.which("zypper"):
            return f"sudo zypper install {package}"
    return f"instala {package} con el gestor de paquetes de tu sistema"


def check_dependencies() -> list[str]:
    """Lista de problemas bloqueantes, ya redactados para mostrar al usuario."""
    problems = []
    if yt_dlp is None:
        problems.append(f"Falta yt-dlp. Instálalo con: pip3 install --user --upgrade yt-dlp")
    if not find_binary("ffmpeg"):
        problems.append(f"Falta ffmpeg (convierte y etiqueta el audio). Instálalo con: {install_hint('ffmpeg')}")
    return problems


def js_runtimes() -> dict | None:
    """yt-dlp necesita un runtime de JavaScript para YouTube; usa los que haya instalados."""
    found = {}
    for name in ("deno", "node", "bun"):
        path = find_binary(name)
        if path:
            found[name] = {"path": path}
    return found or None


def _supports_js_runtimes() -> bool:
    """`js_runtimes` existe desde yt-dlp 2025.11; en versiones viejas se ignora."""
    if yt_dlp is None:
        return False
    try:
        year, month, _ = (int(p) for p in yt_dlp.version.__version__.split(".")[:3])
    except (ValueError, AttributeError):
        return False
    return (year, month) >= (2025, 11)


# ───────────────────────────── Descarga ─────────────────────────────

def build_options(out_dir, mode="max", cookies_browser=None, square_cover=True,
                  playlists=False, progress_hook=None, postprocessor_hook=None, logger=None):
    if yt_dlp is None:
        raise RuntimeError("yt-dlp no está instalado")

    if mode == "copy":
        fmt = "bestaudio[acodec^=mp4a]/bestaudio"
        extract = {"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}
        pp_args = {}
    else:
        fmt = "bestaudio[acodec^=mp4a][abr>=200]/bestaudio[acodec^=opus]/bestaudio"
        extract = {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "256"}
        # iPod: AAC-LC, 44.1 kHz, estéreo (el Opus viene a 48 kHz).
        pp_args = {"extractaudio": ["-ar", "44100", "-ac", "2"]}

    thumb_args = SQUARE_JPEG if square_cover else ["-c:v", "mjpeg", "-q:v", "2"]
    pp_args["thumbnailsconvertor+ffmpeg_o"] = thumb_args

    opts = {
        "format": fmt,
        "paths": {"home": str(out_dir)},
        "outtmpl": OUTTMPL,
        "windowsfilenames": True,  # nombres válidos en iPods formateados en FAT32
        "noplaylist": not playlists,  # un watch?v=...&list=... baja solo esa canción
        "writethumbnail": True,
        "ignoreerrors": "only_download",
        "postprocessors": [
            extract,
            # Número de pista desde la posición en la playlist si el video no trae uno.
            {"key": "MetadataParser", "when": "pre_process",
             "actions": [(yt_dlp.postprocessor.MetadataParserPP.interpretter,
                          "%(track_number,playlist_index|)s", "%(track_number)s")]},
            {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": False},
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"},
            {"key": "EmbedThumbnail", "already_have_thumbnail": False},
        ],
        "postprocessor_args": pp_args,
        "quiet": True,
        "noprogress": True,
        "no_color": True,
    }

    location = ffmpeg_location()
    if location:
        opts["ffmpeg_location"] = location

    runtimes = js_runtimes()
    if runtimes and _supports_js_runtimes():
        opts["js_runtimes"] = runtimes
        opts["remote_components"] = ["ejs:github"]
    if cookies_browser and cookies_browser != "ninguno":
        opts["cookiesfrombrowser"] = (cookies_browser,)
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if postprocessor_hook:
        opts["postprocessor_hooks"] = [postprocessor_hook]
    if logger:
        opts["logger"] = logger
    return opts


def download(urls, **kwargs):
    with yt_dlp.YoutubeDL(build_options(**kwargs)) as ydl:
        return ydl.download(urls)


def reveal(path: Path) -> None:
    """Abre la carpeta en Finder / Archivos, sin fallar si no se puede."""
    try:
        if IS_MAC:
            subprocess.Popen(["open", str(path)])
        elif IS_WINDOWS:
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except (OSError, subprocess.SubprocessError):
        pass
