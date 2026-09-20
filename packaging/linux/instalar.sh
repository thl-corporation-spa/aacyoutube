#!/usr/bin/env bash
# Instala aacyoutube en Linux (Fedora, Ubuntu, Debian, Arch, openSUSE).
#
#   ./packaging/linux/instalar.sh            instalar o actualizar
#   ./packaging/linux/instalar.sh --sin-root no tocar paquetes del sistema
#
# Todo queda en tu usuario: no hace falta root salvo para las dependencias
# del sistema (ffmpeg, tkinter), y eso se pregunta antes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PREFIX="${AACY_PREFIX:-$HOME/.local}"
SHARE="$PREFIX/share/aacyoutube"
VENV="$SHARE/venv"
BIN="$PREFIX/bin"
NO_ROOT=0
[ "${1:-}" = "--sin-root" ] && NO_ROOT=1

say()  { printf '\033[1;31m▸\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m⚠\033[0m %s\n' "$*"; }

# ── 1. Dependencias del sistema ───────────────────────────────────────────
detect_pm() {
  for pm in dnf apt-get pacman zypper; do command -v "$pm" >/dev/null && { echo "$pm"; return; }; done
  echo ""
}

install_system_deps() {
  local pm missing=()
  pm="$(detect_pm)"
  command -v ffmpeg >/dev/null || missing+=(ffmpeg)
  python3 -c 'import tkinter' 2>/dev/null || missing+=(tkinter)
  # yt-dlp necesita un motor de JavaScript para resolver los formatos de YouTube.
  command -v node >/dev/null || command -v deno >/dev/null || command -v bun >/dev/null || missing+=(nodejs)

  [ ${#missing[@]} -eq 0 ] && { say "Dependencias del sistema: ya están todas"; return; }
  if [ "$NO_ROOT" = 1 ] || [ -z "$pm" ]; then
    warn "Faltan: ${missing[*]} — instálalas a mano y vuelve a ejecutar."
    return
  fi

  local pkgs=()
  case "$pm" in
    dnf)
      for m in "${missing[@]}"; do case "$m" in
        ffmpeg)  # ffmpeg completo vive en RPM Fusion; ffmpeg-free basta y está en los repos oficiales.
                 dnf list --available ffmpeg >/dev/null 2>&1 && pkgs+=(ffmpeg) || pkgs+=(ffmpeg-free) ;;
        tkinter) pkgs+=(python3-tkinter) ;;
        nodejs)  pkgs+=(nodejs) ;;
      esac; done
      say "Instalando: ${pkgs[*]}"; sudo dnf install -y "${pkgs[@]}" ;;
    apt-get)
      for m in "${missing[@]}"; do case "$m" in
        ffmpeg)  pkgs+=(ffmpeg) ;;
        tkinter) pkgs+=(python3-tk) ;;
        nodejs)  pkgs+=(nodejs) ;;
      esac; done
      say "Instalando: ${pkgs[*]}"; sudo apt-get update -qq && sudo apt-get install -y "${pkgs[@]}" ;;
    pacman)
      for m in "${missing[@]}"; do case "$m" in
        ffmpeg) pkgs+=(ffmpeg) ;; tkinter) pkgs+=(tk) ;; nodejs) pkgs+=(nodejs) ;;
      esac; done
      say "Instalando: ${pkgs[*]}"; sudo pacman -S --needed --noconfirm "${pkgs[@]}" ;;
    zypper)
      for m in "${missing[@]}"; do case "$m" in
        ffmpeg) pkgs+=(ffmpeg) ;; tkinter) pkgs+=(python3-tk) ;; nodejs) pkgs+=(nodejs) ;;
      esac; done
      say "Instalando: ${pkgs[*]}"; sudo zypper install -y "${pkgs[@]}" ;;
  esac
}

# ── 2. Entorno virtual propio ─────────────────────────────────────────────
# Un venv evita el error "externally-managed-environment" de pip en Fedora 38+
# y Ubuntu 23.04+, y deja yt-dlp actualizable sin tocar el Python del sistema.
install_app() {
  say "Instalando en $SHARE"
  mkdir -p "$SHARE" "$BIN"
  # --system-site-packages para que el venv vea el tkinter del sistema.
  [ -d "$VENV" ] || python3 -m venv --system-site-packages "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet --upgrade "$ROOT"

  cat > "$BIN/aacyoutube" <<LAUNCHER
#!/usr/bin/env bash
exec "$VENV/bin/python" -m aacyoutube "\$@"
LAUNCHER
  chmod +x "$BIN/aacyoutube"
}

# ── 3. Integración con el escritorio ──────────────────────────────────────
install_desktop() {
  local apps="$PREFIX/share/applications"
  local icons="$PREFIX/share/icons/hicolor"
  mkdir -p "$apps"
  for size in 16 32 64 128 256 512; do
    mkdir -p "$icons/${size}x${size}/apps"
    cp "$ROOT/aacyoutube/assets/icon-$size.png" "$icons/${size}x${size}/apps/aacyoutube.png"
  done
  sed "s|@EXEC@|$BIN/aacyoutube|g" "$ROOT/packaging/linux/aacyoutube.desktop.in" \
    > "$apps/aacyoutube.desktop"
  command -v update-desktop-database >/dev/null && update-desktop-database "$apps" 2>/dev/null || true
  command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -qtf "$icons" 2>/dev/null || true
  say "Añadido al menú de aplicaciones"
}

install_system_deps
install_app
install_desktop

echo
say "Listo. Abre «aacyoutube» desde el menú, o en la terminal:"
echo "    aacyoutube                 # ventana"
echo "    aacyoutube URL             # descarga directa"
echo "    aacyoutube --doctor        # revisa el entorno"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo; warn "$BIN no está en tu PATH. Añade a ~/.bashrc:"
     echo "    export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac
