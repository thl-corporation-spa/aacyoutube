"""Punto de entrada del .app de macOS: siempre abre la ventana."""

import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from aacyoutube.app import run_gui
    sys.exit(run_gui())
