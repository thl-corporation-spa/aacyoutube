<div align="center">

<img src="aacyoutube/assets/icon-128.png" width="96" alt="">

# aacyoutube

**Descarga audio de YouTube y YouTube Music en AAC (`.m4a`), etiquetado, con portada y listo para tu iPod.**

Funciona en **Linux** (Fedora, Ubuntu, Debian, Arch, openSUSE) y en **macOS**, tanto con procesador **Intel** como con chip **Apple de la serie M**.

<img src="docs/img/ventana-dark.png" width="760" alt="Ventana de aacyoutube en tema oscuro">

</div>

---

## Qué hace

Pegas enlaces, pulsas **Descargar** y obtienes archivos que un iPod reproduce sin tocar nada más:

- **AAC-LC a 44,1 kHz y estéreo**, que es exactamente lo que espera un iPod. El audio de YouTube suele venir en Opus a 48 kHz, que el iPod no reproduce.
- **Etiquetas completas**: artista, título, álbum y número de pista. En una lista, el número sale de la posición si el vídeo no trae uno.
- **Portada incrustada**, recortada al centro en cuadrado como la carátula de un disco.
- **Nombres de archivo compatibles con FAT32**, el formato con el que vienen los iPod.
- Una carpeta por álbum o lista; las canciones sueltas quedan como `Artista - Título.m4a`.

## Instalar

### macOS (Intel y serie M)

Pega esto en la app **Terminal**:

```bash
curl -fsSL https://raw.githubusercontent.com/thl-corporation-spa/aacyoutube/main/scripts/instalar-mac.sh | bash
```

Y ya está. Instala lo que falte (Homebrew, ffmpeg, Python), monta la app en `Aplicaciones` y deja el mandato `aacyoutube` en la terminal. Funciona igual en Intel que en chip Apple.

Como la app **se construye en tu propio Mac** en vez de descargarse ya hecha, macOS no la marca en cuarentena: no verás el aviso de «está dañada» ni tendrás que abrirla con clic derecho.

La primera vez tarda unos minutos, casi todo instalando ffmpeg.

### Linux (Fedora, Ubuntu, Debian, Arch, openSUSE)

```bash
git clone https://github.com/thl-corporation-spa/aacyoutube.git
cd aacyoutube && ./install.sh
```

El instalador se encarga de todo: pone `ffmpeg`, `python3-tk` y Node si faltan (te pedirá la contraseña de administrador solo para eso), crea un entorno propio en `~/.local/share/aacyoutube` y añade la app al menú de aplicaciones.

Después, ábrela desde el menú o escribe `aacyoutube` en la terminal.

Para quitarla: `./packaging/linux/desinstalar.sh`.

## Usar

**Desde la ventana** — pega uno o varios enlaces (uno por línea), elige la calidad y pulsa **Descargar**. Los ajustes se recuerdan para la próxima vez.

**Desde la terminal**:

```bash
aacyoutube "https://music.youtube.com/watch?v=..."     # una canción
aacyoutube URL1 URL2 URL3                              # varias de una vez
aacyoutube --playlists "https://.../playlist?list=..." # un álbum entero
aacyoutube --copy URL                                  # sin recomprimir
aacyoutube -o ~/Música/iPod URL                        # otra carpeta
aacyoutube --doctor                                    # revisar el entorno
```

### Las dos calidades

| Modo | Qué hace | Cuándo usarlo |
|---|---|---|
| **Máxima calidad** | Coge la mejor fuente disponible y deja AAC a 256 kbps, 44,1 kHz | Por omisión. Lo que quieres casi siempre |
| **Original sin recomprimir** | Copia el AAC que YouTube ya sirve (~128 kbps), sin tocarlo | Si prefieres cero pérdida generacional y archivos más pequeños |

En **máxima calidad**, si tienes YouTube Music Premium y usas cookies, la fuente ya es AAC de 256 kbps y se copia tal cual. Si no, se parte del Opus (~160 kbps) y se codifica a AAC.

### Cookies del navegador

Para contenido de Premium, con restricción de edad o privado, elige tu navegador en **Cookies del navegador**. aacyoutube lee la sesión que ya tienes abierta; no le das ninguna contraseña.

## Documentación

| | |
|---|---|
| [Instalación](docs/INSTALACION.md) | Paso a paso por sistema, y qué hacer con los avisos de macOS |
| [Uso](docs/USO.md) | La ventana, la terminal y todas las opciones |
| [Solución de problemas](docs/SOLUCION-DE-PROBLEMAS.md) | Los fallos habituales y cómo salir de ellos |
| [Desarrollo](docs/DESARROLLO.md) | Estructura del código, pruebas y cómo publicar una versión |

## Cómo está hecho

Python y Tkinter, sin dependencias gráficas: los controles (botones, interruptores, barras) están dibujados sobre `Canvas` para que se vean iguales en GNOME, KDE y macOS. La descarga la hace [yt-dlp](https://github.com/yt-dlp/yt-dlp) y la conversión [ffmpeg](https://ffmpeg.org).

```
aacyoutube/
├── core.py      descarga, rutas por sistema, dependencias
├── app.py       la ventana
├── theme.py     paleta, tipografía y claro/oscuro
├── widgets.py   controles dibujados a mano
└── cli.py       modo terminal
```

## Licencia

[MIT](LICENSE). Descarga solo contenido que tengas derecho a descargar.
