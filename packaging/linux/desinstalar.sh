#!/usr/bin/env bash
# Quita aacyoutube del usuario actual. No toca ffmpeg ni la música descargada.
set -euo pipefail
PREFIX="${AACY_PREFIX:-$HOME/.local}"

rm -rf "$PREFIX/share/aacyoutube"
rm -f  "$PREFIX/bin/aacyoutube"
rm -f  "$PREFIX/share/applications/aacyoutube.desktop"
for size in 16 32 64 128 256 512; do
  rm -f "$PREFIX/share/icons/hicolor/${size}x${size}/apps/aacyoutube.png"
done
command -v update-desktop-database >/dev/null && \
  update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true

echo "✔ aacyoutube desinstalado."
echo "  Tus ajustes siguen en ~/.config/aacyoutube (bórralos si quieres)."
echo "  La música descargada no se ha tocado."
