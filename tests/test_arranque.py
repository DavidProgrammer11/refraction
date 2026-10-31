"""Arranque: el modo --comprobar, los errores no controlados y los puntos de entrada reales."""
import logging
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QImage

from refraccion import APP_NAME, app, paths

RAIZ = Path(__file__).resolve().parents[1]


def test_comprobar_guarda_la_ventana_en_una_imagen(qapp, tmp_path):
    destino = tmp_path / "captura con ñ.png"
    assert app.main(["--comprobar", str(destino)]) == 0
    imagen = QImage(str(destino))
    assert (imagen.width(), imagen.height()) == (1260, 800)


def test_comprobar_no_crea_la_base_de_datos_del_usuario(qapp, tmp_path):
    app.main(["--comprobar", str(tmp_path / "captura.png")])
    assert not paths.db_path().exists()


def test_comprobar_falla_si_no_puede_guardar(qapp, tmp_path):
    assert app.main(["--comprobar", str(tmp_path / "no existe" / "captura.png")]) == 1


def test_el_estilo_lleva_la_ruta_real_de_las_imagenes(qapp):
    estilo = qapp.styleSheet()
    assert "{RECURSOS}" not in estilo
    assert paths.resource("icons/marca.svg").exists()
    assert paths.resource("icons/marca.svg").as_posix() in estilo


def test_un_error_no_controlado_se_registra_y_se_muestra(qapp, monkeypatch, dialogos, caplog):
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)       # se restaura al acabar
    app._install_excepthook()
    with caplog.at_level(logging.CRITICAL):
        try:
            raise ZeroDivisionError("división entre cero de prueba")
        except ZeroDivisionError:
            sys.excepthook(*sys.exc_info())
    assert "Error no controlado" in caplog.text
    assert dialogos.vistos == [("critical", APP_NAME)]


def _ejecutar(argumentos, tmp_path):
    entorno = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, *argumentos], cwd=RAIZ, env=entorno,
                          capture_output=True, text=True, timeout=120)


def test_python_m_refraccion_arranca(tmp_path):
    destino = tmp_path / "modulo.png"
    resultado = _ejecutar(["-m", "refraccion", "--comprobar", str(destino)], tmp_path)
    assert resultado.returncode == 0, resultado.stderr
    assert destino.exists()


def test_run_py_arranca_como_el_ejecutable(tmp_path):
    destino = tmp_path / "run.png"
    resultado = _ejecutar(["run.py", "--comprobar", str(destino)], tmp_path)
    assert resultado.returncode == 0, resultado.stderr
    assert destino.exists()


def test_arranque_normal_con_registro_y_base_de_datos(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from refraccion import db

    monkeypatch.setattr(paths, "log_dir", lambda: tmp_path)
    monkeypatch.setattr(paths, "db_path", lambda: tmp_path / "datos.sqlite3")
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)          # sin bucle de eventos
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    raiz = logging.getLogger()
    antes = list(raiz.handlers)
    try:
        assert app.main([]) == 0
    finally:
        for manejador in raiz.handlers[len(antes):]:
            manejador.close()
            raiz.removeHandler(manejador)
    registro = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert f"{APP_NAME} " in registro and "iniciado" in registro and "cerrado" in registro
    conexion = db.connect(tmp_path / "datos.sqlite3")
    assert db.schema_version(conexion) == len(db.MIGRATIONS)
    conexion.close()


def test_los_botones_estandar_de_qt_salen_en_espanol(qapp):
    # regresión: sin la traducción de Qt, «¿Vaciar el historial?» se contestaba con «Yes» / «No»
    from PySide6.QtCore import QCoreApplication

    assert QCoreApplication.translate("QPlatformTheme", "&Yes") == "&Sí"
    assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Cancelar"


def test_crear_la_app_dos_veces_no_duplica_la_traduccion(qapp):
    from PySide6.QtCore import QTranslator

    app.create_app([])
    assert len(qapp.findChildren(QTranslator, "qtbase_es")) == 1


def test_la_comprobacion_dice_que_falla_y_lo_deja_escrito(qapp, tmp_path, monkeypatch):
    # un ejecutable al que le falta el plugin SVG y que no sabe hacer el PDF
    from refraccion.ui import informe

    real = paths.resource
    monkeypatch.setattr(paths, "resource",
                        lambda relativa: tmp_path / "no está.svg" if relativa.endswith(".svg") else real(relativa))

    def sin_pdf(*args, **kwargs):
        raise RuntimeError("sin QPdfWriter")

    monkeypatch.setattr(informe, "pdf", sin_pdf)
    destino = tmp_path / "captura.png"
    assert app.main(["--comprobar", str(destino)]) == 1
    motivos = destino.with_suffix(".txt").read_text(encoding="utf-8")
    assert "SVG" in motivos and "sin QPdfWriter" in motivos
    assert destino.exists()                                  # la captura sí se pudo guardar


def test_la_comprobacion_avisa_si_el_pdf_sale_vacio(qapp, tmp_path, monkeypatch):
    from refraccion.ui import informe

    monkeypatch.setattr(informe, "pdf", lambda *args, **kwargs: b"")
    destino = tmp_path / "captura.png"
    assert app.main(["--comprobar", str(destino)]) == 1
    assert "vacío" in destino.with_suffix(".txt").read_text(encoding="utf-8")


def test_sin_la_traduccion_de_qt_se_avisa_y_la_comprobacion_lo_detecta(qapp, tmp_path, monkeypatch, caplog):
    from PySide6.QtCore import QLibraryInfo, QTranslator

    actual = qapp.findChild(QTranslator, "qtbase_es")
    qapp.removeTranslator(actual)
    actual.setParent(None)
    try:
        monkeypatch.setattr(QLibraryInfo, "path", staticmethod(lambda _cual: str(tmp_path)))
        with caplog.at_level(logging.WARNING):
            app._traducir_qt(qapp)
        assert "No se encontró la traducción" in caplog.text
        assert qapp.findChild(QTranslator, "qtbase_es") is None      # no queda uno a medias
        destino = tmp_path / "captura.png"
        assert app.main(["--comprobar", str(destino)]) == 1
        assert "qtbase_es.qm" in destino.with_suffix(".txt").read_text(encoding="utf-8")
    finally:
        monkeypatch.undo()
        app._traducir_qt(qapp)                                   # deja la app como estaba
    assert qapp.findChild(QTranslator, "qtbase_es") is not None
