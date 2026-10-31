"""Arranque de la aplicación: Qt, carpeta de datos, logs, errores y ventana principal."""
from __future__ import annotations

import argparse
import contextlib
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QApplication, QMessageBox

from . import APP_NAME, ORG_NAME, __version__, db, exportar, paths
from .logging_setup import setup_logging
from .ui import informe
from .ui.main_window import MainWindow

log = logging.getLogger(__name__)


def _install_excepthook() -> None:
    """Registra los errores no controlados en el log y los muestra al usuario."""

    def hook(exc_type, exc, tb):
        log.critical("Error no controlado", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            QMessageBox.critical(
                None,
                APP_NAME,
                f"Ha ocurrido un error inesperado:\n\n{exc}\n\n"
                f"Los detalles están en el registro:\n{paths.log_dir() / 'app.log'}",
            )

    sys.excepthook = hook


def _apply_look(app: QApplication) -> None:
    app.setStyle("Fusion")
    icono = paths.resource("icons/app.png")
    if icono.exists():
        app.setWindowIcon(QIcon(str(icono)))
    estilo = paths.resource("style.qss")
    if estilo.exists():
        # las imágenes del QSS (la marca de las casillas) van con ruta absoluta
        qss = estilo.read_text(encoding="utf-8")
        app.setStyleSheet(qss.replace("{RECURSOS}", paths.resource("").as_posix().rstrip("/")))


def _traducir_qt(app: QApplication) -> None:
    """Los botones y diálogos propios de Qt en español: «Sí», «No», «Cancelar»."""
    if app.findChild(QTranslator, "qtbase_es") is not None:
        return
    traductor = QTranslator()
    carpeta = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if traductor.load(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain), "qtbase", "_", carpeta):
        traductor.setObjectName("qtbase_es")
        traductor.setParent(app)                    # solo se queda si ha cargado
        app.installTranslator(traductor)
    else:
        log.warning("No se encontró la traducción de Qt al español en %s", carpeta)


def create_app(argv: list[str] | None = None) -> QApplication:
    QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))
    QCoreApplication.setOrganizationName(ORG_NAME)
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(__version__)
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    _traducir_qt(app)
    _apply_look(app)
    return app


def comprobaciones(ventana: MainWindow) -> list[str]:
    """Lo que un ejecutable aligerado podría haber perdido. Devuelve lo que falla."""
    fallos = []
    if QImage(str(paths.resource("icons/marca.svg"))).isNull():
        fallos.append("No se leen imágenes SVG: falta el plugin qsvg.")
    if QCoreApplication.translate("QPlatformTheme", "&Yes") != "&Sí":
        fallos.append("Falta la traducción de Qt al español (qtbase_es.qm).")
    try:
        contenido = informe.pdf(ventana.solucion, "Aire", "Agua", ventana.diagrama.imagen(1.0),
                                informe.imagen_de_curva(ventana.solucion, escala=1.0))
        if not contenido.startswith(b"%PDF-"):
            fallos.append("El PDF sale vacío.")
        exportar.historial_csv([])
    except Exception as error:  # noqa: BLE001 - se informa de cualquier fallo, sea cual sea
        fallos.append(f"Falla la exportación: {error!r}")
    return fallos


def comprobar(destino: Path) -> int:
    """Abre la ventana sin tocar los datos del usuario, la guarda en una imagen, revisa lo
    que necesita el ejecutable (SVG, traducción, PDF y CSV) y sale.

    Para probar un ejecutable: Refraccion.exe --comprobar ruta.png. Devuelve 0 si todo va
    bien; si no, 1, y deja los motivos en ruta.txt (si se puede escribir ahí).
    """
    create_app([sys.argv[0]])
    conn = db.connect(":memory:")
    try:
        ventana = MainWindow(conn)
        ventana.resize(1260, 800)
        ventana.show()
        QApplication.processEvents()
        fallos = [] if ventana.grab().save(str(destino)) else [f"No se pudo guardar {destino}."]
        fallos += comprobaciones(ventana)
        ventana.guardar_estado = lambda: None
        ventana.close()
    finally:
        conn.close()
    if not fallos:
        return 0
    with contextlib.suppress(OSError):          # sin carpeta donde escribir, basta el código
        destino.with_suffix(".txt").write_text("\n".join(fallos), encoding="utf-8")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("--comprobar", metavar="IMAGEN.png", type=Path,
                        help="abrir la ventana, guardarla en una imagen y salir")
    args, _resto = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    if args.comprobar is not None:
        return comprobar(args.comprobar)

    app = create_app()
    setup_logging(paths.log_dir())
    _install_excepthook()
    log.info("%s %s iniciado", APP_NAME, __version__)

    conn = db.connect(paths.db_path())
    try:
        ventana = MainWindow(conn)
        ventana.show()
        return app.exec()
    finally:
        conn.close()
        log.info("%s cerrado", APP_NAME)
