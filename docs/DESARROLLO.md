# Desarrollo

## Montar el entorno

```bash
git clone https://github.com/thl-corporation-spa/aacyoutube.git
cd aacyoutube

# --system-site-packages para que el entorno vea el tkinter del sistema
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e ".[build]"

python -m aacyoutube            # la ventana
python -m aacyoutube --doctor   # revisar el entorno
```

## Estructura

```
aacyoutube/
├── core.py        descarga, rutas por sistema, dependencias. No importa Tk.
├── app.py         la ventana: composición, estado y cola de eventos
├── theme.py       paleta, tipografía, claro/oscuro y estilos ttk
├── widgets.py     controles dibujados sobre Canvas
├── cli.py         modo terminal y `--doctor`
└── assets/        iconos en todos los tamaños

packaging/
├── macos/         receta de PyInstaller, guion de compilación, .app y .dmg
└── linux/         instalador, desinstalador y entrada de menú

scripts/           instalador de macOS desde la última Release
tests/             pruebas del núcleo y de la interfaz
```

Dos reglas que conviene mantener:

- **`core.py` no importa Tkinter.** La terminal y las pruebas del núcleo funcionan sin entorno gráfico.
- **Los hooks de yt-dlp corren en otro hilo.** Solo pueden encolar eventos en `App.events`; quien toca Tk es `App._pump`, siempre en el hilo principal.

## Interfaz

Tk no trae botones redondeados, interruptores ni controles segmentados, y los nativos se ven de otra época. `widgets.py` los dibuja sobre `Canvas`:

| Control | Qué es |
|---|---|
| `Button` | Botón redondeado, variantes `accent`, `ghost` y `plain` |
| `Segmented` | Control segmentado con la pastilla animada |
| `Switch` | Interruptor tipo iOS |
| `Meter` | Barra de progreso, con modo indeterminado |
| `Card` | Panel de esquinas redondeadas que aloja widgets normales |
| `Field` | `tk.Entry` clásico con borde propio |
| `Select` | Desplegable propio, con `tk.Menu` |

Los campos usan los widgets **clásicos** de Tk, no los de ttk: aceptan colores directos, así que se ven igual en clam (Linux) y en aqua (macOS), donde ttk ignora buena parte del estilo.

Los colores nunca se escriben a mano en `app.py`: salen de `theme.py`, que además detecta si el escritorio va en claro u oscuro.

## Pruebas

```bash
python tests/test_core.py            # motor, sin red ni interfaz
xvfb-run -a python tests/test_gui_smoke.py   # la ventana, sin pantalla
```

En macOS, la segunda va directa, sin `xvfb-run`.

No usan pytest a propósito: se ejecutan con el Python pelado y CI no necesita instalar nada más.

### Revisar el aspecto

Para ver la ventana con datos de ejemplo, sin descargar nada:

```python
import tkinter as tk
from aacyoutube.app import App

root = tk.Tk()
app = App(root, dark=True)
app.events.put(("progress", "Artista - Canción", 42.0, "10 MB de 24 MB · 2.1 MB/s"))
app.events.put(("converting", "Otra canción"))
root.mainloop()
```

Las capturas de `docs/img/` se generan así bajo Xvfb, a 880×900.

## Compilar la app de macOS

Hace falta un Mac. Cada arquitectura se compila en su propia máquina: **no hay binario universal**, sino uno nativo por arquitectura.

```bash
pip install "pyinstaller>=6.6"
./packaging/macos/build.sh
```

Genera:

```
dist/<arquitectura>/aacyoutube.app
dist/<arquitectura>/aacyoutube-<versión>-macos-<arquitectura>.dmg
```

El guion, por orden: arma el `.icns` desde los PNG del repositorio, descarga un `ffmpeg` estático de la arquitectura, empaqueta con PyInstaller, firma *ad-hoc* y crea el `.dmg`.

La **firma ad-hoc** (`codesign -s -`) no es un lujo: en Apple Silicon un binario sin firma **no arranca**. No evita el aviso de Gatekeeper, que exigiría una cuenta de desarrollador de Apple de pago.

### Runners de macOS: no hay Intel

**GitHub no asigna runners Intel a esta cuenta.** No es cola ni cuota: el job se queda encolado indefinidamente y **sin ningún mensaje de error**, que es la parte que más despista.

Comprobado con [`comprobar-runners.yml`](../.github/workflows/comprobar-runners.yml), que lanza un `echo` por etiqueta:

| Etiqueta | Arquitectura | Resultado |
|---|---|---|
| `macos-13` | Intel | retirada por GitHub — encola para siempre |
| `macos-14` | arm64 | arranca |
| `macos-15` | arm64 | arranca |
| `macos-15-intel` | Intel | **nunca arranca** |

Por eso **el `.dmg` de Intel se compila de forma cruzada desde un runner Apple Silicon**:

1. Se instala el Python **universal2** de [python.org](https://www.python.org/downloads/macos/) — el de `setup-python` en un runner arm64 es solo arm64, y de ahí no se puede sacar una mitad Intel.
2. La receta de PyInstaller recibe `target_arch="x86_64"` vía `AACY_TARGET_ARCH`, y extrae esa mitad de cada binario universal.
3. El `ffmpeg` empotrado ya se descarga por arquitectura (`ffmpeg-darwin-x64`), así que encaja sin tocar nada.
4. El paso de verificación comprueba con `lipo -archs` que dentro del `.dmg` no se haya colado un binario arm64.

Lo que **no** se puede hacer así es *ejecutar* el resultado para probarlo: eso exige un Mac Intel de verdad. Por eso la verificación se queda en comprobar la arquitectura, la firma y el `minos` del binario.

Si algún día GitHub habilita los runners Intel para la cuenta, basta con devolver la matriz a `runner: macos-15-intel` con `cruzada: false`.

Si tienes un Mac Intel a mano, la vía directa sigue siendo:

```bash
./install.sh --desde-codigo
```

## Integración continua

[`ci.yml`](../.github/workflows/ci.yml) corre en cada `push` y cada pull request sobre Ubuntu, macOS Intel y macOS Apple Silicon, con Python 3.10 y 3.12: instala, ejecuta `--doctor`, abre la ventana bajo Xvfb y pasa las pruebas del núcleo.

Python 3.10 marca el mínimo, porque es lo que pide yt-dlp desde noviembre de 2025.

## Dependencias

| | Para qué | De dónde sale |
|---|---|---|
| **yt-dlp** | Descarga y extracción | pip, va dentro del `.app` |
| **ffmpeg** | Conversión a AAC, etiquetas, portada | Paquete del sistema en Linux; incluido en el `.app` |
| **Tkinter** | La ventana | Paquete del sistema en Linux; viene con Python en macOS |
| **Node / Deno / Bun** | Motor JS que yt-dlp necesita para YouTube | Paquete del sistema; opcional pero muy recomendable |

`ffmpeg` para el `.app` sale de [eugeneware/ffmpeg-static](https://github.com/eugeneware/ffmpeg-static), que publica binarios estáticos para `darwin-x64` y `darwin-arm64`. El guion de compilación pregunta por la última versión y cae a una fija conocida si la API de GitHub no responde.
