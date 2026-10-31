"""Arranque en desarrollo sin instalar el paquete: python run.py

PyInstaller también usa este archivo como punto de entrada (ver packaging/build.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from refraccion.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
