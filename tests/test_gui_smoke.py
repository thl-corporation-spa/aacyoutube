#!/usr/bin/env python3
"""La ventana debe construirse, reaccionar y cerrarse sin lanzar nada.

No hay mainloop: se procesan los eventos a mano con update(), así corre igual
bajo xvfb en CI que en un escritorio real.
"""

import sys
import tempfile
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aacyoutube import core  # noqa: E402
from aacyoutube.app import App, human_size, human_time, usable_geometry  # noqa: E402

checks = []


def check(name, condition, detail=""):
    checks.append((name, bool(condition), detail))


# ── Formateo de cifras ────────────────────────────────────────────────────
check("bytes legibles", human_size(1536) == "1.5 KB", human_size(1536))
check("megas legibles", human_size(5_242_880) == "5.0 MB", human_size(5_242_880))
check("segundos legibles", human_time(45) == "45s", human_time(45))
check("minutos legibles", human_time(125) == "2m 05s", human_time(125))
check("horas legibles", human_time(3725) == "1h 02m", human_time(3725))

# ── Tamaño de ventana guardado ────────────────────────────────────────────
check("se acepta un tamaño normal", usable_geometry("880x900+10+10") == "880x900+10+10")
check("se descarta la ventana sin mapear", usable_geometry("1x1+0+0") is None)
check("se descarta un tamaño por debajo del mínimo", usable_geometry("300x200") is None)
check("se descarta un valor con basura", usable_geometry("no-es-un-tamaño") is None)
check("se descarta un valor vacío", usable_geometry(None) is None)

# ── Ventana ───────────────────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    core.CONFIG_FILE = Path(tmp) / "config.json"   # no tocar los ajustes reales

    for dark in (True, False):
        root = tk.Tk()
        root.withdraw()                            # sin ventana visible en CI
        app = App(root, dark=dark)
        root.update()
        tema = "oscuro" if dark else "claro"

        check(f"la ventana se construye en tema {tema}", app.root is root)

        # El marcador de posición no debe contarse como enlace.
        check(f"[{tema}] el texto de ayuda no es un enlace", app._url_list() == [])

        app._placeholder_out()
        app.urls.insert("1.0", "https://youtu.be/uno\n\nhttps://youtu.be/dos\n")
        app._update_count()
        root.update()
        check(f"[{tema}] las líneas vacías se descartan", len(app._url_list()) == 2,
              str(app._url_list()))
        check(f"[{tema}] el contador muestra el total", "2" in app.count_label.cget("text"),
              app.count_label.cget("text"))

        # Los eventos del hilo de descarga deben pintar una fila por pista.
        app.events.put(("progress", "Una canción", 42.0, "10 MB de 24 MB"))
        app.events.put(("converting", "Otra canción"))
        app.events.put(("finished", "Una canción"))
        app.events.put(("failed", "Una que falla"))
        app._pump()
        root.update()
        check(f"[{tema}] se crea una fila por pista", len(app.rows) == 3, str(list(app.rows)))
        check(f"[{tema}] la pista terminada se marca con ✓",
              app.rows["Una canción"].icon.cget("text") == "✓")
        check(f"[{tema}] la pista fallida se marca con ✕",
              app.rows["Una que falla"].icon.cget("text") == "✕")

        # Los controles deben responder sin reventar.
        app.mode.set("copy")
        root.update()
        check(f"[{tema}] el selector de calidad cambia el texto de ayuda",
              "128" in app.mode_hint.cget("text"), app.mode_hint.cget("text"))
        app.square.set(False)
        app.playlists.set(True)
        app._toggle_log()
        root.update()
        check(f"[{tema}] el registro se despliega", app._log_open)
        app._toggle_log()
        root.update()
        check(f"[{tema}] el registro se repliega", not app._log_open)

        # Cambiar de tema rehace la ventana y conserva los enlaces escritos.
        app._placeholder_out()
        app.urls.delete("1.0", "end")
        app.urls.insert("1.0", "https://youtu.be/conservado")
        app._update_count()
        swapped = app._toggle_theme()
        root.update()
        check(f"[{tema}] al cambiar de tema se repinta al contrario",
              swapped is not None and swapped.t.dark is not dark)
        check(f"[{tema}] al cambiar de tema se conservan los enlaces",
              swapped._url_list() == ["https://youtu.be/conservado"], str(swapped._url_list()))
        check(f"[{tema}] la ventana anterior queda inerte", not app._alive)
        app = swapped

        app._clear_urls()
        root.update()
        check(f"[{tema}] al limpiar vuelve el texto de ayuda", app._placeholder_on)

        # El fin de la descarga deja la interfaz utilizable otra vez.
        app.running = True
        app.events.put(("done", 0))
        app._pump()
        root.update()
        check(f"[{tema}] al terminar se puede volver a descargar", not app.running)

        app._on_close()

        # Cerrar con la ventana oculta no debe guardar un tamaño inservible.
        check(f"[{tema}] no se guarda un tamaño imposible",
              usable_geometry(core.load_config().get("geometry")) is not None,
              str(core.load_config().get("geometry")))

    # Los ajustes deben haber quedado guardados al cerrar.
    saved = core.load_config()
    check("los ajustes se guardan al cerrar", saved.get("mode") == "copy", str(saved))
    check("se recuerda el tema", "dark" in saved, str(saved))

failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f"  {'✔' if ok else '✖'} {name}" + (f"  — {detail}" if detail and not ok else ""))
print(f"\n{len(checks) - len(failed)}/{len(checks)} pruebas de interfaz correctas")
sys.exit(1 if failed else 0)
