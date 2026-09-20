"""Ventana principal de aacyoutube."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from aacyoutube import __version__, core
from aacyoutube.theme import IS_MAC, SPACE, Theme
from aacyoutube.widgets import Button, Card, Field, Meter, Segmented, Select, Switch

MIN_W, MIN_H = 700, 560
DEFAULT_GEOMETRY = "880x900"

PLACEHOLDER = ("Pega aquí los enlaces de YouTube o YouTube Music\n"
               "— uno por línea: canciones, álbumes o listas")


def usable_geometry(geometry):
    """Descarta un tamaño de ventana inservible.

    Si la app se cierra minimizada o sin mapear, Tk devuelve algo como
    «1x1+0+0»; guardarlo dejaría la ventana en nada al volver a abrir.
    """
    try:
        size = str(geometry).split("+")[0]
        width, height = (int(part) for part in size.split("x"))
    except (ValueError, AttributeError):
        return None
    return geometry if width >= MIN_W and height >= MIN_H else None


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def human_time(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


class ScrollList(ttk.Frame):
    """Lista vertical con scroll que se adapta al ancho disponible."""

    def __init__(self, parent, theme):
        super().__init__(parent)
        self.t = theme
        self.canvas = tk.Canvas(self, background=theme["bg"], highlightthickness=0,
                                bd=0, height=120)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                 style="Vertical.TScrollbar")
        self.inner = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")

        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self._bar_shown = False

        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._window, width=e.width))
        for widget in (self.canvas, self.inner):
            widget.bind("<MouseWheel>", self._on_wheel)       # macOS y Windows
            widget.bind("<Button-4>", self._on_wheel)         # X11
            widget.bind("<Button-5>", self._on_wheel)

    def _on_scroll(self, first, last):
        """Muestra la barra solo cuando el contenido no cabe."""
        self.bar.set(first, last)
        needed = float(first) > 0.0 or float(last) < 1.0
        if needed and not self._bar_shown:
            self.bar.pack(side="right", fill="y")
        elif not needed and self._bar_shown:
            self.bar.pack_forget()
        self._bar_shown = needed

    def _on_inner(self, _e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_wheel(self, e):
        if e.num == 4:
            delta = -1
        elif e.num == 5:
            delta = 1
        else:  # en macOS el delta ya viene en «líneas»
            delta = -e.delta if IS_MAC else -e.delta // 120
        self.canvas.yview_scroll(int(delta), "units")

    def scroll_to_end(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()


class TrackRow(ttk.Frame):
    """Una pista en la lista de actividad: estado, nombre y detalle."""

    GLYPH = {"downloading": ("↓", "accent"), "converting": ("↻", "warning"),
             "done": ("✓", "success"), "error": ("✕", "danger")}

    def __init__(self, parent, theme, title):
        super().__init__(parent)
        self.t = theme
        self.columnconfigure(1, weight=1)

        self.icon = ttk.Label(self, text="↓", style="Dim.TLabel", width=2, anchor="center")
        self.icon.grid(row=0, column=0, rowspan=2, padx=(2, 10))
        self.name = ttk.Label(self, text=title, style="TLabel", anchor="w")
        self.name.grid(row=0, column=1, sticky="ew")
        self.detail = ttk.Label(self, text="En cola", style="Faint.TLabel", anchor="w")
        self.detail.grid(row=1, column=1, sticky="ew")
        self.meter = Meter(self, theme, height=4)
        self.meter.grid(row=2, column=1, sticky="ew", pady=(6, 0))

    def update_state(self, state, detail=None, percent=None):
        glyph, color = self.GLYPH.get(state, ("·", "text_dim"))
        self.icon.configure(text=glyph, foreground=self.t[color])
        if detail is not None:
            self.detail.configure(text=detail)
        if state == "converting":
            self.meter.set_color(self.t["warning"])
            self.meter.start_indeterminate()
        elif state in ("done", "error"):
            self.meter.set_color(self.t["success" if state == "done" else "danger"])
            self.meter.set(100)
        elif percent is not None:
            self.meter.set_color(self.t["accent"])
            self.meter.set(percent)


class App:
    def __init__(self, root, dark=None):
        self.root = root
        self.events = queue.Queue()
        self.rows: dict[str, TrackRow] = {}
        self.running = False
        self._pump_job = None
        self._alive = True

        self.config = core.load_config()
        self.t = Theme(root, dark=self.config.get("dark") if dark is None else dark)

        root.title("aacyoutube")
        root.configure(background=self.t["bg"])
        self._set_window_icon()
        root.minsize(MIN_W, MIN_H)
        root.geometry(usable_geometry(self.config.get("geometry")) or DEFAULT_GEOMETRY)

        self.folder = tk.StringVar(value=self.config.get("folder") or str(core.default_music_dir()))
        self.mode = tk.StringVar(value=self.config.get("mode", "max"))
        self.square = tk.BooleanVar(value=self.config.get("square", True))
        self.playlists = tk.BooleanVar(value=self.config.get("playlists", False))
        self.browser = tk.StringVar(value=self.config.get("browser", "ninguno"))

        self._build()
        self._check_dependencies()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._pump_job = root.after(80, self._pump)

    def _set_window_icon(self):
        """Icono de la ventana. En macOS lo pone el .app, así que aquí sobra."""
        if IS_MAC:
            return
        try:
            images = [tk.PhotoImage(file=str(core.assets_dir() / f"icon-{n}.png"))
                      for n in (32, 64, 128) if (core.assets_dir() / f"icon-{n}.png").is_file()]
            if images:
                self._icons = images  # Tk no retiene la referencia; hay que guardarla.
                self.root.iconphoto(True, *images)
        except tk.TclError:
            pass

    # ───────────────────────────── construcción ─────────────────────────────

    def _build(self):
        root, t = self.root, self.t
        outer = ttk.Frame(root, padding=(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"]))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        self._build_header(outer)
        self._build_links(outer)
        self._build_settings(outer)
        self._build_activity(outer)
        self._build_action_bar(outer)

    def _build_header(self, parent):
        t = self.t
        head = ttk.Frame(parent)
        head.grid(row=0, column=0, sticky="ew", pady=(0, SPACE["md"]))
        head.columnconfigure(1, weight=1)

        mark = tk.Canvas(head, width=44, height=44, highlightthickness=0, bd=0,
                         background=t["bg"], takefocus=0)
        mark.grid(row=0, column=0, rowspan=2, padx=(0, 14))
        from aacyoutube.theme import round_rect
        round_rect(mark, 2, 2, 42, 42, 13, fill=t["accent"], outline=t["accent"])
        mark.create_polygon(17, 13, 17, 31, 32, 22, fill=t["on_accent"], outline="")

        ttk.Label(head, text="aacyoutube", style="Title.TLabel").grid(row=0, column=1, sticky="sw")
        ttk.Label(head, text="Audio AAC de YouTube, etiquetado y listo para tu iPod",
                  style="Dim.TLabel").grid(row=1, column=1, sticky="nw")

        tools = ttk.Frame(head)
        tools.grid(row=0, column=2, rowspan=2, sticky="e")
        Button(tools, t, "Tema", command=self._toggle_theme, variant="plain", size="sm",
               icon="◐" if t.dark else "◑").pack(side="left", padx=(0, 6))
        Button(tools, t, "Abrir carpeta", command=self._open_folder, variant="ghost",
               size="sm", icon="⌂").pack(side="left")

    def _build_links(self, parent):
        t = self.t
        card = Card(parent, t, padding=SPACE["md"])
        card.grid(row=1, column=0, sticky="ew", pady=(0, SPACE["md"]))
        body = card.body
        body.columnconfigure(0, weight=1)

        top = tk.Frame(body, background=t["surface"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Enlaces", style="H2.TLabel", background=t["surface"]).grid(row=0, column=0, sticky="w")
        self.count_label = ttk.Label(top, text="", style="SurfaceFaint.TLabel")
        self.count_label.grid(row=0, column=1, sticky="w", padx=10)
        Button(top, t, "Pegar", command=self._paste, variant="ghost", size="sm",
               icon="⌘" if IS_MAC else "⎘", bg=t["surface"]).grid(row=0, column=2, padx=(0, 6))
        Button(top, t, "Limpiar", command=self._clear_urls, variant="plain", size="sm",
               bg=t["surface"]).grid(row=0, column=3)

        field = tk.Frame(body, background=t["border"], padx=1, pady=1)
        field.grid(row=1, column=0, sticky="ew")
        self.urls = tk.Text(field, height=4, wrap="none", relief="flat", bd=0,
                            background=t["input"], foreground=t["text_faint"],
                            insertbackground=t["accent"], font=t.font("body"),
                            padx=12, pady=10, highlightthickness=0,
                            selectbackground=t["accent"], selectforeground=t["on_accent"])
        self.urls.pack(fill="both", expand=True)
        self._placeholder_on = True
        self.urls.insert("1.0", PLACEHOLDER)
        self.urls.bind("<FocusIn>", self._placeholder_out)
        self.urls.bind("<FocusOut>", self._placeholder_in)
        self.urls.bind("<KeyRelease>", lambda _e: self._update_count())
        self.urls.bind("<<Paste>>", lambda _e: self.root.after(10, self._update_count))

    def _build_settings(self, parent):
        t = self.t
        card = Card(parent, t, padding=SPACE["md"])
        card.grid(row=2, column=0, sticky="ew", pady=(0, SPACE["md"]))
        body = card.body
        body.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(body, text="Calidad", style="H2.TLabel", background=t["surface"]
                  ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1
        seg = Segmented(body, t, [(k, v) for k, v in core.MODES.items()],
                        self.mode, bg=t["surface"])
        seg.grid(row=row, column=0, sticky="w")
        self.mode_hint = ttk.Label(body, text="", style="SurfaceDim.TLabel")
        self.mode_hint.grid(row=row, column=1, sticky="w", padx=12)
        # Enganchado a la variable: así el texto acompaña también a los cambios
        # que no vienen de un clic (los ajustes guardados, por ejemplo).
        self.mode.trace_add("write", lambda *_a: self._update_mode_hint())
        self._update_mode_hint()
        row += 1

        ttk.Separator(body, orient="horizontal").grid(row=row, column=0, columnspan=2,
                                                      sticky="ew", pady=SPACE["sm"] + 2)
        row += 1

        ttk.Label(body, text="Guardar en", style="Surface.TLabel").grid(row=row, column=0, sticky="w")
        folder_row = tk.Frame(body, background=t["surface"])
        folder_row.grid(row=row, column=1, sticky="ew", padx=(12, 0))
        folder_row.columnconfigure(0, weight=1)
        Field(folder_row, t, self.folder).grid(row=0, column=0, sticky="ew")
        Button(folder_row, t, "Elegir…", command=self._choose_folder, variant="ghost",
               size="sm", bg=t["surface"]).grid(row=0, column=1, padx=(8, 0))
        row += 1

        row = self._option_row(body, row, "Portada cuadrada",
                               "Recorta la miniatura al centro, como la carátula de un álbum",
                               self.square)
        row = self._option_row(body, row, "Descargar listas completas",
                               "Si está apagado, un enlace con «&list=» baja solo esa canción",
                               self.playlists)

        cookie_row = tk.Frame(body, background=t["surface"])
        cookie_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(11, 0))
        cookie_row.columnconfigure(0, weight=1)
        text = tk.Frame(cookie_row, background=t["surface"])
        text.grid(row=0, column=0, sticky="w")
        ttk.Label(text, text="Cookies del navegador", style="Surface.TLabel").pack(anchor="w")
        ttk.Label(text, text="Para Premium, contenido con edad o privado",
                  style="SurfaceFaint.TLabel").pack(anchor="w")
        Select(cookie_row, t, core.BROWSERS, self.browser, bg=t["surface"]
               ).grid(row=0, column=1, sticky="e")

    def _option_row(self, body, row, title, hint, variable):
        """Fila de ajuste: título y explicación a la izquierda, interruptor a la derecha."""
        t = self.t
        line = tk.Frame(body, background=t["surface"])
        line.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(11, 0))
        line.columnconfigure(0, weight=1)
        text = tk.Frame(line, background=t["surface"])
        text.grid(row=0, column=0, sticky="w")
        ttk.Label(text, text=title, style="Surface.TLabel").pack(anchor="w")
        ttk.Label(text, text=hint, style="SurfaceFaint.TLabel").pack(anchor="w")
        Switch(line, t, variable, bg=t["surface"]).grid(row=0, column=1, sticky="e")
        return row + 1

    def _build_activity(self, parent):
        t = self.t
        wrap = ttk.Frame(parent)
        wrap.grid(row=3, column=0, sticky="nsew", pady=(0, SPACE["md"]))
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(1, weight=1)

        head = ttk.Frame(wrap)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        head.columnconfigure(1, weight=1)
        ttk.Label(head, text="Actividad", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        self.log_button = Button(head, t, "Ver detalles", command=self._toggle_log,
                                 variant="plain", size="sm")
        self.log_button.grid(row=0, column=2, sticky="e")

        self.activity = ScrollList(wrap, t)
        self.activity.grid(row=1, column=0, sticky="nsew")
        self.empty = ttk.Label(self.activity.inner,
                               text="Todavía no hay descargas en esta sesión.",
                               style="Faint.TLabel")
        self.empty.pack(anchor="w", pady=12)

        self.log_frame = tk.Frame(wrap, background=t["border"], padx=1, pady=1)
        self.log = tk.Text(self.log_frame, height=8, wrap="word", relief="flat", bd=0,
                           background=t["input"], foreground=t["text_dim"],
                           font=t.font("mono"), padx=10, pady=8, state="disabled",
                           highlightthickness=0)
        self.log.pack(fill="both", expand=True)
        self._log_open = False

    def _build_action_bar(self, parent):
        t = self.t
        bar = ttk.Frame(parent)
        bar.grid(row=4, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        self.go = Button(bar, t, "Descargar", command=self._start, variant="accent",
                         size="lg", icon="↓")
        self.go.grid(row=0, column=0, rowspan=2, padx=(0, SPACE["md"]))

        self.status = ttk.Label(bar, text="Listo.", style="TLabel")
        self.status.grid(row=0, column=1, sticky="sw")
        self.substatus = ttk.Label(bar, text=self._env_line(), style="Faint.TLabel")
        self.substatus.grid(row=1, column=1, sticky="nw")

        self.meter = Meter(bar, t, height=6)
        self.meter.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(SPACE["sm"], 0))

    def _env_line(self):
        arch = core.mac_arch()
        where = f"macOS {arch}" if arch else ("Linux" if core.IS_LINUX else sys.platform)
        return f"v{__version__} · {where} · destino: {self.folder.get()}"

    # ───────────────────────────── interacciones ─────────────────────────────

    def _placeholder_out(self, _e=None):
        if self._placeholder_on:
            self.urls.delete("1.0", "end")
            self.urls.configure(foreground=self.t["text"])
            self._placeholder_on = False

    def _placeholder_in(self, _e=None):
        if not self.urls.get("1.0", "end").strip():
            self._placeholder_on = True
            self.urls.delete("1.0", "end")
            self.urls.insert("1.0", PLACEHOLDER)
            self.urls.configure(foreground=self.t["text_faint"])

    def _url_list(self):
        if self._placeholder_on:
            return []
        return [u.strip() for u in self.urls.get("1.0", "end").splitlines() if u.strip()]

    def _update_count(self):
        n = len(self._url_list())
        self.count_label.configure(text="" if not n else f"{n} enlace{'s' if n != 1 else ''}")

    def _update_mode_hint(self):
        self.mode_hint.configure(text=core.MODE_HINTS.get(self.mode.get(), ""))

    def _paste(self):
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        if not text:
            return
        self._placeholder_out()
        current = self.urls.get("1.0", "end").strip()
        self.urls.insert("end", ("\n" if current else "") + text)
        self._update_count()

    def _clear_urls(self):
        self.urls.delete("1.0", "end")
        self._placeholder_on = False
        self._placeholder_in()
        self._update_count()

    def _choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.folder.get(), title="Guardar la música en…")
        if chosen:
            self.folder.set(chosen)
            self.substatus.configure(text=self._env_line())

    def _open_folder(self):
        path = Path(self.folder.get()).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        core.reveal(path)

    def _toggle_log(self):
        self._log_open = not self._log_open
        if self._log_open:
            self.log_frame.grid(row=2, column=0, sticky="ew", pady=(SPACE["sm"], 0))
            self.log_button.set_text("Ocultar detalles")
        else:
            self.log_frame.grid_remove()
            self.log_button.set_text("Ver detalles")

    def _toggle_theme(self):
        """Cambia entre claro y oscuro repintando la ventana en el sitio."""
        if self.running:
            self.status.configure(text="Espera a que termine la descarga para cambiar el tema.",
                                  foreground=self.t["warning"])
            return

        dark = not self.t.dark
        self.config = {**self.config, **self._settings(), "dark": dark}
        core.save_config(self.config)
        urls = self._url_list()

        # Los estilos ttk y los colores están repartidos por todos los widgets,
        # así que sale más limpio rehacer la ventana que repintarla pieza a pieza.
        self._teardown()
        for child in self.root.winfo_children():
            if not isinstance(child, tk.Menu):   # la barra de menú de macOS se queda
                child.destroy()

        fresh = App(self.root, dark=dark)
        if urls:
            fresh._placeholder_out()
            fresh.urls.insert("1.0", "\n".join(urls))
            fresh._update_count()
        return fresh

    def _check_dependencies(self):
        problems = core.check_dependencies()
        if not problems:
            return
        self.go.set_state("disabled")
        self.status.configure(text="Falta una dependencia", foreground=self.t["danger"])
        self.substatus.configure(text=problems[0])
        for problem in problems:
            self._write_log("⚠ " + problem)

    # ───────────────────────────── descarga ─────────────────────────────

    def _settings(self):
        return {"folder": self.folder.get(), "mode": self.mode.get(),
                "square": self.square.get(), "playlists": self.playlists.get(),
                "browser": self.browser.get(), "dark": self.t.dark,
                # Solo se guarda si es un tamaño con el que se pueda volver a abrir.
                "geometry": usable_geometry(self.root.geometry())
                            or self.config.get("geometry") or DEFAULT_GEOMETRY}

    def _start(self):
        if self.running:
            return
        urls = self._url_list()
        if not urls:
            self.status.configure(text="Pega al menos un enlace.", foreground=self.t["warning"])
            self.urls.focus_set()
            return

        out = Path(self.folder.get()).expanduser()
        try:
            out.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("aacyoutube", f"No se puede escribir en la carpeta:\n{e}")
            return

        self.running = True
        self.go.set_state("disabled")
        self.go.set_text("Descargando…", icon="⋯")
        self.status.configure(text="Preparando…", foreground=self.t["text"])
        self.substatus.configure(text=f"{len(urls)} enlace(s) → {out}")
        self.meter.set_color(self.t["accent"])
        self.meter.start_indeterminate()
        self.empty.pack_forget()
        self._write_log(f"— {len(urls)} enlace(s) → {out}")

        kwargs = dict(out_dir=out, mode=self.mode.get(), cookies_browser=self.browser.get(),
                      square_cover=self.square.get(), playlists=self.playlists.get(),
                      progress_hook=self._hook, postprocessor_hook=self._pp_hook,
                      logger=_QueueLogger(self.events))
        threading.Thread(target=self._worker, args=(urls, kwargs), daemon=True).start()

    def _worker(self, urls, kwargs):
        try:
            code = core.download(urls, **kwargs)
            self.events.put(("done", code))
        except Exception as e:  # noqa: BLE001 — cualquier fallo se le muestra al usuario
            self.events.put(("log", f"✖ {e}"))
            self.events.put(("done", 1))

    # Los hooks corren en el hilo de descarga: solo encolan, nunca tocan Tk.
    def _hook(self, d):
        name = Path(d.get("filename") or d.get("info_dict", {}).get("title", "")).stem
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            pct = d.get("downloaded_bytes", 0) * 100 / total if total else 0
            bits = []
            if total:
                bits.append(f"{human_size(d.get('downloaded_bytes', 0))} de {human_size(total)}")
            if d.get("speed"):
                bits.append(f"{human_size(d['speed'])}/s")
            if d.get("eta"):
                bits.append(f"faltan {human_time(d['eta'])}")
            self.events.put(("progress", name, pct, " · ".join(bits)))
        elif d["status"] == "finished":
            self.events.put(("converting", name))
        elif d["status"] == "error":
            self.events.put(("failed", name))

    def _pp_hook(self, d):
        if d.get("status") != "finished":
            return
        if d.get("postprocessor") in ("EmbedThumbnail", "MoveFiles"):
            path = d.get("info_dict", {}).get("filepath") or ""
            self.events.put(("finished", Path(path).stem))

    def _row(self, name) -> TrackRow | None:
        if not name:
            return None
        if name not in self.rows:
            row = TrackRow(self.activity.inner, self.t, name)
            row.pack(fill="x", pady=(0, 12))
            self.rows[name] = row
            self.activity.scroll_to_end()
        return self.rows[name]

    def _write_log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _pump(self):
        """Pasa al hilo de la interfaz lo que dejaron los hooks de descarga."""
        if not self._alive:
            return
        # Al empezar, descarta el temporizador guardado: o somos nosotros mismos,
        # o es uno huérfano de una llamada directa a _pump().
        if self._pump_job is not None:
            self.root.after_cancel(self._pump_job)
            self._pump_job = None
        while True:
            try:
                ev = self.events.get_nowait()
            except queue.Empty:
                break
            kind = ev[0]
            if kind == "log":
                self._write_log(ev[1])
            elif kind == "progress":
                _k, name, pct, detail = ev
                self.status.configure(text=name or "Descargando…", foreground=self.t["text"])
                self.substatus.configure(text=detail)
                self.meter.set(pct)
                row = self._row(name)
                if row:
                    row.update_state("downloading", detail, pct)
            elif kind == "converting":
                self.status.configure(text="Convirtiendo a AAC y etiquetando…")
                self.meter.set_color(self.t["warning"])
                self.meter.start_indeterminate()
                row = self._row(ev[1])
                if row:
                    row.update_state("converting", "Convirtiendo a AAC y añadiendo portada…")
            elif kind == "finished":
                row = self._row(ev[1])
                if row:
                    row.update_state("done", "Listo")
            elif kind == "failed":
                row = self._row(ev[1])
                if row:
                    row.update_state("error", "No se pudo descargar")
            elif kind == "done":
                self._on_done(ev[1] == 0)
        self._pump_job = self.root.after(80, self._pump)

    def _on_done(self, ok):
        self.running = False
        self.go.set_state("normal")
        self.go.set_text("Descargar", icon="↓")
        for row in self.rows.values():
            if row.icon.cget("text") in ("↓", "↻"):
                row.update_state("done" if ok else "error", "Listo" if ok else "Terminó con errores")
        self.meter.set_color(self.t["success"] if ok else self.t["danger"])
        self.meter.set(100)
        self.status.configure(text="Listo" if ok else "Terminó con errores",
                              foreground=self.t["success" if ok else "danger"])
        self.substatus.configure(
            text="Arrastra los .m4a a Música/iTunes, al Finder o a Rockbox."
            if ok else "Mira «Ver detalles» para saber qué falló.")
        self._write_log("✔ Listo." if ok else "✖ Terminó con errores.")
        core.save_config({**self.config, **self._settings()})

    def _teardown(self):
        """Deja esta instancia inerte: sin temporizadores vivos.

        Sin esto, los `after` pendientes se disparan contra widgets ya
        destruidos y Tk escupe «invalid command name» en la terminal.
        """
        self._alive = False
        if self._pump_job is not None:
            try:
                self.root.after_cancel(self._pump_job)
            except tk.TclError:
                pass
            self._pump_job = None

    def _on_close(self):
        core.save_config({**self.config, **self._settings()})
        self._teardown()
        self.root.destroy()


class _QueueLogger:
    """Adaptador del logger de yt-dlp hacia la cola de eventos de la interfaz."""

    def __init__(self, events):
        self.events = events

    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.info(msg)

    def info(self, msg):
        self.events.put(("log", msg))

    def warning(self, msg):
        self.events.put(("log", "⚠ " + msg))

    def error(self, msg):
        self.events.put(("log", "✖ " + msg))


def run_gui(dark=None):
    root = tk.Tk()
    if IS_MAC:
        # Sin una barra de menú propia, macOS muestra la del intérprete «Python».
        menu = tk.Menu(root)
        edit = tk.Menu(menu, tearoff=0)
        for label, event in (("Cortar", "<<Cut>>"), ("Copiar", "<<Copy>>"), ("Pegar", "<<Paste>>")):
            edit.add_command(label=label,
                             command=lambda e=event: root.focus_get().event_generate(e))
        menu.add_cascade(label="Edición", menu=edit)
        root.configure(menu=menu)
    App(root, dark=dark)
    root.mainloop()
    return 0
