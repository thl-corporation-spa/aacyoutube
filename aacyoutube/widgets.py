"""Controles dibujados a mano sobre Canvas.

Tk no trae botones redondeados, interruptores ni controles segmentados, y los
nativos se ven de otra época. Son pocos y contenidos, así que se dibujan aquí
con la misma paleta que el resto de la interfaz.
"""

from __future__ import annotations

import sys
import tkinter as tk

from aacyoutube.theme import RADIUS, round_rect

IS_MAC_MENU = sys.platform == "darwin"


class _CanvasWidget(tk.Canvas):
    """Base común: fondo transparente respecto al padre y repintado perezoso."""

    def __init__(self, parent, theme, bg=None, **kw):
        self.t = theme
        self._bg = bg or theme["bg"]
        super().__init__(parent, highlightthickness=0, bd=0, background=self._bg,
                         takefocus=0, **kw)
        self.bind("<Configure>", lambda _e: self._redraw())

    _anim = None

    def _redraw(self):  # pragma: no cover - lo implementa cada control
        pass

    def destroy(self):
        """Corta cualquier animación pendiente antes de irse."""
        if self._anim:
            try:
                self.after_cancel(self._anim)
            except Exception:  # noqa: BLE001 - el intérprete Tk puede haber muerto ya
                pass
            self._anim = None
        super().destroy()


class Button(_CanvasWidget):
    """Botón redondeado con estados de reposo, hover, pulsado y deshabilitado.

    variant: 'accent' (acción principal), 'ghost' (contorno) o 'plain' (texto).
    """

    PADDING = {"sm": (12, 7), "md": (18, 10), "lg": (22, 12)}

    def __init__(self, parent, theme, text, command=None, variant="accent",
                 size="md", bg=None, icon=None, width=None):
        self.t = theme
        self.text = text
        self.icon = icon
        self.command = command
        self.variant = variant
        self.size = size
        self._state = "normal"
        self._hover = False
        self._pressed = False

        font = theme.font("body_bold" if variant == "accent" else "body")
        self._font = font
        pad_x, pad_y = self.PADDING[size]
        label = f"{icon}  {text}" if icon else text
        w = width or font.measure(label) + pad_x * 2
        h = font.metrics("linespace") + pad_y * 2

        super().__init__(parent, theme, bg=bg, width=w, height=h)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ── estado ────────────────────────────────────────────────────────────
    def set_state(self, state: str):
        self._state = state
        self.configure(cursor="" if state == "disabled" else "hand2")
        self._redraw()

    def set_text(self, text: str, icon=None):
        self.text = text
        if icon is not None:
            self.icon = icon
        self._redraw()

    # ── eventos ───────────────────────────────────────────────────────────
    def _on_enter(self, _e):
        self._hover = True
        if self._state != "disabled":
            self.configure(cursor="hand2")
        self._redraw()

    def _on_leave(self, _e):
        self._hover = self._pressed = False
        self._redraw()

    def _on_press(self, _e):
        if self._state == "disabled":
            return
        self._pressed = True
        self._redraw()

    def _on_release(self, _e):
        was_pressed, self._pressed = self._pressed, False
        self._redraw()
        if was_pressed and self._state != "disabled" and self.command:
            self.command()

    # ── pintura ───────────────────────────────────────────────────────────
    def _colors(self):
        c = self.t.c
        if self._state == "disabled":
            if self.variant == "accent":
                return c["surface_hi"], None, c["text_faint"]
            return self._bg, c["border"], c["text_faint"]
        if self.variant == "accent":
            fill = c["accent_lo"] if self._pressed else (c["accent_hi"] if self._hover else c["accent"])
            return fill, None, c["on_accent"]
        if self.variant == "ghost":
            fill = c["surface_hi"] if (self._hover or self._pressed) else self._bg
            edge = c["border_hi"] if self._hover else c["border"]
            return fill, edge, c["text"]
        fill = c["surface_hi"] if (self._hover or self._pressed) else self._bg
        return fill, None, c["text_dim"] if not self._hover else c["text"]

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        fill, edge, fg = self._colors()
        round_rect(self, 1, 1, w - 1, h - 1, RADIUS["md"],
                   fill=fill, outline=edge or fill, width=1)
        label = f"{self.icon}  {self.text}" if self.icon else self.text
        self.create_text(w / 2, h / 2 + (1 if self._pressed else 0), text=label,
                         fill=fg, font=self._font)


class Segmented(_CanvasWidget):
    """Control segmentado: una pastilla que se desliza bajo la opción elegida."""

    def __init__(self, parent, theme, options, variable, command=None, bg=None, height=None):
        self.options = list(options)  # [(valor, etiqueta), …]
        self.var = variable
        self.command = command
        self._font = theme.font("body_bold")
        self._hover = None
        self._thumb_x = None
        self._anim = None

        pad = 14
        widths = [self._font.measure(lbl) + pad * 2 for _v, lbl in self.options]
        self._seg_w = max(widths)
        h = height or self._font.metrics("linespace") + 18

        super().__init__(parent, theme, bg=bg, width=self._seg_w * len(self.options) + 8, height=h)
        self.configure(cursor="hand2")
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.var.trace_add("write", lambda *_a: self._animate_to_selection())

    def _index_at(self, x):
        idx = int((x - 4) // self._seg_w)
        return max(0, min(idx, len(self.options) - 1))

    def _on_motion(self, e):
        idx = self._index_at(e.x)
        if idx != self._hover:
            self._hover = idx
            self._redraw()

    def _on_leave(self, _e):
        self._hover = None
        self._redraw()

    def _on_click(self, e):
        value = self.options[self._index_at(e.x)][0]
        if value != self.var.get():
            self.var.set(value)
            if self.command:
                self.command(value)

    def _selected_index(self):
        current = self.var.get()
        return next((i for i, (v, _l) in enumerate(self.options) if v == current), 0)

    def _target_x(self):
        return 4 + self._selected_index() * self._seg_w

    def _animate_to_selection(self):
        if self._anim:
            self.after_cancel(self._anim)
            self._anim = None
        target = self._target_x()
        if self._thumb_x is None:
            self._thumb_x = target
            self._redraw()
            return

        def step():
            delta = target - self._thumb_x
            if abs(delta) < 0.6:
                self._thumb_x = target
                self._anim = None
            else:
                self._thumb_x += delta * 0.35  # suavizado exponencial
                self._anim = self.after(12, step)
            self._redraw()

        step()

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        c = self.t.c
        round_rect(self, 0, 0, w, h, RADIUS["md"], fill=c["surface_hi"], outline=c["surface_hi"])
        if self._thumb_x is None:
            self._thumb_x = self._target_x()
        round_rect(self, self._thumb_x, 4, self._thumb_x + self._seg_w, h - 4,
                   RADIUS["sm"] + 2, fill=c["accent"], outline=c["accent"])
        selected = self._selected_index()
        for i, (_value, label) in enumerate(self.options):
            x = 4 + i * self._seg_w + self._seg_w / 2
            if i == selected:
                fg = c["on_accent"]
            elif i == self._hover:
                fg = c["text"]
            else:
                fg = c["text_dim"]
            self.create_text(x, h / 2, text=label, fill=fg, font=self._font)


class Switch(_CanvasWidget):
    """Interruptor tipo iOS, con el pomo animado."""

    W, H = 42, 24

    def __init__(self, parent, theme, variable, command=None, bg=None):
        self.var = variable
        self.command = command
        self._knob = None
        self._anim = None
        super().__init__(parent, theme, bg=bg, width=self.W, height=self.H)
        self.configure(cursor="hand2")
        self.bind("<Button-1>", self._toggle)
        self.var.trace_add("write", lambda *_a: self._animate())
        self.after(0, self._animate)

    def _toggle(self, _e):
        self.var.set(not self.var.get())
        if self.command:
            self.command(self.var.get())

    def _target(self):
        return self.W - self.H / 2 - 3 if self.var.get() else self.H / 2 + 3

    def _animate(self):
        if self._anim:
            self.after_cancel(self._anim)
            self._anim = None
        target = self._target()
        if self._knob is None:
            self._knob = target
            self._redraw()
            return

        def step():
            delta = target - self._knob
            if abs(delta) < 0.5:
                self._knob = target
                self._anim = None
            else:
                self._knob += delta * 0.35
                self._anim = self.after(12, step)
            self._redraw()

        step()

    def _redraw(self):
        self.delete("all")
        c = self.t.c
        on = self.var.get()
        if self._knob is None:
            self._knob = self._target()
        track = c["accent"] if on else c["track"]
        round_rect(self, 1, 1, self.W - 1, self.H - 1, RADIUS["pill"], fill=track, outline=track)
        r = self.H / 2 - 4
        self.create_oval(self._knob - r, self.H / 2 - r, self._knob + r, self.H / 2 + r,
                         fill=c["on_accent"] if on else c["text_dim"], outline="")


class Meter(_CanvasWidget):
    """Barra de progreso fina. En modo indeterminado recorre un pulso de ida y vuelta."""

    def __init__(self, parent, theme, height=6, bg=None, color=None):
        self._value = 0.0
        self._indeterminate = False
        self._phase = 0.0
        self._anim = None
        self._color = color
        super().__init__(parent, theme, bg=bg, height=height)

    def set(self, value: float):
        """Progreso 0–100; detiene el modo indeterminado."""
        self._stop()
        self._indeterminate = False
        self._value = max(0.0, min(100.0, value))
        self._redraw()

    def start_indeterminate(self):
        if self._indeterminate:
            return
        self._indeterminate = True
        self._phase = 0.0
        self._tick()

    def set_color(self, color):
        self._color = color
        self._redraw()

    def _stop(self):
        if self._anim:
            self.after_cancel(self._anim)
            self._anim = None

    def _tick(self):
        self._phase = (self._phase + 0.018) % 1.0
        self._redraw()
        self._anim = self.after(16, self._tick)

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        c = self.t.c
        fill = self._color or c["accent"]
        round_rect(self, 0, 0, w, h, h / 2, fill=c["track"], outline=c["track"])
        if self._indeterminate:
            span = w * 0.35
            # Triángulo 0→1→0 suavizado: el pulso va y vuelve sin tirones.
            tri = 1 - abs(1 - 2 * self._phase)
            eased = tri * tri * (3 - 2 * tri)
            center = -span / 2 + (w + span) * eased
            x1 = max(0, min(center - span / 2, w))
            x2 = max(0, min(center + span / 2, w))
            if x2 - x1 > 1:
                round_rect(self, x1, 0, x2, h, h / 2, fill=fill, outline=fill)
        elif self._value > 0:
            end = max(h, w * self._value / 100)
            round_rect(self, 0, 0, end, h, h / 2, fill=fill, outline=fill)


class Card(tk.Canvas):
    """Panel con esquinas redondeadas que aloja widgets normales dentro."""

    def __init__(self, parent, theme, padding=16, radius=None, bg=None, **kw):
        self.t = theme
        self._pad = padding
        self._radius = radius or RADIUS["lg"]
        self._outer_bg = bg or theme["bg"]
        super().__init__(parent, highlightthickness=0, bd=0,
                         background=self._outer_bg, takefocus=0, **kw)

        self.body = tk.Frame(self, background=theme["surface"])
        self._window = self.create_window(padding, padding, window=self.body, anchor="nw")
        self.bind("<Configure>", self._on_configure)
        self.body.bind("<Configure>", self._on_body)

    def _on_body(self, _e):
        """El Canvas se ajusta a lo que mida su contenido."""
        self.configure(height=self.body.winfo_reqheight() + self._pad * 2)

    def _on_configure(self, _e):
        w, h = self.winfo_width(), self.winfo_height()
        self.delete("bg")
        c = self.t.c
        round_rect(self, 0, 0, w, h, self._radius,
                   fill=c["surface"], outline=c["border"], width=1, tags="bg")
        self.tag_lower("bg")
        self.itemconfigure(self._window, width=max(1, w - self._pad * 2))


class Field(tk.Frame):
    """Campo de texto de una línea.

    Usa el `tk.Entry` clásico en vez de `ttk.Entry`: acepta colores directos, así
    que se ve idéntico en clam (Linux) y en aqua (macOS), donde ttk ignora buena
    parte del estilo.
    """

    def __init__(self, parent, theme, textvariable, bg=None, width=None):
        self.t = theme
        super().__init__(parent, background=theme["border"], padx=1, pady=1)
        self.entry = tk.Entry(
            self, textvariable=textvariable, relief="flat", bd=0, width=width or 20,
            background=theme["input"], foreground=theme["text"],
            insertbackground=theme["accent"], font=theme.font("body"),
            highlightthickness=0, disabledbackground=theme["input"],
            selectbackground=theme["accent"], selectforeground=theme["on_accent"])
        self.entry.pack(fill="both", expand=True, ipady=7, ipadx=8)
        self.entry.bind("<FocusIn>", lambda _e: self.configure(background=theme["accent"]))
        self.entry.bind("<FocusOut>", lambda _e: self.configure(background=theme["border"]))


class Select(_CanvasWidget):
    """Desplegable propio: un botón dibujado más un `tk.Menu` emergente.

    `ttk.Combobox` se resiste a cambiar de color en clam y se ve ajeno en macOS;
    esto se ve igual en los dos y deja que el menú sea nativo donde lo hay.
    """

    def __init__(self, parent, theme, values, variable, command=None, bg=None, width=None):
        self.values = list(values)
        self.var = variable
        self.command = command
        self._font = theme.font("body")
        self._hover = False

        w = width or max(self._font.measure(str(v)) for v in self.values) + 46
        h = self._font.metrics("linespace") + 16
        super().__init__(parent, theme, bg=bg, width=w, height=h)
        self.configure(cursor="hand2")

        self.menu = tk.Menu(self, tearoff=0)
        if not IS_MAC_MENU:  # en macOS los menús son nativos e ignoran los colores
            self.menu.configure(background=theme["surface_hi"], foreground=theme["text"],
                                activebackground=theme["accent"],
                                activeforeground=theme["on_accent"],
                                bd=0, relief="flat", font=self._font)
        for value in self.values:
            self.menu.add_command(label=str(value), command=lambda v=value: self._pick(v))

        self.bind("<Button-1>", self._open)
        self.bind("<Enter>", lambda _e: (setattr(self, "_hover", True), self._redraw()))
        self.bind("<Leave>", lambda _e: (setattr(self, "_hover", False), self._redraw()))
        self.var.trace_add("write", lambda *_a: self._redraw())

    def _pick(self, value):
        self.var.set(value)
        if self.command:
            self.command(value)

    def _open(self, _e):
        self.menu.post(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + 2)

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        c = self.t.c
        edge = c["border_hi"] if self._hover else c["border"]
        round_rect(self, 1, 1, w - 1, h - 1, RADIUS["md"], fill=c["surface_hi"], outline=edge, width=1)
        self.create_text(14, h / 2, text=str(self.var.get()), anchor="w",
                         fill=c["text"], font=self._font)
        x, y = w - 17, h / 2 - 1
        self.create_line(x - 4, y - 1, x, y + 3, x + 4, y - 1,
                         fill=c["text_dim"] if not self._hover else c["text"],
                         width=1.6, capstyle="round", joinstyle="round")

