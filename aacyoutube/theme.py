"""Paleta, tipografía y estilos ttk.

Un único sitio donde viven los colores y las fuentes, para que la interfaz se
vea igual de intencionada en GNOME, en KDE y en macOS.
"""

from __future__ import annotations

import subprocess
import sys

IS_MAC = sys.platform == "darwin"

# Escala tipográfica y de espaciado: una sola serie, usada en toda la interfaz.
SPACE = {"xs": 4, "sm": 8, "md": 14, "lg": 20, "xl": 28}
RADIUS = {"sm": 6, "md": 10, "lg": 14, "pill": 999}

DARK = {
    "bg": "#0E1014",
    "surface": "#171A21",
    "surface_hi": "#1F242E",
    "input": "#12151B",
    "border": "#272D3A",
    "border_hi": "#394153",
    "text": "#E8EBF2",
    "text_dim": "#99A1B3",
    "text_faint": "#646C7E",
    "accent": "#FF4438",
    "accent_hi": "#FF5F55",
    "accent_lo": "#DC3628",
    "on_accent": "#FFFFFF",
    "success": "#3DDC84",
    "warning": "#F5A524",
    "danger": "#FF5A65",
    "track": "#252B37",
    "shadow": "#05070A",
}

LIGHT = {
    "bg": "#F4F5F8",
    "surface": "#FFFFFF",
    "surface_hi": "#F0F2F6",
    "input": "#FFFFFF",
    "border": "#DEE2E9",
    "border_hi": "#C6CCD8",
    "text": "#131720",
    "text_dim": "#5C6575",
    "text_faint": "#8B93A3",
    "accent": "#E03325",
    "accent_hi": "#F04234",
    "accent_lo": "#BE2418",
    "on_accent": "#FFFFFF",
    "success": "#1E9E5F",
    "warning": "#B7791F",
    "danger": "#D93F4C",
    "track": "#E6E9EF",
    "shadow": "#C9CDD6",
}

# Pilas tipográficas por sistema: la primera que exista es la que se usa.
_FONT_STACKS = {
    "darwin": ["SF Pro Text", ".AppleSystemUIFont", "Helvetica Neue", "Lucida Grande"],
    "linux": ["Inter", "Cantarell", "Ubuntu", "Noto Sans", "DejaVu Sans"],
    "win32": ["Segoe UI Variable Text", "Segoe UI", "Tahoma"],
}
_MONO_STACKS = {
    "darwin": ["SF Mono", "Menlo", "Monaco"],
    "linux": ["JetBrains Mono", "Fira Code", "Source Code Pro", "DejaVu Sans Mono", "Monospace"],
    "win32": ["Cascadia Mono", "Consolas", "Courier New"],
}


def system_prefers_dark() -> bool:
    """Lee la preferencia clara/oscura del escritorio; ante la duda, oscuro."""
    try:
        if IS_MAC:
            out = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                                 capture_output=True, text=True, timeout=2)
            return "dark" in out.stdout.strip().lower()
        out = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                             capture_output=True, text=True, timeout=2)
        value = out.stdout.strip().lower()
        if "dark" in value:
            return True
        if "light" in value:
            return False
        out = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                             capture_output=True, text=True, timeout=2)
        return "dark" in out.stdout.strip().lower()
    except (OSError, subprocess.SubprocessError):
        return True
    return True


def _first_available(stacks: dict, families: set[str]) -> str:
    stack = stacks.get(sys.platform) or stacks["linux"]
    lowered = {f.lower() for f in families}
    for name in stack:
        if name.lower() in lowered:
            return name
    return stack[-1]


class Theme:
    """Colores, fuentes y estilos ttk ya registrados en una ventana Tk."""

    def __init__(self, root, dark: bool | None = None):
        import tkinter.font as tkfont
        from tkinter import ttk

        self.root = root
        self.dark = system_prefers_dark() if dark is None else dark
        self.c = dict(DARK if self.dark else LIGHT)

        families = set(tkfont.families(root))
        ui = _first_available(_FONT_STACKS, families)
        mono = _first_available(_MONO_STACKS, families)
        # macOS renderiza las fuentes de sistema un punto más grandes que X11.
        base = 13 if IS_MAC else 10

        self.fonts = {
            "title": tkfont.Font(root=root, family=ui, size=base + 7, weight="bold"),
            "h2": tkfont.Font(root=root, family=ui, size=base + 2, weight="bold"),
            "body": tkfont.Font(root=root, family=ui, size=base),
            "body_bold": tkfont.Font(root=root, family=ui, size=base, weight="bold"),
            "small": tkfont.Font(root=root, family=ui, size=base - 1),
            "tiny": tkfont.Font(root=root, family=ui, size=base - 2),
            "mono": tkfont.Font(root=root, family=mono, size=base - 1),
        }

        self.style = ttk.Style(root)
        self.style.theme_use("clam")  # la única base ttk que deja repintarlo todo
        self._register_styles()

    # ── acceso corto a un color ────────────────────────────────────────────
    def __getitem__(self, key: str) -> str:
        return self.c[key]

    def font(self, key: str):
        return self.fonts[key]

    def _register_styles(self):
        c, s, f = self.c, self.style, self.fonts

        s.configure(".", background=c["bg"], foreground=c["text"],
                    fieldbackground=c["input"], borderwidth=0, focuscolor=c["accent"])
        s.configure("TFrame", background=c["bg"])
        s.configure("Surface.TFrame", background=c["surface"])
        s.configure("Input.TFrame", background=c["input"])

        s.configure("TLabel", background=c["bg"], foreground=c["text"], font=f["body"])
        s.configure("Title.TLabel", font=f["title"], foreground=c["text"])
        s.configure("H2.TLabel", font=f["h2"], foreground=c["text"])
        s.configure("Dim.TLabel", font=f["small"], foreground=c["text_dim"])
        s.configure("Faint.TLabel", font=f["tiny"], foreground=c["text_faint"])
        s.configure("Surface.TLabel", background=c["surface"], foreground=c["text"], font=f["body"])
        s.configure("SurfaceDim.TLabel", background=c["surface"], foreground=c["text_dim"], font=f["small"])
        s.configure("SurfaceFaint.TLabel", background=c["surface"], foreground=c["text_faint"], font=f["tiny"])

        s.configure("Vertical.TScrollbar", background=c["track"], troughcolor=c["bg"],
                    bordercolor=c["bg"], arrowcolor=c["bg"], darkcolor=c["track"],
                    lightcolor=c["track"], borderwidth=0, arrowsize=0, width=8)
        s.map("Vertical.TScrollbar", background=[("active", c["text_faint"])])
        s.layout("Vertical.TScrollbar",
                 [("Vertical.Scrollbar.trough",
                   {"sticky": "ns", "children": [("Vertical.Scrollbar.thumb",
                                                  {"expand": "1", "sticky": "nswe"})]})])

        s.configure("TSeparator", background=c["border"])


def round_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Rectángulo redondeado en un Canvas (Tk no trae uno)."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **kwargs)
