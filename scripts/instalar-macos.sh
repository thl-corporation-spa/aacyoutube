#!/usr/bin/env bash
# Instala aacyoutube en macOS descargando el .dmg de la última Release.
#
#   ./scripts/instalar-macos.sh
#
# El repositorio es privado, así que la descarga va por la CLI de GitHub (`gh`),
# que ya sabe autenticarse. Detecta solo si el Mac es Intel o Apple Silicon.
set -euo pipefail

REPO="${AACY_REPO:-thl-corporation-spa/aacyoutube}"
APPS="${AACY_APPS:-/Applications}"

say()  { printf '\033[1;31m▸\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m✖\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || die "Este instalador es solo para macOS."

# ── 1. Qué Mac es ─────────────────────────────────────────────────────────
ARCH="$(uname -m)"
# Bajo Rosetta 2 un shell x86_64 miente sobre la máquina; sysctl no.
if [ "$ARCH" = "x86_64" ] && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)" = "1" ]; then
  ARCH="arm64"
  say "Estás en un shell bajo Rosetta; se instalará la versión nativa Apple Silicon."
fi
case "$ARCH" in
  arm64)  say "Mac con chip Apple (serie M) — versión arm64" ;;
  x86_64) say "Mac con procesador Intel — versión x86_64" ;;
  *) die "Arquitectura no soportada: $ARCH" ;;
esac

# ── 2. Descargar el .dmg de la Release ────────────────────────────────────
command -v gh >/dev/null || die "Falta la CLI de GitHub. Instálala con:  brew install gh
Luego entra con:  gh auth login"
gh auth status >/dev/null 2>&1 || die "No has iniciado sesión en GitHub. Ejecuta:  gh auth login"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

say "Descargando la última versión de $REPO…"
gh release download --repo "$REPO" --pattern "*macos-$ARCH.dmg" --dir "$TMP" --clobber \
  || die "No hay ningún .dmg para $ARCH en la última Release.
Comprueba en https://github.com/$REPO/releases que la compilación terminó."

DMG="$(find "$TMP" -name '*.dmg' | head -1)"
[ -n "$DMG" ] || die "La descarga no trajo ningún .dmg."
say "Descargado: $(basename "$DMG")"

# ── 3. Montar, copiar, desmontar ──────────────────────────────────────────
MOUNT="$TMP/mnt"
mkdir -p "$MOUNT"
hdiutil attach "$DMG" -mountpoint "$MOUNT" -nobrowse -quiet
trap 'hdiutil detach "$MOUNT" -quiet 2>/dev/null || true; rm -rf "$TMP"' EXIT

if [ -d "$APPS/aacyoutube.app" ]; then
  say "Reemplazando la versión anterior…"
  rm -rf "$APPS/aacyoutube.app"
fi
say "Copiando a $APPS…"
cp -R "$MOUNT/aacyoutube.app" "$APPS/" 2>/dev/null \
  || { say "Hace falta permiso de administrador"; sudo cp -R "$MOUNT/aacyoutube.app" "$APPS/"; }

hdiutil detach "$MOUNT" -quiet
trap 'rm -rf "$TMP"' EXIT

# ── 4. Quitar la cuarentena ───────────────────────────────────────────────
# La app está firmada ad-hoc pero no con una cuenta de desarrollador de pago,
# así que Gatekeeper la marca al venir de internet. Esto evita el aviso de
# "está dañada" y el rodeo de abrirla con clic derecho.
say "Quitando la marca de cuarentena…"
xattr -dr com.apple.quarantine "$APPS/aacyoutube.app" 2>/dev/null \
  || sudo xattr -dr com.apple.quarantine "$APPS/aacyoutube.app" 2>/dev/null || true

echo
say "Listo. aacyoutube está en $APPS"
echo "    open -a aacyoutube"
echo
read -r -p "¿Abrirla ahora? [S/n] " answer
case "${answer:-s}" in [SsYy]*) open -a aacyoutube ;; esac
