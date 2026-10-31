"""Preparativos comunes: Qt sin ventanas, diálogos que no bloquean y datos temporales."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if Path("C:/Windows/Fonts").is_dir():
    # sin esto, offscreen dibuja cuadraditos y las medidas de los textos mienten
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

import pytest  # noqa: E402
from PySide6.QtCore import QStandardPaths  # noqa: E402
from PySide6.QtGui import QDesktopServices  # noqa: E402
from PySide6.QtWidgets import QFileDialog, QMessageBox  # noqa: E402

from refraccion import db  # noqa: E402
from refraccion.app import create_app  # noqa: E402

# las pruebas nunca escriben en la carpeta de datos real del usuario
QStandardPaths.setTestModeEnabled(True)


@pytest.fixture(scope="session")
def qapp():
    """La misma QApplication que la app real (estilo, nombres, coma decimal)."""
    return create_app([])


class Dialogos:
    """Sustituye los diálogos modales: responde lo que diga la prueba y los apunta."""

    def __init__(self) -> None:
        self.vistos: list[tuple[str, str]] = []         # (tipo, título)
        self.respuesta = QMessageBox.StandardButton.Yes
        self.guardar_en = ""                            # lo que «elige» el usuario al guardar
        self.propuesto = ""                             # la ruta que propuso la app
        self.urls: list[str] = []

    def tipos(self) -> list[str]:
        return [tipo for tipo, _ in self.vistos]


@pytest.fixture(autouse=True)
def dialogos(monkeypatch):
    d = Dialogos()

    def apunta(tipo, respuesta):
        def falso(*args, **kwargs):
            d.vistos.append((tipo, args[1] if len(args) > 1 else ""))
            return respuesta() if callable(respuesta) else respuesta
        return staticmethod(falso)

    monkeypatch.setattr(QMessageBox, "question", apunta("question", lambda: d.respuesta))
    for tipo in ("information", "warning", "critical", "about"):
        monkeypatch.setattr(QMessageBox, tipo, apunta(tipo, None))

    def guardar(*args, **kwargs):
        d.vistos.append(("guardar", args[1] if len(args) > 1 else ""))
        d.propuesto = args[2] if len(args) > 2 else ""
        return d.guardar_en, ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(guardar))
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        staticmethod(lambda url: d.urls.append(url.toLocalFile()) or True))
    return d


@pytest.fixture
def conn(tmp_path):
    conexion = db.connect(tmp_path / "datos con ñ.sqlite3")
    yield conexion
    conexion.close()


@pytest.fixture
def abrir_ventana(qtbot, conn):
    """Abre una ventana (o varias, para probar que se recuerda el estado) sobre la base."""
    from refraccion.ui.main_window import MainWindow

    abiertas = []

    def abrir(conexion=None, ancho=1260, alto=800):
        win = MainWindow(conexion or conn)
        qtbot.addWidget(win)
        win.resize(ancho, alto)
        win.show()
        qtbot.waitExposed(win)
        abiertas.append(win)
        return win

    yield abrir
    for win in abiertas:
        win.close()
        win.guardar_estado = lambda: None          # qtbot la vuelve a cerrar con la base ya cerrada


@pytest.fixture
def ventana(abrir_ventana):
    return abrir_ventana()
