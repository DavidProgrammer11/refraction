"""La ventana con pytest-qt y Qt sin pantalla: se escribe, se pulsa y se arrastra
como lo haría el usuario, y se mira lo que queda en pantalla."""
import math
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QFontMetrics, QGuiApplication, QImage
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QLineEdit, QMessageBox, QWidget

from refraccion import ORG_NAME, __version__, db, ejemplos, paths
from refraccion.optica import Incognita
from refraccion.ui.diagrama import Diagrama


def theta2_esperado(n1, n2, theta1):
    """Cálculo de referencia, independiente del de la app."""
    return math.degrees(math.asin(n1 * math.sin(math.radians(theta1)) / n2))


def es(numero: float, decimales: int = 2) -> str:
    return f"{numero:.{decimales}f}".replace(".", ",")


def escribir(qtbot, campo, texto):
    editor = campo.spin.lineEdit()
    editor.selectAll()
    qtbot.keyClicks(editor, texto)


def punto(diagrama, medio, grados, fraccion=0.9) -> QPoint:
    """Píxel del diagrama en la dirección de un rayo: medio 1 arriba a la izquierda, 2 abajo a la derecha."""
    o, largo = Diagrama.geometria(QRectF(diagrama.rect()))
    a = math.radians(grados)
    if medio == 1:
        x, y = o.x() - largo * fraccion * math.sin(a), o.y() - largo * fraccion * math.cos(a)
    else:
        x, y = o.x() + largo * fraccion * math.sin(a), o.y() + largo * fraccion * math.cos(a)
    return QPoint(round(x), round(y))


def ejemplo(titulo):
    return next(e for e in ejemplos.EJEMPLOS if e.titulo == titulo)


# --- arranque ----------------------------------------------------------------------------------

def test_arranca_calculando_theta2_del_aire_al_agua(ventana):
    esperado = es(theta2_esperado(1.0003, 1.333, 40))            # 28,84
    assert ventana.titular.text() == f"θ₂ = {esperado}°"
    assert ventana.detalle.text() == "El rayo se acerca a la normal"
    assert ventana.campos[Incognita.THETA2].es_incognita
    assert ventana.campos[Incognita.THETA2].resultado.text() == f"{esperado}°"
    assert [ventana.combos[m].currentData() for m in (1, 2)] == ["Aire", "Agua"]
    assert ventana.botones_incognita[Incognita.THETA2].isChecked()
    assert ventana.diagrama.solucion is ventana.solucion


def test_paso_a_paso_con_los_numeros_de_pantalla(ventana):
    texto = ventana.pasos.toPlainText()
    # la sustitución va como fracción: numerador y denominador en líneas distintas
    assert "1,0003 · sen 40,00°" in texto and "1,333" in texto
    # 1,0003 · 0,64279 / 1,333 = 0,48236
    assert "θ₂ = arcsen 0,4824 = 28,84°" in texto


# --- escribir datos --------------------------------------------------------------------------------

@pytest.mark.parametrize("tecleado", ["30,5", "30.5"])
def test_escribir_un_angulo_recalcula_al_momento(qtbot, ventana, tecleado):
    escribir(qtbot, ventana.campos[Incognita.THETA1], tecleado)
    assert ventana.campos[Incognita.THETA1].valor() == 30.5
    assert ventana.titular.text() == f"θ₂ = {es(theta2_esperado(1.0003, 1.333, 30.5))}°"   # 22,39


def test_un_indice_con_punto_decimal_vale_como_con_coma(qtbot, ventana):
    # regresión: con la configuración española «1.5» se quedaba en 1
    escribir(qtbot, ventana.campos[Incognita.N2], "1.5")
    assert ventana.campos[Incognita.N2].valor() == 1.5


def test_elegir_un_material_pone_su_indice(ventana):
    combo = ventana.combos[1]
    indice = combo.findData("Diamante")
    combo.setCurrentIndex(indice)
    combo.activated.emit(indice)
    assert ventana.campos[Incognita.N1].valor() == 2.417
    # 2,417 · sen 40° / 1,333 = 1,166 > 1: del diamante al agua ya no sale a 40°
    assert ventana.titular.text() == "Reflexión total"
    assert ventana.titular.property("estado") == "aviso"
    assert ventana.campos[Incognita.THETA2].resultado.text() == "—"


def test_elegir_personalizado_no_cambia_el_indice(ventana):
    combo = ventana.combos[2]
    indice = combo.findData("Personalizado")
    combo.activated.emit(indice)
    assert ventana.campos[Incognita.N2].valor() == 1.333


def test_un_indice_que_no_es_de_la_lista_es_personalizado(ventana):
    ventana.campos[Incognita.N2].poner(1.4)
    assert ventana.combos[2].currentData() == "Personalizado"
    ventana.campos[Incognita.N2].poner(1.333)
    assert ventana.combos[2].currentData() == "Agua"


# --- la incógnita ------------------------------------------------------------------------------------

def test_cambiar_la_incognita_conserva_el_resultado_como_dato(qtbot, ventana):
    # θ₁ = 30° → θ₂ = 22,04°, mientras la casilla oculta de θ₂ sigue con el 28,84 de antes
    ventana.campos[Incognita.THETA1].poner(30)
    calculado = round(theta2_esperado(1.0003, 1.333, 30), 2)
    qtbot.mouseClick(ventana.botones_incognita[Incognita.N2], Qt.MouseButton.LeftButton)
    assert ventana.incognita is Incognita.N2
    theta2 = ventana.campos[Incognita.THETA2]
    assert not theta2.es_incognita and theta2.valor() == calculado   # el resultado, ya como dato
    assert ventana.campos[Incognita.N2].es_incognita
    assert ventana.solucion.valor == pytest.approx(1.333, abs=5e-4)  # vuelve a salir el agua
    assert not ventana.combos[2].isEnabled() and ventana.combos[2].currentIndex() == -1
    assert ventana.combos[1].isEnabled()
    assert ventana.nombre_medio(2) == "(se calcula)"
    assert ventana.descripcion.text() == "n₂: el índice del medio de abajo"


def test_volver_a_un_dato_recupera_su_material(qtbot, ventana):
    qtbot.mouseClick(ventana.botones_incognita[Incognita.N2], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(ventana.botones_incognita[Incognita.THETA2], Qt.MouseButton.LeftButton)
    assert ventana.combos[2].isEnabled() and ventana.combos[2].currentData() == "Agua"


def test_sin_solucion_el_resultado_no_se_copia_al_cambiar_de_incognita(qtbot, ventana):
    ventana.aplicar_ejemplo(ejemplo("Reflexión total en el agua"))
    anterior = ventana.campos[Incognita.THETA2].valor()
    qtbot.mouseClick(ventana.botones_incognita[Incognita.N1], Qt.MouseButton.LeftButton)
    assert ventana.campos[Incognita.THETA2].valor() == anterior


# --- arrastrar los rayos --------------------------------------------------------------------------------

def test_arrastrar_el_rayo_incidente_cambia_theta1(qtbot, ventana):
    diagrama = ventana.diagrama
    qtbot.mousePress(diagrama, Qt.MouseButton.LeftButton, pos=punto(diagrama, 1, 60))
    assert ventana.campos[Incognita.THETA1].valor() == pytest.approx(60, abs=0.6)
    qtbot.mouseMove(diagrama, pos=punto(diagrama, 1, 25))
    qtbot.mouseRelease(diagrama, Qt.MouseButton.LeftButton, pos=punto(diagrama, 1, 25))
    theta1 = ventana.campos[Incognita.THETA1].valor()
    assert theta1 == pytest.approx(25, abs=0.6)
    assert ventana.solucion.valor == pytest.approx(theta2_esperado(1.0003, 1.333, theta1), abs=1e-9)


def test_al_bajar_del_horizonte_el_rayo_queda_rasante(qtbot, ventana):
    diagrama = ventana.diagrama
    qtbot.mousePress(diagrama, Qt.MouseButton.LeftButton, pos=punto(diagrama, 1, 45))
    qtbot.mouseMove(diagrama, pos=punto(diagrama, 2, 45))         # sigue arrastrando el incidente
    assert ventana.campos[Incognita.THETA1].valor() == 90
    qtbot.mouseRelease(diagrama, Qt.MouseButton.LeftButton)


def test_la_incognita_no_se_puede_arrastrar(qtbot, ventana):
    with qtbot.assertNotEmitted(ventana.diagrama.anguloArrastrado):
        qtbot.mousePress(ventana.diagrama, Qt.MouseButton.LeftButton, pos=punto(ventana.diagrama, 2, 60))
    assert ventana.campos[Incognita.THETA2].resultado.text() == "28,84°"


def test_si_se_calcula_theta1_se_arrastra_el_refractado(qtbot, ventana):
    qtbot.mouseClick(ventana.botones_incognita[Incognita.THETA1], Qt.MouseButton.LeftButton)
    assert "refractado" in ventana.pista.text()
    diagrama = ventana.diagrama
    qtbot.mousePress(diagrama, Qt.MouseButton.LeftButton, pos=punto(diagrama, 2, 30))
    qtbot.mouseRelease(diagrama, Qt.MouseButton.LeftButton)
    theta2 = ventana.campos[Incognita.THETA2].valor()
    assert theta2 == pytest.approx(30, abs=0.6)
    # θ₁ = arcsen (1,333 · sen θ₂ / 1,0003)
    assert ventana.solucion.valor == pytest.approx(theta2_esperado(1.333, 1.0003, theta2), abs=1e-9)


def test_el_boton_derecho_no_arrastra(qtbot, ventana):
    with qtbot.assertNotEmitted(ventana.diagrama.anguloArrastrado):
        qtbot.mousePress(ventana.diagrama, Qt.MouseButton.RightButton, pos=punto(ventana.diagrama, 1, 60))


# --- ejemplos e intercambio -------------------------------------------------------------------------

def test_ejemplo_de_reflexion_total(ventana):
    ej = ejemplo("Reflexión total en el agua")
    ventana.pestanas.setCurrentIndex(2)
    ventana.aplicar_ejemplo(ej)
    assert ventana.titular.text() == "Reflexión total"
    assert ej.titulo in ventana.pista.text()
    assert ventana.pestanas.currentWidget() is ventana.pasos
    assert [ventana.combos[m].currentData() for m in (1, 2)] == ["Agua", "Aire"]


def test_al_tocar_un_dato_se_quita_la_explicacion_del_ejemplo(ventana):
    ventana.aplicar_ejemplo(ejemplo("Reflexión total en el agua"))
    ventana.campos[Incognita.THETA1].poner(30)
    assert ventana.pista.text().startswith("Arrastra")
    assert ventana.titular.text() == f"θ₂ = {es(theta2_esperado(1.333, 1.0003, 30))}°"


@pytest.mark.parametrize("ej", ejemplos.EJEMPLOS, ids=lambda e: e.titulo)
def test_todos_los_ejemplos_del_menu_se_aplican(ventana, ej):
    ventana.aplicar_ejemplo(ej)
    assert ventana.incognita is ej.incognita
    for campo in Incognita:
        if campo is not ej.incognita:
            assert ventana.campos[campo].valor() == pytest.approx(ej.datos.valor(campo))


def test_intercambiar_los_medios(ventana):
    ventana.intercambiar_medios()
    assert (ventana.campos[Incognita.N1].valor(), ventana.campos[Incognita.N2].valor()) == (1.333, 1.0003)
    assert [ventana.combos[m].currentData() for m in (1, 2)] == ["Agua", "Aire"]
    assert ventana.titular.text() == f"θ₂ = {es(theta2_esperado(1.333, 1.0003, 40))}°"


def test_intercambiar_los_medios_cuando_se_calcula_un_indice(qtbot, ventana):
    qtbot.mouseClick(ventana.botones_incognita[Incognita.N1], Qt.MouseButton.LeftButton)
    n1 = ventana.solucion.valor                                   # ≈ 1,0003
    ventana.intercambiar_medios()
    assert ventana.incognita is Incognita.N2                      # la incógnita viaja con su medio
    assert ventana.campos[Incognita.N1].valor() == 1.333
    assert ventana.solucion.valor == pytest.approx(
        1.333 * math.sin(math.radians(40)) / math.sin(math.radians(28.84)), rel=1e-9)
    assert n1 == pytest.approx(1.0003, abs=3e-4)


# --- historial ---------------------------------------------------------------------------------------

def test_guardar_en_el_historial_y_volver_a_un_calculo(qtbot, ventana, conn):
    qtbot.mouseClick(ventana.boton_guardar, Qt.MouseButton.LeftButton)
    ventana.aplicar_ejemplo(ejemplo("Por qué brilla un diamante"))
    ventana.guardar_en_historial()
    tabla = ventana.historial.tabla
    assert tabla.rowCount() == 2
    assert [tabla.item(0, c).text() for c in (1, 2, 7, 8)] == ["θ₂", "Diamante", "—", "Reflexión total"]
    assert [tabla.item(1, c).text() for c in (2, 3, 4, 7, 8)] == [
        "Aire", "1,0003", "40,00°", "28,84°", "θ₂ = 28,84°"]

    tabla.selectRow(1)
    qtbot.mouseClick(ventana.historial.boton_cargar, Qt.MouseButton.LeftButton)
    assert ventana.campos[Incognita.N1].valor() == 1.0003
    assert ventana.titular.text() == "θ₂ = 28,84°"
    assert len(db.listar_calculos(conn)) == 2


def test_doble_clic_en_el_historial_carga_el_calculo(qtbot, ventana):
    ventana.aplicar_ejemplo(ejemplo("Medir el índice de un vidrio"))
    ventana.guardar_en_historial()
    ventana.aplicar_ejemplo(ejemplo("Del aire al agua"))
    ventana.historial.tabla.itemDoubleClicked.emit(ventana.historial.tabla.item(0, 0))
    assert ventana.incognita is Incognita.N2
    assert ventana.campos[Incognita.THETA2].valor() == 27.79


def test_borrar_y_vaciar_el_historial(qtbot, ventana, dialogos):
    for _ in range(3):
        ventana.guardar_en_historial()
    historial = ventana.historial
    ventana.pestanas.setCurrentWidget(historial)
    assert not historial.boton_borrar.isEnabled()               # sin selección no hay qué borrar
    historial.tabla.selectRow(0)
    qtbot.mouseClick(historial.boton_borrar, Qt.MouseButton.LeftButton)
    assert historial.tabla.rowCount() == 2

    dialogos.respuesta = QMessageBox.StandardButton.No
    qtbot.mouseClick(historial.boton_vaciar, Qt.MouseButton.LeftButton)
    assert historial.tabla.rowCount() == 2 and dialogos.tipos() == ["question"]
    dialogos.respuesta = QMessageBox.StandardButton.Yes
    qtbot.mouseClick(historial.boton_vaciar, Qt.MouseButton.LeftButton)
    assert historial.tabla.rowCount() == 0
    assert historial.vacio.isVisible() and not historial.boton_exportar.isEnabled()


def test_un_calculo_que_ya_no_existe_no_hace_nada(ventana):
    ventana.cargar_calculo(12345)
    assert ventana.titular.text() == "θ₂ = 28,84°"


# --- exportar ------------------------------------------------------------------------------------------

def test_exportar_el_historial_a_una_carpeta_con_espacios_y_tildes(tmp_path, ventana, dialogos, conn):
    ventana.guardar_en_historial()
    carpeta = tmp_path / "Mis cálculos de óptica"
    carpeta.mkdir()
    dialogos.guardar_en = str(carpeta / "historial")             # sin extensión: la pone la app
    ventana.exportar_historial()
    archivo = carpeta / "historial.csv"
    contenido = archivo.read_bytes()
    assert contenido.startswith(b"\xef\xbb\xbf")
    assert "θ₂ = 28,84°".encode() in contenido
    assert dialogos.propuesto.endswith("Historial de refracción.csv")
    assert db.leer_ajuste(conn, "carpeta_exportar") == str(carpeta)
    # la próxima vez propone la misma carpeta
    ventana.exportar_historial()
    assert dialogos.propuesto.startswith(str(carpeta))


def test_exportar_sin_historial_no_pregunta_nada(ventana, dialogos):
    ventana.exportar_historial()
    assert dialogos.vistos == []
    assert "vacío" in ventana.statusBar().currentMessage()


def test_cancelar_la_exportacion_no_escribe_nada(tmp_path, ventana, dialogos):
    ventana.guardar_en_historial()
    dialogos.guardar_en = ""
    ventana.exportar_historial()
    assert dialogos.tipos() == ["guardar"] and list(tmp_path.glob("*.csv")) == []


def test_si_no_se_puede_escribir_el_csv_avisa(tmp_path, ventana, dialogos):
    ventana.guardar_en_historial()
    dialogos.guardar_en = str(tmp_path / "no existe" / "historial.csv")
    ventana.exportar_historial()
    assert dialogos.tipos() == ["guardar", "warning"]


def test_guardar_el_diagrama_como_png_al_doble_de_resolucion(tmp_path, ventana, dialogos):
    dialogos.guardar_en = str(tmp_path / "diagrama con ñ.jpg")
    ventana.guardar_imagen()
    archivo = tmp_path / "diagrama con ñ.png"
    imagen = QImage(str(archivo))
    assert not imagen.isNull()
    assert (imagen.width(), imagen.height()) == (2 * ventana.diagrama.width(), 2 * ventana.diagrama.height())


def test_guardar_el_diagrama_en_una_carpeta_que_no_existe_avisa(tmp_path, ventana, dialogos):
    dialogos.guardar_en = str(tmp_path / "no existe" / "diagrama.png")
    ventana.guardar_imagen()
    assert dialogos.tipos() == ["guardar", "warning"]


def test_cancelar_guardar_el_diagrama(ventana, dialogos):
    ventana.guardar_imagen()
    assert dialogos.tipos() == ["guardar"]


def test_copiar_el_diagrama_al_portapapeles(ventana):
    QGuiApplication.clipboard().clear()
    ventana.copiar_imagen()
    imagen = QGuiApplication.clipboard().image()
    assert imagen.width() == 2 * ventana.diagrama.width()


# --- estado entre sesiones ----------------------------------------------------------------------------

def test_se_recuerda_como_se_dejo_la_ventana(qtbot, abrir_ventana, conn):
    primera = abrir_ventana()
    qtbot.mouseClick(primera.botones_incognita[Incognita.THETA1], Qt.MouseButton.LeftButton)
    primera.campos[Incognita.THETA2].poner(20)
    combo = primera.combos[1]
    combo.activated.emit(combo.findData("Diamante"))
    primera.ver_animacion.setChecked(False)
    primera.pestanas.setCurrentIndex(2)
    theta1 = primera.solucion.valor
    primera.close()

    segunda = abrir_ventana(conn)
    assert segunda.incognita is Incognita.THETA1
    assert segunda.campos[Incognita.THETA2].valor() == 20
    assert segunda.combos[1].currentData() == "Diamante"
    assert not segunda.ver_animacion.isChecked() and segunda.ver_frentes.isChecked()
    assert segunda.pestanas.currentIndex() == 2
    assert segunda.solucion.valor == pytest.approx(theta1)


@pytest.mark.parametrize("estado", [
    "basura",
    {"incognita": "n9", "n1": "mucho", "theta1": True, "pestana": 99, "divisor": [1, "a"]},
])
def test_un_estado_guardado_corrupto_no_impide_arrancar(abrir_ventana, conn, estado):
    db.guardar_ajuste(conn, "estado", estado)
    db.guardar_ajuste(conn, "geometria", "esto no es base64")
    win = abrir_ventana(conn)
    assert win.incognita is Incognita.THETA2
    assert win.campos[Incognita.N1].valor() == 1.0003
    assert win.campos[Incognita.THETA1].valor() == 40
    assert win.pestanas.currentIndex() == 0
    assert win.titular.text() == "θ₂ = 28,84°"


def test_si_la_base_falla_al_cerrar_no_se_pierde_el_cierre(abrir_ventana, tmp_path):
    conexion = db.connect(tmp_path / "otra.sqlite3")
    win = abrir_ventana(conexion)
    conexion.close()                                            # guardar el estado fallará
    assert win.close()


# --- vista, menús y medidas ------------------------------------------------------------------------------

def test_la_animacion_solo_corre_con_frentes_de_onda(qtbot, ventana):
    diagrama = ventana.diagrama
    assert diagrama.animando
    fase = diagrama.fase
    qtbot.waitUntil(lambda: diagrama.fase != fase, timeout=2000)
    ventana.ver_frentes.setChecked(False)
    assert not diagrama.animando and not ventana.ver_animacion.isEnabled()
    assert not ventana.accion_frentes.isChecked()              # el menú Ver va a la par
    ventana.accion_frentes.setChecked(True)
    assert ventana.ver_frentes.isChecked() and diagrama.animando
    ventana.ver_animacion.setChecked(False)
    assert not diagrama.animando and not ventana.accion_animar.isChecked()


def test_la_animacion_se_para_si_la_ventana_no_se_ve(ventana):
    ventana.hide()
    assert not ventana.diagrama.animando
    ventana.show()
    assert ventana.diagrama.animando


def test_ayuda_acerca_de_y_carpeta_de_datos(ventana, dialogos):
    ventana.mostrar_ayuda()
    ventana.show_about()
    assert dialogos.tipos() == ["information", "about"]
    assert __version__ in ventana.about_text() and ORG_NAME in ventana.about_text()
    ventana.open_data_dir()
    assert [Path(url) for url in dialogos.urls] == [paths.data_dir()]


def test_cabe_en_el_portatil_de_844_px_de_alto(ventana):
    # el portátil deja 844 px de alto útil (escala 125 %); la barra de título se lleva unos 30
    assert ventana.minimumSizeHint().height() <= 800


@pytest.mark.parametrize("tamano", ["normal", "minimo"])
def test_ningun_texto_queda_recortado(qtbot, abrir_ventana, tamano):
    win = abrir_ventana()
    if tamano == "minimo":
        win.resize(win.minimumSizeHint())
    QApplication.processEvents()
    recortados = []
    for hijo in win.findChildren(QWidget):
        if isinstance(hijo, (QLabel, QAbstractButton, QLineEdit)) and hijo.isVisible() and hijo.text():
            if hijo.height() < QFontMetrics(hijo.font()).height():
                recortados.append((type(hijo).__name__, hijo.text()[:30], hijo.height()))
    assert recortados == []


def test_en_ventanas_estrechas_se_esconde_lo_accesorio(ventana):
    ventana.resize(950, 800)
    assert not ventana.formula.isVisible() and ventana.lema.isVisible()
    ventana.resize(820, 800)
    assert not ventana.lema.isVisible()
    ventana.resize(1260, 800)
    assert ventana.formula.isVisible() and ventana.lema.isVisible()


def test_las_graficas_siguen_al_calculo(ventana):
    marca = ventana.curva.contenido.marcas[0]
    assert (marca.x, marca.y) == pytest.approx((40, theta2_esperado(1.0003, 1.333, 40)))
    ventana.aplicar_ejemplo(ejemplo("Reflexión total en el agua"))
    assert ventana.curva.contenido.marcas == []                  # no hay θ₂ que marcar
    assert any("reflexión total" in linea.etiqueta for linea in ventana.curva.contenido.lineas)
    assert [m.x for m in ventana.fresnel.contenido.marcas] == [55.0, 55.0]


def test_un_arrastre_sobre_la_incognita_se_ignora(ventana):
    ventana.diagrama.anguloArrastrado.emit(2, 12.0)               # θ₂ se calcula: no se toca
    assert ventana.campos[Incognita.THETA2].resultado.text() == "28,84°"


def test_intercambiar_los_medios_sin_solucion(ventana):
    ventana.aplicar_ejemplo(ejemplo("Reflexión total en el agua"))
    ventana.intercambiar_medios()
    # del aire al agua a 55° ya hay refracción: 1,0003 · sen 55° / 1,333
    assert ventana.titular.text() == f"θ₂ = {es(theta2_esperado(1.0003, 1.333, 55))}°"


def test_el_panel_de_datos_cabe_en_su_columna(ventana):
    # regresión: la lista de materiales pedía más ancho y se cortaba el borde derecho de las tarjetas
    from PySide6.QtWidgets import QScrollArea

    lienzo = ventana.findChild(QScrollArea, "Lienzo")
    panel = lienzo.widget()
    assert panel.minimumSizeHint().width() <= lienzo.viewport().width()
    assert panel.width() <= lienzo.viewport().width()


def test_la_animacion_se_para_con_la_ventana_minimizada(ventana):
    # Qt sigue dando por «visible» una ventana minimizada: hay que mirarlo aparte
    ventana.setWindowState(Qt.WindowState.WindowMinimized)
    assert ventana.isMinimized()
    assert not ventana.diagrama.animando
    ventana.setWindowState(Qt.WindowState.WindowNoState)
    assert ventana.diagrama.animando


# --- PDF ---------------------------------------------------------------------------------------

def test_exportar_el_calculo_a_pdf(tmp_path, ventana, dialogos, conn):
    carpeta = tmp_path / "Apuntes de física"
    carpeta.mkdir()
    dialogos.guardar_en = str(carpeta / "ejercicio 3")                 # sin extensión: la pone la app
    ventana.exportar_pdf()
    archivo = carpeta / "ejercicio 3.pdf"
    assert archivo.read_bytes().startswith(b"%PDF-")
    assert dialogos.propuesto.endswith("Refracción - θ₂ = 28,84°.pdf")
    assert db.leer_ajuste(conn, "carpeta_exportar") == str(carpeta)
    assert "PDF guardado" in ventana.statusBar().currentMessage()


def test_cancelar_el_pdf_no_escribe_nada(tmp_path, ventana, dialogos):
    ventana.exportar_pdf()
    assert dialogos.tipos() == ["guardar"] and list(tmp_path.glob("*.pdf")) == []


def test_si_no_se_puede_escribir_el_pdf_avisa(tmp_path, ventana, dialogos):
    dialogos.guardar_en = str(tmp_path / "no existe" / "calculo.pdf")
    ventana.exportar_pdf()
    assert dialogos.tipos() == ["guardar", "warning"]


def test_el_enlace_de_la_tarjeta_exporta_el_pdf(qtbot, tmp_path, ventana, dialogos):
    dialogos.guardar_en = str(tmp_path / "desde el enlace.pdf")
    qtbot.mouseClick(ventana.boton_pdf, Qt.MouseButton.LeftButton)
    assert (tmp_path / "desde el enlace.pdf").exists()


def test_al_tamano_por_defecto_los_datos_caben_sin_desplazar(ventana):
    # regresión: el enlace del PDF alargó la tarjeta de resultado y salía la barra de desplazamiento
    from PySide6.QtWidgets import QScrollArea

    lienzo = ventana.findChild(QScrollArea, "Lienzo")
    QApplication.processEvents()
    assert lienzo.widget().minimumSizeHint().height() <= lienzo.viewport().height()
    assert not lienzo.verticalScrollBar().isVisible()
