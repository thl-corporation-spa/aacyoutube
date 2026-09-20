#!/usr/bin/env bash
# Instala aacyoutube en un Mac desde el código, sin binarios compilados.
#
#   curl -fsSL https://raw.githubusercontent.com/thl-corporation-spa/aacyoutube/main/scripts/instalar-mac.sh | bash
#
# Funciona igual en Intel que en Apple Silicon. Como la app se construye en tu
# propio Mac y no se descarga ya hecha, macOS no la marca en cuarentena: no
# aparece el aviso de «está dañada» ni hay que abrirla con clic derecho.
set -euo pipefail

REPO="${AACY_REPO:-thl-corporation-spa/aacyoutube}"
RAMA="${AACY_RAMA:-main}"
BASE="$HOME/Library/Application Support/aacyoutube"
VENV="$BASE/venv"
APP="/Applications/aacyoutube.app"

azul() { printf '\033[1;31m▸\033[0m %s\n' "$*"; }
ojo()  { printf '\033[1;33m⚠\033[0m %s\n' "$*"; }
morir(){ printf '\033[1;31m✖\033[0m %s\n' "$*" >&2; exit 1; }

# Con `curl | bash` la entrada estándar es la tubería, así que para preguntar
# (y para que sudo pida la contraseña) hay que hablarle a la terminal real.
preguntar() {
  local respuesta
  if [ -r /dev/tty ]; then
    printf '%s ' "$1" > /dev/tty
    read -r respuesta < /dev/tty || respuesta=""
  else
    respuesta="$2"
  fi
  echo "${respuesta:-$2}"
}

[ "$(uname -s)" = "Darwin" ] || morir "Este instalador es solo para macOS."

ARQ="$(uname -m)"
case "$ARQ" in
  x86_64) azul "Mac con procesador Intel" ;;
  arm64)  azul "Mac con chip Apple (serie M)" ;;
esac
azul "macOS $(sw_vers -productVersion)"

# ── 1. Herramientas de línea de comandos de Xcode ─────────────────────────
if ! xcode-select -p >/dev/null 2>&1; then
  ojo "Faltan las Herramientas de línea de comandos de Xcode."
  azul "Se abrirá una ventana de macOS para instalarlas."
  xcode-select --install 2>/dev/null || true
  morir "Cuando terminen de instalarse, vuelve a pegar el mismo mandato."
fi

# ── 2. Homebrew ───────────────────────────────────────────────────────────
# En Intel vive en /usr/local; en Apple Silicon, en /opt/homebrew.
for prefijo in /opt/homebrew /usr/local; do
  [ -x "$prefijo/bin/brew" ] && eval "$("$prefijo/bin/brew" shellenv)" && break
done

if ! command -v brew >/dev/null 2>&1; then
  ojo "Homebrew no está instalado. Hace falta para ffmpeg y Python."
  r="$(preguntar '¿Lo instalo ahora? [S/n]' s)"
  case "$r" in
    [SsYy]*|"")
      azul "Instalando Homebrew (te pedirá tu contraseña)…"
      NONINTERACTIVE=1 /bin/bash -c \
        "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
        || morir "No se pudo instalar Homebrew. Instálalo desde https://brew.sh y repite."
      for prefijo in /opt/homebrew /usr/local; do
        [ -x "$prefijo/bin/brew" ] && eval "$("$prefijo/bin/brew" shellenv)" && break
      done
      ;;
    *) morir "Sin Homebrew no puedo seguir. Instálalo desde https://brew.sh" ;;
  esac
fi
azul "Homebrew en $(brew --prefix)"

# ── 3. Dependencias ───────────────────────────────────────────────────────
# python-tk aparte: el Python de Homebrew no trae Tk, y el de macOS usa un Tk
# 8.5 antiguo con el que la ventana se ve mal y da problemas.
FALTAN=()
brew list ffmpeg          >/dev/null 2>&1 || FALTAN+=(ffmpeg)
brew list python@3.12     >/dev/null 2>&1 || FALTAN+=(python@3.12)
brew list python-tk@3.12  >/dev/null 2>&1 || FALTAN+=(python-tk@3.12)
# yt-dlp necesita un motor de JavaScript para resolver los formatos de YouTube.
command -v node >/dev/null 2>&1 || brew list node >/dev/null 2>&1 || FALTAN+=(node)

if [ ${#FALTAN[@]} -gt 0 ]; then
  azul "Instalando: ${FALTAN[*]}  (esto es lo que más tarda)"
  brew install "${FALTAN[@]}"
else
  azul "Dependencias: ya están todas"
fi

PY="$(brew --prefix)/opt/python@3.12/bin/python3.12"
[ -x "$PY" ] || PY="$(command -v python3)"
azul "Python: $PY"

# ── 4. Entorno propio ─────────────────────────────────────────────────────
azul "Preparando el entorno en $BASE"
mkdir -p "$BASE"
rm -rf "$VENV"
"$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip

azul "Descargando aacyoutube y sus dependencias…"
"$VENV/bin/python" -m pip install --quiet --upgrade \
  "https://github.com/$REPO/archive/refs/heads/$RAMA.tar.gz" \
  || morir "No se pudo instalar desde GitHub. ¿Tienes conexión?"

"$VENV/bin/python" -c "import tkinter" 2>/dev/null \
  || ojo "Tkinter no está disponible: la ventana no abrirá. Prueba: brew install python-tk@3.12"

# ── 5. La app en Aplicaciones ─────────────────────────────────────────────
# Es un envoltorio: un guion que llama al entorno, no un binario compilado.
azul "Creando $APP"
SUDO=""
[ -w /Applications ] || SUDO="sudo"
$SUDO rm -rf "$APP"
$SUDO mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

$SUDO tee "$APP/Contents/MacOS/aacyoutube" >/dev/null <<LANZADOR
#!/bin/bash
exec "$VENV/bin/python" -m aacyoutube "\$@"
LANZADOR
$SUDO chmod +x "$APP/Contents/MacOS/aacyoutube"

$SUDO tee "$APP/Contents/Info.plist" >/dev/null <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>aacyoutube</string>
  <key>CFBundleDisplayName</key><string>aacyoutube</string>
  <key>CFBundleExecutable</key><string>aacyoutube</string>
  <key>CFBundleIdentifier</key><string>com.thlcorporation.aacyoutube</string>
  <key>CFBundleIconFile</key><string>aacyoutube</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>2.0.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.music</string>
  <key>NSRequiresAquaSystemAppearance</key><false/>
</dict>
</plist>
PLIST

ICONO="$("$VENV/bin/python" -c 'import aacyoutube.core as c; print(c.assets_dir() / "aacyoutube.icns")' 2>/dev/null)"
[ -f "$ICONO" ] && $SUDO cp "$ICONO" "$APP/Contents/Resources/aacyoutube.icns"
$SUDO touch "$APP"   # refresca el icono en el Finder

# ── 6. El mandato de terminal ─────────────────────────────────────────────
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/aacyoutube" <<LANZADOR
#!/bin/bash
exec "$VENV/bin/python" -m aacyoutube "\$@"
LANZADOR
chmod +x "$HOME/.local/bin/aacyoutube"

# ── Listo ─────────────────────────────────────────────────────────────────
echo
azul "Instalado."
"$VENV/bin/python" -m aacyoutube --doctor 2>/dev/null | sed 's/^/    /' || true
echo
echo "    Ábrela desde Launchpad, o en la terminal:  aacyoutube"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo; ojo "Para el mandato de terminal, añade a ~/.zshrc:"
     echo '    export PATH="$HOME/.local/bin:$PATH"' ;;
esac

r="$(preguntar '¿Abro la app ahora? [S/n]' n)"
case "$r" in [SsYy]*) open "$APP" ;; esac
