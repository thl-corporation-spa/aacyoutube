#!/usr/bin/env bash
# Copia los .dmg de una Release privada al repositorio público de descargas.
#
#   ./scripts/publicar-descargas.sh            la última versión publicada
#   ./scripts/publicar-descargas.sh v2.1.0     una concreta
#
# El repositorio privado guarda el código; el público solo el instalador y los
# .dmg, para que cualquiera pueda descargar la app sin ver el código ni tener
# que iniciar sesión en GitHub.
set -euo pipefail

PRIVADO="${AACY_REPO_PRIVADO:-thl-corporation-spa/aacyoutube}"
PUBLICO="${AACY_REPO_PUBLICO:-thl-corporation-spa/aacyoutube-descargas}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

rojo()  { printf '\033[1;31m▸\033[0m %s\n' "$*"; }
morir() { printf '\033[1;31m✖\033[0m %s\n' "$*" >&2; exit 1; }

command -v gh >/dev/null || morir "Falta la CLI de GitHub (gh)."
gh auth status >/dev/null 2>&1 || morir "No has iniciado sesión: gh auth login"

TAG="${1:-$(gh release view --repo "$PRIVADO" --json tagName --jq .tagName)}"
[ -n "$TAG" ] || morir "No hay ninguna Release en $PRIVADO."
rojo "Publicando $TAG de $PRIVADO en $PUBLICO"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

rojo "Descargando los .dmg de la Release privada…"
gh release download "$TAG" --repo "$PRIVADO" --pattern "*.dmg" --dir "$TMP" --clobber \
  || morir "La Release $TAG no tiene ningún .dmg todavía."

# Que no se publique media versión sin querer: si falta una arquitectura,
# se avisa y hay que confirmar.
FALTAN=""
for arch in x86_64 arm64; do
  ls "$TMP"/*macos-$arch.dmg >/dev/null 2>&1 || FALTAN="$FALTAN $arch"
done
if [ -n "$FALTAN" ]; then
  printf '\033[1;33m⚠\033[0m Falta el .dmg de:%s\n' "$FALTAN"
  if [ -t 0 ]; then
    printf '  ¿Publicar igualmente? [s/N] '
    read -r r; case "$r" in [SsYy]*) ;; *) morir "Cancelado." ;; esac
  else
    rojo "Se publica de todos modos (sin terminal para preguntar)."
  fi
fi

for f in "$TMP"/*.dmg; do rojo "  $(basename "$f")  ($(du -h "$f" | cut -f1))"; done

# Las notas del repo público no mencionan el privado, que nadie de fuera puede abrir.
NOTAS="$TMP/notas.md"
sed "s|@REPO@|$PUBLICO|g" "$ROOT/packaging/macos/notas-publicas.md" > "$NOTAS"

if gh release view "$TAG" --repo "$PUBLICO" >/dev/null 2>&1; then
  rojo "La versión ya existía en el repositorio público; se actualiza."
  gh release edit "$TAG" --repo "$PUBLICO" --notes-file "$NOTAS"
else
  gh release create "$TAG" --repo "$PUBLICO" \
    --title "aacyoutube $TAG" --notes-file "$NOTAS"
fi

gh release upload "$TAG" "$TMP"/*.dmg --repo "$PUBLICO" --clobber
rojo "Listo: https://github.com/$PUBLICO/releases/tag/$TAG"
echo
echo "  Quien quiera instalarla solo tiene que pegar esto en la Terminal:"
echo "    curl -fsSL https://raw.githubusercontent.com/$PUBLICO/main/instalar.sh | bash"
