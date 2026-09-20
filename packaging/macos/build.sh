#!/usr/bin/env bash
# Construye aacyoutube.app y su .dmg en macOS (Intel o Apple Silicon).
#
#   ./packaging/macos/build.sh
#
# Se ejecuta igual en un Mac propio que en un runner de GitHub Actions.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ARCH="${AACY_ARCH:-$(uname -m)}"
VERSION="$(python3 -c 'import re,pathlib; print(re.search(r"\"(.+?)\"", pathlib.Path("aacyoutube/__init__.py").read_text()).group(1))')"
DIST="dist/$ARCH"
export AACY_ARCH="$ARCH" AACY_VERSION="$VERSION"

echo "▸ aacyoutube $VERSION para $ARCH"

# ── 1. Icono .icns a partir de los PNG del repo ───────────────────────────
ICONSET="packaging/macos/aacyoutube.iconset"
rm -rf "$ICONSET" && mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  cp "aacyoutube/assets/icon-$size.png" "$ICONSET/icon_${size}x${size}.png"
  double=$((size * 2))
  src="aacyoutube/assets/icon-$double.png"
  [ -f "$src" ] || src="aacyoutube/assets/icon.png"
  cp "$src" "$ICONSET/icon_${size}x${size}@2x.png"
done
iconutil -c icns "$ICONSET" -o packaging/macos/aacyoutube.icns
echo "  icono listo"

# ── 2. ffmpeg estático para empotrar ──────────────────────────────────────
# Sin esto la app solo funciona si el usuario ya tiene Homebrew con ffmpeg.
if [ -z "${AACY_FFMPEG_DIR:-}" ]; then
  AACY_FFMPEG_DIR="$(pwd)/build/ffmpeg-$ARCH"
  mkdir -p "$AACY_FFMPEG_DIR"
  if [ ! -x "$AACY_FFMPEG_DIR/ffmpeg" ]; then
    case "$ARCH" in
      arm64)  SLUG="darwin-arm64" ;;
      x86_64) SLUG="darwin-x64" ;;
      *) echo "arquitectura no soportada: $ARCH" >&2; exit 1 ;;
    esac
    # Se pregunta por la última versión; si la API no contesta, se usa una fija
    # que ya sabemos buena, para que la compilación no dependa de la red de GitHub.
    TAG="${FFMPEG_STATIC_TAG:-}"
    if [ -z "$TAG" ]; then
      TAG="$(curl -fsSL https://api.github.com/repos/eugeneware/ffmpeg-static/releases/latest \
             | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1)"
    fi
    TAG="${TAG:-b6.1.1}"
    BASE="https://github.com/eugeneware/ffmpeg-static/releases/download/$TAG"
    echo "  ffmpeg-static $TAG"
    for tool in ffmpeg ffprobe; do
      echo "  descargando $tool ($SLUG)…"
      curl -fsSL "$BASE/$tool-$SLUG" -o "$AACY_FFMPEG_DIR/$tool"
      chmod +x "$AACY_FFMPEG_DIR/$tool"
    done
  fi
fi
export AACY_FFMPEG_DIR
echo "  ffmpeg: $AACY_FFMPEG_DIR"

# ── 3. Empaquetar ─────────────────────────────────────────────────────────
rm -rf "$DIST" build/aacyoutube
python3 -m PyInstaller --noconfirm --clean \
  --distpath "$DIST" --workpath "build/pyi-$ARCH" \
  packaging/macos/aacyoutube.spec

APP="$DIST/aacyoutube.app"
[ -d "$APP" ] || { echo "no se generó $APP" >&2; exit 1; }

# ── 4. Firma ad-hoc ───────────────────────────────────────────────────────
# En Apple Silicon un binario sin firma ni siquiera arranca. La firma ad-hoc no
# evita el aviso de Gatekeeper (eso pide una cuenta de desarrollador de pago),
# pero sí deja que la app se ejecute tras abrirla con clic derecho → Abrir.
codesign --force --deep --sign - --timestamp=none "$APP"
codesign --verify --deep --strict "$APP" && echo "  firma ad-hoc verificada"

# ── 5. DMG ────────────────────────────────────────────────────────────────
DMG="$DIST/aacyoutube-$VERSION-macos-$ARCH.dmg"
STAGE="build/dmg-$ARCH"
rm -rf "$STAGE" "$DMG" && mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/macos/LEEME.txt "$STAGE/LÉEME primero.txt" 2>/dev/null || true
hdiutil create -volname "aacyoutube $VERSION" -srcfolder "$STAGE" \
  -ov -format UDZO "$DMG" >/dev/null

echo "✔ $APP"
echo "✔ $DMG"
