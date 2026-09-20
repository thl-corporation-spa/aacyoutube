# Solución de problemas

Antes que nada:

```bash
aacyoutube --doctor
```

Te dice qué falta. Casi todo lo de abajo sale ahí.

- [La descarga falla](#la-descarga-falla)
- [macOS](#macos)
- [Linux](#linux)
- [El audio o las etiquetas](#el-audio-o-las-etiquetas)
- [El iPod](#el-ipod)

---

## La descarga falla

### «Sign in to confirm you're not a bot» · «Unable to extract player response»

YouTube cambió algo. Casi siempre se arregla actualizando yt-dlp, que publica versiones cada pocos días:

```bash
# Linux, instalado con el instalador
~/.local/share/aacyoutube/venv/bin/pip install --upgrade yt-dlp

# macOS, con la app del .dmg: descarga la versión nueva desde Releases
# (yt-dlp va dentro de la app)

# Desde el código, con el entorno activado
pip install --upgrade yt-dlp
```

Si persiste, elige tu navegador en **Cookies del navegador**: con una sesión iniciada, YouTube deja de pedir verificación.

### «Requested format is not available»

Falta un **motor de JavaScript**. yt-dlp lo necesita para resolver los formatos de YouTube.

```bash
sudo dnf install nodejs      # Fedora
sudo apt install nodejs      # Ubuntu / Debian
brew install node            # macOS
```

Comprueba con `aacyoutube --doctor` que la línea `runtime JS` ya no dice «ninguno».

### «Video unavailable» · «Private video»

El vídeo no es público. Si tienes acceso con tu cuenta, elige tu navegador en **Cookies del navegador**.

### Solo baja una canción de un álbum

Es a propósito: **Descargar listas completas** viene apagado, para que un enlace de canción con `&list=` no arrastre la lista entera. Enciéndelo, o usa `--playlists` en la terminal.

### «could not copy Chrome cookie database»

Chrome bloquea sus cookies mientras está abierto. **Ciérralo del todo** y vuelve a intentarlo. Firefox no tiene este problema.

---

## macOS

### «aacyoutube está dañada y no se puede abrir»

No lo está. macOS marca lo que llega de internet sin firma de desarrollador de pago:

```bash
xattr -dr com.apple.quarantine /Applications/aacyoutube.app
```

### «Apple no puede comprobar si contiene software malicioso»

Clic derecho sobre la app → **Abrir** → **Abrir**. Solo la primera vez.

### «You can't open the application because it is not supported on this type of Mac»

Descargaste el `.dmg` de la otra arquitectura. Comprueba con  → **Acerca de este Mac** y baja el que toca:

- Chip M1/M2/M3/M4 → `arm64`
- Procesador Intel → `x86_64`

Para saber cuál instalaste:

```bash
file /Applications/aacyoutube.app/Contents/MacOS/aacyoutube
```

### La app abre y se cierra sola

Míralo desde la terminal, que sí muestra el error:

```bash
/Applications/aacyoutube.app/Contents/MacOS/aacyoutube
```

### «ffmpeg not found» con la app del .dmg

No debería pasar, porque va incluido. Como red de seguridad:

```bash
brew install ffmpeg
```

aacyoutube busca en `/opt/homebrew/bin` (Apple Silicon) y `/usr/local/bin` (Intel), que es donde Homebrew lo deja en cada caso.

### La ventana se ve borrosa en una pantalla Retina

Pasa si abres el programa con un Python sin soporte Retina. La app del `.dmg` viene con `NSHighResolutionCapable` activado y se ve nítida. Desde el código, usa el Python de [python.org](https://www.python.org/downloads/macos/) o de Homebrew, no el `/usr/bin/python3` del sistema.

---

## Linux

### `ModuleNotFoundError: No module named 'tkinter'`

```bash
sudo dnf install python3-tkinter    # Fedora
sudo apt install python3-tk         # Ubuntu / Debian
sudo pacman -S tk                   # Arch
```

### `error: externally-managed-environment`

Fedora 38+ y Ubuntu 23.04+ no dejan que `pip` escriba en el Python del sistema. Por eso el instalador crea un entorno propio: usa `./install.sh` en vez de `pip install` a pelo.

### `aacyoutube: command not found`

`~/.local/bin` no está en tu `PATH`. Añade a `~/.bashrc` (o `~/.zshrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Y recarga con `source ~/.bashrc`.

### La app no sale en el menú

```bash
update-desktop-database ~/.local/share/applications
```

En algunos escritorios hay que cerrar y volver a entrar en la sesión.

### `ffmpeg: command not found` en Fedora

El `ffmpeg` completo está en RPM Fusion. O habilitas el repositorio:

```bash
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install ffmpeg
```

O usas el de los repositorios oficiales, que también sirve:

```bash
sudo dnf install ffmpeg-free
```

### La ventana se ve enorme o diminuta en HiDPI

Tk sigue el escalado de X11. Ajústalo con:

```bash
echo "Xft.dpi: 144" | xrdb -merge     # 144 = 150 %
```

---

## El audio o las etiquetas

### El iPod no reproduce los archivos

Comprueba que salió AAC-LC a 44,1 kHz:

```bash
ffprobe -hide_banner -show_entries stream=codec_name,sample_rate,channels "archivo.m4a"
```

Tiene que decir `codec_name=aac`, `sample_rate=44100`, `channels=2`. Si pone `opus` o `48000`, el archivo viene de otra herramienta: vuelve a bajarlo con **Máxima calidad**.

### No aparece la portada

Algunos vídeos no traen miniatura utilizable. Míralo en el registro (**Ver detalles**): saldrá un aviso de `EmbedThumbnail`. El audio está bien igualmente.

### El artista sale mal

aacyoutube usa el campo `artist` de YouTube Music y, si no existe, el nombre del canal. Los vídeos normales de YouTube casi nunca traen `artist`, así que sale el canal. Los enlaces de **music.youtube.com** dan metadatos mucho mejores.

### Falta el número de pista

Solo se rellena si el vídeo lo trae o si lo descargas como lista. Un enlace suelto no tiene posición de la que sacarlo.

---

## El iPod

### No veo las canciones nuevas

Con Música o iTunes hay que **sincronizar** después de añadirlas a la biblioteca. Con Rockbox, actualiza la base de datos desde el menú del propio iPod.

### Los nombres salen cortados o con símbolos raros

aacyoutube ya escribe nombres compatibles con FAT32. Si aun así se ven raros, es la pantalla del iPod: los modelos antiguos no muestran todos los caracteres. Las etiquetas de dentro del archivo están bien.

---

## Sigue sin funcionar

Abre una [incidencia](../../issues/new) con:

1. La salida completa de `aacyoutube --doctor`
2. Lo que aparece en **Ver detalles** cuando falla
3. Tu sistema y versión (Fedora 41, Ubuntu 24.04, macOS 14 en M2…)
4. Un enlace de ejemplo que lo reproduzca, si puedes
