"""Log rotativo en la carpeta de datos, para poder pedir el log al cliente si algo falla."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMATO = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(carpeta: Path, nivel: int = logging.INFO) -> Path:
    archivo = carpeta / "app.log"
    raiz = logging.getLogger()
    raiz.setLevel(nivel)

    manejador = RotatingFileHandler(archivo, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    manejador.setFormatter(logging.Formatter(FORMATO))
    raiz.addHandler(manejador)

    # En el ejecutable sin consola (--windowed) sys.stderr es None.
    if sys.stderr is not None and not getattr(sys, "frozen", False):
        consola = logging.StreamHandler()
        consola.setFormatter(logging.Formatter(FORMATO))
        raiz.addHandler(consola)

    return archivo
