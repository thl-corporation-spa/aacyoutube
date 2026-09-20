# Desarrollo

## Montar el entorno

```bash
git clone git@github.com:thl-corporation-spa/aacyoutube.git
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

## Publicar una versión

1. Sube la versión en `aacyoutube/__init__.py` y `pyproject.toml` (tienen que coincidir).
2. Confirma los cambios.
3. Marca y empuja la etiqueta:

   ```bash
   git tag v2.1.0
   git push origin v2.1.0
   ```

El flujo [`build-macos.yml`](../.github/workflows/build-macos.yml) compila en `macos-13` (Intel) y `macos-14` (Apple Silicon), comprueba que cada binario es de su arquitectura, y sube los dos `.dmg` a la Release de la etiqueta. El texto de la Release sale de [`notas-release.md`](../packaging/macos/notas-release.md).

Cada job sube su propio `.dmg` **directamente a la Release**, sin pasar por los artefactos de Actions: los artefactos consumen la cuota de almacenamiento de la cuenta y los archivos de una Release no. El primer job que llega crea la Release y el segundo se encuentra con que ya existe.

También se puede lanzar a mano desde la pestaña **Actions** → **Compilar app de macOS** → **Run workflow**. Sin etiqueta no hay Release, así que ahí sí se guardan como artefactos, y ese paso no hace fallar la compilación si la cuota está llena.

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
