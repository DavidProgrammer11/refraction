"""Rutas de la app: recursos incluidos en el paquete y carpeta de datos del usuario."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths

# Relativo al módulo, no al directorio actual: funciona igual en desarrollo y en el
# ejecutable de PyInstaller (que copia resources/ junto al paquete).
_PAQUETE = Path(__file__).resolve().parent


def resource(relativa: str) -> Path:
    """Ruta a un archivo de src/refraccion/resources/."""
    return _PAQUETE / "resources" / relativa


def data_dir() -> Path:
    """Carpeta de datos del usuario (en Windows, %APPDATA%\\DZM\\<App>).

    Requiere haber fijado antes el nombre de la organización y de la app
    (QCoreApplication.setOrganizationName / setApplicationName), como hace app.main().
    """
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    ruta = Path(base)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def log_dir() -> Path:
    ruta = data_dir() / "logs"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def db_path() -> Path:
    return data_dir() / "datos.sqlite3"
