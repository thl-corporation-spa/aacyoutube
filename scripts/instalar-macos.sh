#!/usr/bin/env bash
# Instalador de aacyoutube para macOS.
#
#   curl -fsSL https://raw.githubusercontent.com/thl-corporation-spa/aacyoutube/main/scripts/instalar-macos.sh | bash
#
# Detecta si tu Mac es Intel o Apple Silicon, descarga la versión que
# corresponde y la deja lista en Aplicaciones. No hace falta instalar nada
# más: ffmpeg viene dentro de la app.
set -euo pipefail

REPO="${AACY_REPO:-thl-corporation-spa/aacyoutube}"
APPS="${AACY_APPS:-/Applications}"

rojo()  { printf '\033[1;31m▸\033[0m %s\n' "$*"; }
morir() { printf '\033[1;31m✖\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || morir "Este instalador es solo para macOS."

# ── 1. Qué Mac es ─────────────────────────────────────────────────────────
ARCH="$(uname -m)"
# Bajo Rosetta 2 un shell x86_64 miente sobre la máquina; sysctl no.
if [ "$ARCH" = "x86_64" ] && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)" = "1" ]; then
  ARCH="arm64"
  rojo "Shell bajo Rosetta: se instalará la versión nativa de Apple Silicon."
fi
case "$ARCH" in
  arm64)  rojo "Mac con chip Apple (serie M) — versión arm64" ;;
  x86_64) rojo "Mac con procesador Intel — versión x86_64" ;;
  *) morir "Arquitectura no soportada: $ARCH" ;;
esac

# ── 2. Buscar la última versión ───────────────────────────────────────────
rojo "Buscando la última versión…"
JSON="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest")" \
  || morir "No se pudo consultar GitHub. ¿Tienes conexión?"

# Solo sed y grep: en un Mac recién estrenado no hay python ni jq.
URL="$(printf '%s' "$JSON" \
  | tr ',' '\n' \
  | sed -n 's/.*"browser_download_url": *"\([^"]*macos-'"$ARCH"'\.dmg\)".*/\1/p' \
  | head -1)"
[ -n "$URL" ] || morir "No hay ninguna descarga para $ARCH en la última versión.
Mira las versiones disponibles en https://github.com/$REPO/releases"

VERSION="$(printf '%s' "$JSON" | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1)"
rojo "Versión $VERSION"

# ── 3. Descargar ──────────────────────────────────────────────────────────
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DMG="$TMP/aacyoutube.dmg"

rojo "Descargando…"
curl -fL --progress-bar "$URL" -o "$DMG" || morir "Falló la descarga."

# ── 4. Montar, copiar, desmontar ──────────────────────────────────────────
MONTAJE="$TMP/mnt"
mkdir -p "$MONTAJE"
hdiutil attach "$DMG" -mountpoint "$MONTAJE" -nobrowse -quiet \
  || morir "No se pudo abrir el archivo descargado."
trap 'hdiutil detach "$MONTAJE" -quiet 2>/dev/null || true; rm -rf "$TMP"' EXIT

if [ -d "$APPS/aacyoutube.app" ]; then
  rojo "Reemplazando la versión anterior…"
  rm -rf "$APPS/aacyoutube.app" 2>/dev/null || sudo rm -rf "$APPS/aacyoutube.app"
fi

rojo "Instalando en $APPS…"
cp -R "$MONTAJE/aacyoutube.app" "$APPS/" 2>/dev/null || {
  rojo "Hace falta permiso de administrador"
  sudo cp -R "$MONTAJE/aacyoutube.app" "$APPS/"
}

hdiutil detach "$MONTAJE" -quiet
trap 'rm -rf "$TMP"' EXIT

# ── 5. Quitar la cuarentena ───────────────────────────────────────────────
# La app está firmada, pero no con una cuenta de desarrollador de Apple de
# pago, así que macOS la marca al venir de internet. Esto evita el aviso de
# "está dañada" y el rodeo de abrirla con clic derecho.
xattr -dr com.apple.quarantine "$APPS/aacyoutube.app" 2>/dev/null \
  || sudo xattr -dr com.apple.quarantine "$APPS/aacyoutube.app" 2>/dev/null || true

echo
rojo "Listo. aacyoutube $VERSION está instalada."
echo "    Ábrela desde Launchpad, o escribe:  open -a aacyoutube"

# Si nos han llegado por una tubería (curl | bash) no hay terminal que preguntar.
if [ -t 0 ]; then
  printf '¿Abrirla ahora? [S/n] '
  read -r respuesta
  case "${respuesta:-s}" in [SsYy]*) open -a aacyoutube ;; esac
fi
