# Instalación

- [macOS (Intel y serie M)](#macos)
- [Linux](#linux)
- [Sin instalador, desde el código](#desde-el-código)
- [Actualizar](#actualizar)
- [Desinstalar](#desinstalar)

---

## macOS

### Qué Mac tengo

Menú  → **Acerca de este Mac**. La línea «Chip» o «Procesador» te lo dice:

| Dice | Es | Descarga |
|---|---|---|
| Chip Apple M1, M2, M3, M4… | Apple Silicon | `…-macos-arm64.dmg` |
| Procesador Intel Core i5/i7/i9… | Intel | `…-macos-x86_64.dmg` |

Cada `.dmg` trae un binario **nativo** de su arquitectura, así que en un Mac con chip M no hace falta Rosetta.

Versiones mínimas: **macOS 10.15 Catalina** en Intel, **macOS 11 Big Sur** en Apple Silicon.

### Opción A — desde el navegador

1. Abre la página de [versiones publicadas](../../releases/latest) con tu sesión de GitHub iniciada (el repositorio es privado).
2. Descarga el `.dmg` que corresponde a tu Mac.
3. Ábrelo y arrastra **aacyoutube** a la carpeta `Applications`.
4. **La primera vez, ábrela con clic derecho → Abrir** y confirma en el aviso.

### Opción B — desde la terminal

Necesitas la [CLI de GitHub](https://cli.github.com), que sabe autenticarse en un repositorio privado:

```bash
brew install gh          # si no la tienes
gh auth login            # una sola vez

gh repo clone thl-corporation-spa/aacyoutube
cd aacyoutube
./install.sh
```

Detecta la arquitectura, descarga el `.dmg` correcto, lo instala en `/Applications` y le quita la marca de cuarentena, así que no verás ningún aviso.

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
git clone git@github.com:thl-corporation-spa/aacyoutube.git
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
git clone git@github.com:thl-corporation-spa/aacyoutube.git
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

**macOS** — vuelve a ejecutar `./scripts/instalar-macos.sh`, o descarga el `.dmg` nuevo y reemplaza la app.

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
