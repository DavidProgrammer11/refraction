"""El cálculo paso a paso en HTML, con θ₁ en azul y θ₂ en verde como en el diagrama."""
from __future__ import annotations

from html import escape

from PySide6.QtWidgets import QTextBrowser, QWidget

from .. import explicacion as ex
from ..optica import Solucion
from . import colores as c

_FORMULA = "font-family:'Cambria Math','Cambria','Times New Roman',serif; font-size:13pt;"
_FONDOS = {ex.NORMAL: "#FFFFFF", ex.RESULTADO: "#EAF4FC", ex.AVISO: "#FFF5F5", ex.NOTA: "#F7F9FB"}
_SIMBOLOS = (
    ("θc", c.CRITICO), ("θB", c.BREWSTER),
    ("θ₁", c.THETA1), ("n₁", c.THETA1), ("θ₂", c.THETA2), ("n₂", c.THETA2),
)


def colorear(texto: str) -> str:
    """Escapa el texto y pinta cada símbolo con su color."""
    html = escape(texto)
    for simbolo, color in _SIMBOLOS:
        html = html.replace(simbolo, f'<span style="color:{color.name()}; font-weight:600;">{simbolo}</span>')
    return html


def formula(texto: str, negrita: bool = False) -> str:
    """Una fórmula en HTML. Si es «a = b / c», la división se escribe como una fracción."""
    peso = "font-weight:700;" if negrita else ""
    lados = texto.split(" = ")
    if len(lados) == 2 and lados[1].count(" / ") == 1:
        numerador, denominador = lados[1].split(" / ")
        return (
            f'<table border="0" cellspacing="0" cellpadding="0" style="{_FORMULA}{peso} margin-top:3px;">'
            f'<tr><td valign="middle" style="padding-right:6px;">{colorear(lados[0])} =</td>'
            f'<td><table border="0" cellspacing="0" cellpadding="0">'
            f'<tr><td align="center" style="border-bottom:1px solid {c.TEXTO.name()}; '
            f'padding:0 4px 2px 4px;">{colorear(numerador)}</td></tr>'
            f'<tr><td align="center" style="padding:2px 4px 0 4px;">{colorear(denominador)}</td></tr>'
            f"</table></td></tr></table>"
        )
    return f'<div style="{_FORMULA}{peso} margin-top:3px;">{colorear(texto)}</div>'


def html(sol: Solucion) -> str:
    partes = [
        f'<p style="margin:0 0 2px 0; font-size:11pt; font-weight:600; color:{c.TEXTO.name()};">'
        f"{colorear(ex.objetivo(sol))}</p>",
        f'<p style="margin:0 0 10px 0; color:{c.GRIS.name()};">Datos: {colorear(ex.datos_conocidos(sol))}</p>',
    ]
    for numero, paso in enumerate(ex.explicar(sol), start=1):
        titulo_color = c.CRITICO.name() if paso.tipo == ex.AVISO else c.TEXTO.name()
        cuerpo = [f'<div style="font-weight:600; color:{titulo_color};">{escape(paso.titulo)}</div>']
        cuerpo += [formula(f, negrita=paso.tipo == ex.RESULTADO) for f in paso.formulas]
        cuerpo += [f'<div style="color:#374151; margin-top:3px;">{colorear(t)}</div>' for t in paso.texto]
        partes.append(
            f'<table width="100%" border="0" cellspacing="0" cellpadding="8" '
            f'bgcolor="{_FONDOS[paso.tipo]}" style="margin-bottom:6px;">'
            f'<tr><td width="28" valign="top" style="color:{c.PRIMARIO.name()}; font-weight:700;">'
            f"{numero}</td><td>{''.join(cuerpo)}</td></tr></table>"
        )
    return "".join(partes)


class PasoAPaso(QTextBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PasoAPaso")
        self.setOpenLinks(False)
        self.document().setDocumentMargin(12)

    def mostrar(self, sol: Solucion) -> None:
        barra = self.verticalScrollBar()
        posicion = barra.value()
        self.setHtml(html(sol))
        barra.setValue(posicion)          # al arrastrar un rayo no salta arriba
