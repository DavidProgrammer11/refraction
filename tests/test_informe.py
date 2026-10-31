"""El PDF del cálculo: se genera de verdad y se vuelve a leer con QtPdf."""
import pytest
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize
from PySide6.QtPdf import QPdfDocument

from refraccion.optica import Datos, Incognita, resolver
from refraccion.ui import informe
from refraccion.ui.diagrama import Diagrama

SALTO = chr(10)
BARRA = chr(92)


def leer_pdf(contenido: bytes) -> tuple[QPdfDocument, QBuffer]:
    buffer = QBuffer()
    buffer.setData(QByteArray(contenido))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    doc = QPdfDocument()
    doc.load(buffer)
    return doc, buffer                     # el buffer tiene que seguir vivo mientras se lee


def texto_del_pdf(doc: QPdfDocument) -> str:
    return SALTO.join(doc.getAllText(pagina).text() for pagina in range(doc.pageCount()))


@pytest.fixture
def diagrama(qapp):
    d = Diagrama()
    d.resize(900, 480)
    return d


def generar(diagrama, datos, incognita, medio1="Aire", medio2="Agua"):
    sol = resolver(datos, incognita)
    diagrama.mostrar(sol, medio1, medio2)
    return informe.pdf(sol, medio1, medio2, diagrama.imagen(2.0, QSize(900, 480)),
                       informe.imagen_de_curva(sol, escala=1.0))


def test_el_pdf_es_un_a4_con_el_calculo_y_el_diagrama(diagrama):
    contenido = generar(diagrama, Datos(1.0003, 1.333, 40, 0), Incognita.THETA2)
    assert contenido.startswith(b"%PDF-")
    assert b"/Subtype /Image" in contenido                       # las figuras van dentro
    doc, _buffer = leer_pdf(contenido)
    assert doc.status() == QPdfDocument.Status.Ready
    assert doc.pageCount() == 2
    pagina = doc.pagePointSize(0)
    assert (round(pagina.width()), round(pagina.height())) == (595, 842)   # A4 en puntos
    texto = texto_del_pdf(doc)
    for frase in ("Refracción", "La ley de Snell", "Medio 1: Aire", "Medio 2: Agua",
                  "Sustituimos los datos", "Comprobación", "28,84", "El rayo se acerca a la normal"):
        assert frase in texto, frase


def test_la_primera_pagina_ilustra_y_la_segunda_explica(diagrama):
    # el paso a paso va entero en la página 2: así ninguna fracción se parte entre páginas
    doc, _buffer = leer_pdf(generar(diagrama, Datos(1.0003, 1.333, 40, 0), Incognita.THETA2))
    primera, segunda = doc.getAllText(0).text(), doc.getAllText(1).text()
    assert "La ley de Snell para todas las incidencias" in primera
    assert "Sustituimos" not in primera
    assert "El cálculo, paso a paso" in segunda and "Sustituimos los datos" in segunda


def test_la_curva_es_una_figura_mas_y_sin_ella_el_pdf_tambien_sale(diagrama):
    # una imagen con transparencia se guarda como imagen + máscara: se comparan los dos PDF
    sol = resolver(Datos(1.0, 1.5, 30, 0), Incognita.THETA2)
    diagrama.mostrar(sol, "Vacío", "Vidrio")
    figura = diagrama.imagen(1.0, QSize(900, 480))
    sin_curva = informe.pdf(sol, "Vacío", "Vidrio", figura)
    con_curva = informe.pdf(sol, "Vacío", "Vidrio", figura, informe.imagen_de_curva(sol, escala=1.0))
    assert con_curva.count(b"/Subtype /Image") > sin_curva.count(b"/Subtype /Image") > 0
    assert leer_pdf(sin_curva)[0].pageCount() == 2
    assert "La ley de Snell para todas las incidencias" not in texto_del_pdf(leer_pdf(sin_curva)[0])


def test_el_pdf_de_una_reflexion_total_explica_el_motivo(diagrama):
    contenido = generar(diagrama, Datos(1.5, 1.0, 60, 0), Incognita.THETA2, "Vidrio", "Aire")
    texto = texto_del_pdf(leer_pdf(contenido)[0])
    assert "Reflexión total" in texto and "41,81" in texto


def test_el_titulo_del_pdf_lleva_el_resultado(diagrama):
    contenido = generar(diagrama, Datos(1.0, 1.333, 30, 0), Incognita.THETA2)
    doc, _buffer = leer_pdf(contenido)
    assert "22,03" in doc.metaData(QPdfDocument.MetaDataField.Title)


@pytest.mark.parametrize("datos, incognita, nombre", [
    (Datos(1.0, 1.333, 30, 0), Incognita.THETA2, "Refracción - θ₂ = 22,03°.pdf"),
    (Datos(1.5, 1.0, 60, 0), Incognita.THETA2, "Refracción - Reflexión total.pdf"),
])
def test_nombre_de_archivo_con_el_resultado(datos, incognita, nombre):
    assert informe.nombre_de_archivo(resolver(datos, incognita)) == nombre


def test_el_nombre_de_archivo_no_lleva_caracteres_prohibidos_en_windows(monkeypatch):
    from refraccion import explicacion

    feo = 'a<b>:c"d/e' + BARRA + 'f|g?h*i' + chr(7)
    monkeypatch.setattr(explicacion, "resumen", lambda sol: (feo, ""))
    assert informe.nombre_de_archivo(resolver(Datos(), Incognita.THETA2)) == "Refracción - abcdefghi.pdf"


def test_el_pdf_deja_margenes_iguales_a_los_dos_lados(diagrama):
    # regresión: el diagrama se salía por la derecha porque Qt añade 2 cm de margen al imprimir
    from PySide6.QtCore import QSize

    from PySide6.QtGui import QColor, QImage, QPainter

    doc, _buffer = leer_pdf(generar(diagrama, Datos(1.0003, 1.333, 40, 0), Incognita.THETA2))
    pagina = QImage(1240, 1754, QImage.Format.Format_RGB32)       # el render trae el fondo transparente
    pagina.fill(QColor("white"))
    pintor = QPainter(pagina)
    pintor.drawImage(0, 0, doc.render(0, QSize(1240, 1754)))
    pintor.end()
    columnas = [x for y in range(0, int(1754 * 0.9), 3) for x in range(0, 1240, 2)
                if pagina.pixelColor(x, y).lightness() < 245]
    izquierda, derecha = min(columnas), 1240 - 1 - max(columnas)
    assert derecha >= 100                                          # unos 2 cm: no invade el margen
    assert abs(izquierda - derecha) <= 15                          # y queda centrado
