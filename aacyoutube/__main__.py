"""Punto de entrada: `python3 -m aacyoutube`."""

import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        from aacyoutube.cli import run_cli
        return run_cli(argv)
    from aacyoutube.app import run_gui
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
