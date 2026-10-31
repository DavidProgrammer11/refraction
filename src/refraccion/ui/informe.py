"""El cálculo en PDF, en A4: la página 1 ilustra (resultado, diagrama y la curva de la
ley de Snell) y la 2 lleva el paso a paso entero.

Para entregar un ejercicio, imprimirlo o pegarlo en unos apuntes. Usa el mismo HTML
que la pestaña «Paso a paso», así que las fracciones y los colores salen iguales. El
paso a paso va en su propia página porque Qt no deja impedir que una fracción se parta.
"""
from __future__ import annotations

import re
from html import escape

from PySide6.QtCore import QBuffer, QByteArray, QDate, QIODevice, QMarginsF, QPoint, QUrl
from PySide6.QtGui import QFont, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter, QTextDocument

from .. import APP_NAME, ORG_NAME, __version__
from .. import explicacion as ex
from ..optica import Solucion
from . import colores as c
from .campos import ESPANOL
from .grafica import contenido_refraccion, grafica_refraccion
from .paso_a_paso import colorear, html as html_pasos

# Al imprimir, QTextDocument pone 2 cm de margen por su cuenta y 4 px más por cada lado: el
# PDF va sin márgenes propios y el hueco útil de un A4 queda en 170 mm, que en unidades del
# documento (96 ppp) son 642,5 menos esos 8:
ANCHO_UTIL = 634
_PROHIBIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def nombre_de_archivo(sol: Solucion) -> str:
    """«Refracción - θ₂ = 28,84°.pdf»: el resultado en el nombre, sin caracteres prohibidos."""
    titular = _PROHIBIDOS.sub("", ex.resumen(sol)[0]).strip()
    return f"{APP_NAME} - {titular}.pdf"


def imagen_de_curva(sol: Solucion, ancho: int = 900, alto: int = 400, escala: float = 2.5) -> QImage:
    """La curva θ₂(θ₁) con el punto del cálculo, dibujada aparte a buena resolución."""
    grafica = grafica_refraccion()
    grafica.ensurePolished()                        # para que use la letra del tema
    grafica.resize(ancho, alto)
    grafica.mostrar(contenido_refraccion(sol))
    imagen = QImage(int(ancho * escala), int(alto * escala), QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(c.TARJETA)
    pintor = QPainter(imagen)
    pintor.scale(escala, escala)
    grafica.render(pintor, QPoint(0, 0))
    pintor.end()
    return imagen


def _imagen(doc: QTextDocument, nombre: str, imagen: QImage) -> str:
    doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(nombre), imagen)
    alto = round(ANCHO_UTIL * imagen.height() / max(imagen.width(), 1))
    return f'<img src="{nombre}" width="{ANCHO_UTIL}" height="{alto}">'


def documento(sol: Solucion, medio1: str, medio2: str, diagrama: QImage,
              curva: QImage | None = None) -> QTextDocument:
    doc = QTextDocument()
    doc.setDefaultFont(QFont("Segoe UI", 10))
    titular, detalle = ex.resumen(sol)
    color_titular = c.TEXTO.name() if sol.ok else c.CRITICO.name()
    fecha = ESPANOL.toString(QDate.currentDate(), "d 'de' MMMM 'de' yyyy")
    gris = c.GRIS.name()
    partes = [
        f'<p style="margin:0; font-size:16pt; font-weight:600;">{escape(APP_NAME)}</p>',
        f'<p style="margin:0 0 10px 0; color:{gris};">La ley de Snell, explicada y dibujada'
        f" · {escape(fecha)}</p>",
        f'<p style="margin:0; font-size:20pt; font-weight:600; color:{color_titular};">'
        f"{colorear(titular)}</p>",
        f'<p style="margin:0 0 6px 0; color:#374151;">{colorear(detalle)}</p>',
        f'<p style="margin:0 0 8px 0; color:{gris};">Medio 1: {escape(medio1)} · '
        f"Medio 2: {escape(medio2)}</p>",
        f'<p style="margin:0 0 10px 0;">{_imagen(doc, "diagrama.png", diagrama)}</p>',
    ]
    if curva is not None:
        partes += [
            f'<p style="margin:4px 0 4px 0; font-weight:600;">La ley de Snell para todas las '
            f"incidencias</p>",
            f'<p style="margin:0;">{_imagen(doc, "curva.png", curva)}</p>',
        ]
    partes += [
        '<div style="page-break-before:always;">',
        f'<p style="margin:0 0 10px 0; font-size:14pt; font-weight:600;">El cálculo, paso a paso</p>',
        html_pasos(sol),
        f'<p style="margin-top:12px; color:{gris}; font-size:8pt;">Hecho con {escape(APP_NAME)} '
        f"{escape(__version__)} · {escape(ORG_NAME)}</p>",
        "</div>",
    ]
    doc.setHtml("".join(partes))
    return doc


def pdf(sol: Solucion, medio1: str, medio2: str, diagrama: QImage,
        curva: QImage | None = None) -> bytes:
    """El PDF en memoria: así un archivo bloqueado da un OSError al escribirlo, no un PDF vacío."""
    datos = QByteArray()
    salida = QBuffer(datos)
    salida.open(QIODevice.OpenModeFlag.WriteOnly)
    escritor = QPdfWriter(salida)
    escritor.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    escritor.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)   # los pone Qt
    escritor.setResolution(300)
    escritor.setTitle(f"{APP_NAME}: {ex.resumen(sol)[0]}")
    escritor.setCreator(f"{APP_NAME} {__version__} ({ORG_NAME})")
    documento(sol, medio1, medio2, diagrama, curva).print_(escritor)
    del escritor                                    # cierra el PDF antes de leer los bytes
    salida.close()
    return bytes(datos)
