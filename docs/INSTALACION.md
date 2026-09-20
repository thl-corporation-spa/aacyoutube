# Instalación

- [macOS (Intel y serie M)](#macos)
- [Linux](#linux)
- [Sin instalador, desde el código](#desde-el-código)
- [Actualizar](#actualizar)
- [Desinstalar](#desinstalar)

---

## macOS

### Una línea y listo

Abre la app **Terminal** y pega:

```bash
curl -fsSL https://raw.githubusercontent.com/thl-corporation-spa/aacyoutube/main/scripts/instalar-mac.sh | bash
```

Hace todo por ti:

1. Comprueba las **Herramientas de línea de comandos de Xcode** y las pide si faltan.
2. Instala **Homebrew** si no lo tienes (preguntando antes).
3. Instala **ffmpeg**, **Python 3.12**, **python-tk** y **Node** con `brew`.
4. Crea un entorno propio en `~/Library/Application Support/aacyoutube`.
5. Descarga aacyoutube desde GitHub y lo instala ahí.
6. Monta **aacyoutube.app** en `Aplicaciones`, con su icono.
7. Deja el mandato `aacyoutube` en `~/.local/bin`.

Funciona igual en Intel que en Apple Silicon: no descarga ningún binario ya compilado, así que no depende de la arquitectura.

**Y no hay aviso de Gatekeeper.** La app se construye en tu Mac en lugar de bajarse hecha, así que macOS no la pone en cuarentena.

La primera vez tarda unos minutos, sobre todo compilando o bajando ffmpeg.

### Qué deja instalado, y cómo quitarlo

| | |
|---|---|
| La app | `/Applications/aacyoutube.app` — un envoltorio, no un binario |
| El programa | `~/Library/Application Support/aacyoutube/venv` |
| El mandato | `~/.local/bin/aacyoutube` |
| Los ajustes | `~/Library/Application Support/aacyoutube/config.json` |

Para desinstalar:

```bash
rm -rf /Applications/aacyoutube.app ~/Library/Application\ Support/aacyoutube ~/.local/bin/aacyoutube
```

Tu música descargada no se toca. `ffmpeg` y compañía se quedan; quítalos con `brew uninstall` si no los quieres.

### El aviso de macOS

> **«No se puede abrir porque Apple no puede comprobar si contiene software malicioso.»**
> **«aacyoutube está dañada y no se puede abrir.»**

No está dañada. macOS marca todo lo que llega de internet sin estar firmado con una cuenta de desarrollador de Apple (99 USD al año), y aacyoutube se firma solo de forma *ad-hoc*.

Sal del paso de una de estas dos formas:

```bash
# La directa: quitar la marca de cuarentena
xattr -dr com.apple.quarantine /Applications/aacyoutube.app
```

O bien, sin terminal: clic derecho sobre la app → **Abrir** → **Abrir** en el diálogo. Solo la primera vez.

### ¿Hace falta instalar ffmpeg?

No. El `.dmg` lleva `ffmpeg` y `ffprobe` dentro de la app. Si algún día falta, aacyoutube también busca el de [Homebrew](https://brew.sh) en `/opt/homebrew/bin` (Apple Silicon) y `/usr/local/bin` (Intel):

```bash
brew install ffmpeg
```

---

## Linux

Probado en Fedora y Ubuntu; el instalador también reconoce Debian, Arch y openSUSE.

```bash
git clone https://github.com/thl-corporation-spa/aacyoutube.git
cd aacyoutube
./install.sh
```

Esto hace cuatro cosas:

1. **Instala lo que falte del sistema** con tu gestor de paquetes — te pedirá la contraseña solo para este paso:

   | | Fedora | Ubuntu / Debian |
   |---|---|---|
   | Conversión de audio | `ffmpeg` o `ffmpeg-free` | `ffmpeg` |
   | Interfaz gráfica | `python3-tkinter` | `python3-tk` |
   | Motor JavaScript | `nodejs` | `nodejs` |

2. **Crea un entorno propio** en `~/.local/share/aacyoutube/venv` con yt-dlp y la app. Así no choca con el Python del sistema, que en Fedora 38+ y Ubuntu 23.04+ bloquea `pip` (el error `externally-managed-environment`).

3. **Deja el mandato `aacyoutube`** en `~/.local/bin`.

4. **Añade la app al menú**, con su icono.

Si `~/.local/bin` no está en tu `PATH`, el instalador te avisa y te dice qué añadir a `~/.bashrc`.

### Sobre ffmpeg en Fedora

El `ffmpeg` completo vive en [RPM Fusion](https://rpmfusion.org). Si no lo tienes habilitado, el instalador usa `ffmpeg-free` de los repositorios oficiales, que incluye el codificador AAC nativo y sirve perfectamente.

Para el completo:

```bash
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install ffmpeg
```

### Sin tocar paquetes del sistema

```bash
./packaging/linux/instalar.sh --sin-root
```

Instala solo la parte del usuario y te dice qué falta por poner a mano.

### En otra ruta

```bash
AACY_PREFIX=/opt/aacyoutube ./packaging/linux/instalar.sh
```

---

## Desde el código

Sin instalador, en cualquier sistema con Python 3.10 o superior:

```bash
git clone https://github.com/thl-corporation-spa/aacyoutube.git
cd aacyoutube
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e .
python -m aacyoutube
```

Necesitas `ffmpeg` y `tkinter` en el sistema. Comprueba con:

```bash
python -m aacyoutube --doctor
```

### Compilar tu propia app de macOS

En un Mac, con Python 3 instalado:

```bash
./install.sh --desde-codigo
```

Genera `dist/<arquitectura>/aacyoutube.app` y su `.dmg`, compilados para el Mac donde lo ejecutas.

---

## Actualizar

**macOS** — vuelve a ejecutar la misma línea de instalación: reemplaza la versión anterior.

**Linux** — desde la carpeta del repositorio:

```bash
git pull
./install.sh
```

**Solo yt-dlp** (YouTube cambia a menudo y suele ser lo único que hay que refrescar):

```bash
~/.local/share/aacyoutube/venv/bin/pip install --upgrade yt-dlp
```

---

## Desinstalar

**Linux**

```bash
./packaging/linux/desinstalar.sh
```

**macOS**

```bash
rm -rf /Applications/aacyoutube.app
```

En los dos casos, los ajustes quedan en `~/.config/aacyoutube` (Linux) o `~/Library/Application Support/aacyoutube` (macOS), y **tu música descargada no se toca**.
