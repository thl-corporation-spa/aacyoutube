#!/usr/bin/env bash
# Instalador de aacyoutube: elige el camino según el sistema.
#
#   ./install.sh
#
# En Linux instala desde el código. En macOS descarga el .dmg ya compilado
# de la última Release (o compila desde el código con --desde-codigo).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$(uname -s)" in
  Linux)
    exec "$ROOT/packaging/linux/instalar.sh" "$@" ;;
  Darwin)
    if [ "${1:-}" = "--desde-codigo" ]; then
      command -v python3 >/dev/null || { echo "Falta Python 3. Instálalo con: brew install python" >&2; exit 1; }
      python3 -m pip install --user --upgrade "pyinstaller>=6.6" yt-dlp
      exec "$ROOT/packaging/macos/build.sh"
    fi
    exec "$ROOT/scripts/instalar-macos.sh" ;;
  *)
    echo "Sistema no soportado: $(uname -s)" >&2
    echo "aacyoutube funciona en Linux y macOS." >&2
    exit 1 ;;
esac
