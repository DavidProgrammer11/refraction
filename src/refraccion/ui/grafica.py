"""Gráficas dibujadas con QPainter: las fórmulas recorridas de 0° a 90°.

Una gráfica genérica (ejes, curvas, zonas, líneas verticales y lectura con el
ratón) y las dos de la app: el ángulo refractado y la luz reflejada/transmitida.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import explicacion as ex
from ..optica import (
    Estado, Solucion, angulo_brewster, angulo_critico, curva_fresnel, curva_refraccion,
    fresnel, refractar,
)
from . import colores as c

Lector = Callable[[float], list[tuple[str, QColor]]]


@dataclass
class Serie:
    puntos: list[tuple[float, float]]
    color: QColor
    ancho: float = 2.0
    estilo: Qt.PenStyle = Qt.PenStyle.SolidLine
    etiqueta: str = ""


@dataclass
class LineaV:
    x: float
    color: QColor
    etiqueta: str = ""


@dataclass
class Zona:
    x0: float
    x1: float
    color: QColor
    etiqueta: str = ""


@dataclass
class Marca:
    x: float
    y: float
    color: QColor


@dataclass
class Contenido:
    series: list[Serie] = field(default_factory=list)
    lineas: list[LineaV] = field(default_factory=list)
    zonas: list[Zona] = field(default_factory=list)
    marcas: list[Marca] = field(default_factory=list)
    lector: Lector | None = None
    mensaje: str = ""


class Grafica(QWidget):
    MARGEN_IZQ, MARGEN_DER, MARGEN_ARRIBA, MARGEN_ABAJO = 52, 18, 34, 40

    def __init__(self, titulo_x: str, color_x: QColor, titulo_y: str, color_y: QColor,
                 y_max: float, paso_y: float, unidad_y: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.titulo_x, self.color_x = titulo_x, color_x
        self.titulo_y, self.color_y = titulo_y, color_y
        self.x_max, self.paso_x = 90.0, 15.0
        self.y_max, self.paso_y, self.unidad_y = y_max, paso_y, unidad_y
        self.contenido = Contenido()
        self.raton_x: float | None = None

    def sizeHint(self) -> QSize:
        return QSize(640, 300)

    def minimumSizeHint(self) -> QSize:
        return QSize(320, 200)

    def mostrar(self, contenido: Contenido) -> None:
        self.contenido = contenido
        self.update()

    # --- coordenadas -----------------------------------------------------------------

    def area(self) -> QRectF:
        r = QRectF(self.rect())
        return r.adjusted(self.MARGEN_IZQ, self.MARGEN_ARRIBA, -self.MARGEN_DER, -self.MARGEN_ABAJO)

    def a_pantalla(self, x: float, y: float) -> QPointF:
        a = self.area()
        return QPointF(a.left() + a.width() * x / self.x_max,
                       a.bottom() - a.height() * y / self.y_max)

    def a_dato_x(self, px: float) -> float:
        a = self.area()
        return (px - a.left()) / a.width() * self.x_max

    # --- ratón ---------------------------------------------------------------------------

    def mouseMoveEvent(self, evento: QMouseEvent) -> None:
        a = self.area()
        pos = evento.position()
        dentro = a.contains(pos) and self.contenido.lector is not None
        self.raton_x = self.a_dato_x(pos.x()) if dentro else None
        self.update()

    def leaveEvent(self, evento) -> None:
        self.raton_x = None
        self.update()
        super().leaveEvent(evento)

    # --- pintar --------------------------------------------------------------------------

    def _fuente(self, p: QPainter, puntos: float, negrita: bool = False) -> QFontMetricsF:
        fuente = QFont(self.font())
        fuente.setPointSizeF(puntos)
        fuente.setBold(negrita)
        p.setFont(fuente)
        return QFontMetricsF(fuente)

    def paintEvent(self, evento) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        fondo = QPainterPath()
        fondo.addRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        p.fillPath(fondo, c.TARJETA)
        p.setPen(QPen(c.BORDE, 1))
        p.drawPath(fondo)
        a = self.area()
        if a.width() < 40 or a.height() < 40:
            p.end()
            return
        self._ejes(p, a)
        cont = self.contenido
        if cont.mensaje:
            self._fuente(p, 10)
            p.setPen(c.GRIS)
            p.drawText(a, int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap), cont.mensaje)
        p.save()
        p.setClipRect(a.adjusted(-2, -2, 2, 2))
        for zona in cont.zonas:
            arriba_izq = self.a_pantalla(zona.x0, self.y_max)
            abajo_der = self.a_pantalla(zona.x1, 0)
            p.fillRect(QRectF(arriba_izq, abajo_der), zona.color)
        for linea in cont.lineas:
            p.setPen(QPen(linea.color, 1.3, Qt.PenStyle.DashLine))
            p.drawLine(self.a_pantalla(linea.x, 0), self.a_pantalla(linea.x, self.y_max))
        for serie in cont.series:
            if len(serie.puntos) < 2:
                continue
            camino = QPainterPath(self.a_pantalla(*serie.puntos[0]))
            for x, y in serie.puntos[1:]:
                camino.lineTo(self.a_pantalla(x, y))
            pluma = QPen(serie.color, serie.ancho, serie.estilo)
            pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
            pluma.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pluma)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(camino)
        for marca in cont.marcas:
            punto = self.a_pantalla(marca.x, marca.y)
            guia = QPen(c.con_alfa(marca.color, 0.5), 1, Qt.PenStyle.DotLine)
            p.setPen(guia)
            p.drawLine(punto, self.a_pantalla(marca.x, 0))
            p.drawLine(punto, self.a_pantalla(0, marca.y))
            p.setPen(QPen(c.TARJETA, 2))
            p.setBrush(marca.color)
            p.drawEllipse(punto, 5.5, 5.5)
        p.restore()
        self._rotulos_lineas(p, a)
        self._leyenda(p)
        if self.raton_x is not None and 0 <= self.raton_x <= self.x_max:
            self._lectura(p, a)
        p.end()

    def _ejes(self, p: QPainter, a: QRectF) -> None:
        m = self._fuente(p, 8)
        rejilla = QPen(QColor("#EEF1F5"), 1)
        for i in range(int(round(self.x_max / self.paso_x)) + 1):
            x = i * self.paso_x
            arriba, abajo = self.a_pantalla(x, self.y_max), self.a_pantalla(x, 0)
            p.setPen(rejilla)
            p.drawLine(arriba, abajo)
            texto = f"{ex.num(x, 0)}°"
            p.setPen(c.GRIS)
            p.drawText(QPointF(abajo.x() - m.horizontalAdvance(texto) / 2, abajo.y() + m.ascent() + 4), texto)
        for i in range(int(round(self.y_max / self.paso_y)) + 1):
            y = i * self.paso_y
            izq, der = self.a_pantalla(0, y), self.a_pantalla(self.x_max, y)
            p.setPen(rejilla)
            p.drawLine(izq, der)
            texto = f"{ex.num(y, 0)}{self.unidad_y}"
            p.setPen(c.GRIS)
            p.drawText(QPointF(izq.x() - m.horizontalAdvance(texto) - 6, izq.y() + m.ascent() / 2 - 1), texto)
        p.setPen(QPen(QColor("#9AA5B1"), 1.2))
        p.drawLine(a.bottomLeft(), a.bottomRight())
        p.drawLine(a.bottomLeft(), a.topLeft())
        # títulos de los ejes, del color de su ángulo
        m = self._fuente(p, 9, negrita=True)
        p.setPen(self.color_x)
        p.drawText(QPointF(a.center().x() - m.horizontalAdvance(self.titulo_x) / 2,
                           a.bottom() + 20 + m.ascent()), self.titulo_x)
        p.save()
        p.translate(14, a.center().y() + m.horizontalAdvance(self.titulo_y) / 2)
        p.rotate(-90)
        p.setPen(self.color_y)
        p.drawText(QPointF(0, m.ascent() / 2), self.titulo_y)
        p.restore()

    def _rotulos_lineas(self, p: QPainter, a: QRectF) -> None:
        m = self._fuente(p, 8, negrita=True)
        ocupado: list[QRectF] = []
        for linea in self.contenido.lineas:
            if not linea.etiqueta:
                continue
            punto = self.a_pantalla(linea.x, self.y_max)
            ancho = m.horizontalAdvance(linea.etiqueta) + 8
            caja = QRectF(punto.x() + 3, a.top() + 3, ancho, m.height() + 2)
            if caja.right() > a.right():
                caja.moveRight(punto.x() - 3)
            while any(caja.intersects(otra) for otra in ocupado):
                caja.translate(0, m.height() + 3)
            ocupado.append(caja)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c.con_alfa(c.TARJETA, 0.9))
            p.drawRoundedRect(caja, 3, 3)
            p.setPen(linea.color)
            p.drawText(caja, int(Qt.AlignmentFlag.AlignCenter), linea.etiqueta)

    def _leyenda(self, p: QPainter) -> None:
        m = self._fuente(p, 8.5)
        x = float(self.MARGEN_IZQ)
        y = 11.0
        for serie in self.contenido.series:
            if not serie.etiqueta:
                continue
            ancho = 22 + m.horizontalAdvance(serie.etiqueta) + 16
            if x + ancho > self.width() - self.MARGEN_DER and x > self.MARGEN_IZQ:
                break                                   # no cabe: mejor cortar que montar
            p.setPen(QPen(serie.color, max(serie.ancho, 1.5), serie.estilo))
            p.drawLine(QPointF(x, y + m.height() / 2), QPointF(x + 18, y + m.height() / 2))
            p.setPen(c.TEXTO)
            p.drawText(QPointF(x + 22, y + m.ascent()), serie.etiqueta)
            x += ancho

    def _lectura(self, p: QPainter, a: QRectF) -> None:
        lineas = self.contenido.lector(self.raton_x)
        if not lineas:
            return
        x = self.a_pantalla(self.raton_x, 0).x()
        p.setPen(QPen(c.con_alfa(c.TEXTO, 0.35), 1))
        p.drawLine(QPointF(x, a.top()), QPointF(x, a.bottom()))
        m = self._fuente(p, 9)
        ancho = max(m.horizontalAdvance(texto) for texto, _ in lineas) + 16
        alto = len(lineas) * m.height() + 10
        caja = QRectF(x + 10, a.top() + 26, ancho, alto)
        if caja.right() > a.right():
            caja.moveRight(x - 10)
        p.setPen(QPen(c.BORDE, 1))
        p.setBrush(c.TARJETA)
        p.drawRoundedRect(caja, 5, 5)
        for i, (texto, color) in enumerate(lineas):
            p.setPen(color)
            p.drawText(QPointF(caja.left() + 8, caja.top() + 5 + i * m.height() + m.ascent()), texto)


# --- las dos gráficas de la app --------------------------------------------------------

def _indices(sol: Solucion) -> tuple[float, float] | None:
    d = sol.completa() or sol.datos
    if not sol.ok and not sol.incognita.es_angulo:
        return None                                     # falta un índice
    return d.n1, d.n2


def _theta1(sol: Solucion) -> float | None:
    if sol.ok:
        return sol.completa().theta1
    if sol.estado is Estado.REFLEXION_TOTAL:
        return sol.datos.theta1
    return None


def contenido_refraccion(sol: Solucion) -> Contenido:
    """θ₂ en función de θ₁: la ley de Snell para todas las incidencias a la vez."""
    indices = _indices(sol)
    if indices is None:
        return Contenido(mensaje="Sin los dos índices no se puede dibujar la curva.")
    n1, n2 = indices
    critico = angulo_critico(n1, n2)
    cont = Contenido(series=[
        Serie([(0, 0), (90, 90)], c.GRIS_CLARO, 1.3, Qt.PenStyle.DashLine,
              "θ₂ = θ₁ (si n₁ = n₂, no se desvía)"),
        Serie(curva_refraccion(n1, n2), c.RAYO, 2.6,
              etiqueta=f"θ₂ con n₁ = {ex.indice(n1)} y n₂ = {ex.indice(n2)}"),
    ])
    if critico is not None:
        cont.zonas.append(Zona(critico, 90, c.con_alfa(c.CRITICO, 0.07)))
        cont.lineas.append(LineaV(critico, c.CRITICO, f"θc = {ex.num(critico, 1)}° · reflexión total"))
    theta1 = _theta1(sol)
    if theta1 is not None:
        theta2 = refractar(n1, n2, theta1)
        if theta2 is not None:
            cont.marcas.append(Marca(theta1, theta2, c.RAYO))
        else:
            cont.lineas.append(LineaV(theta1, c.THETA1, f"θ₁ = {ex.num(theta1, 1)}°"))

    def lector(x: float) -> list[tuple[str, QColor]]:
        theta2 = refractar(n1, n2, x)
        lineas = [(f"θ₁ = {ex.num(x, 1)}°", c.THETA1)]
        if theta2 is None:
            lineas.append(("reflexión total", c.CRITICO))
        else:
            lineas.append((f"θ₂ = {ex.num(theta2, 1)}°", c.THETA2))
            desvio = theta2 - x
            if abs(desvio) >= 0.05:
                lineas.append((f"se desvía {ex.num(abs(desvio), 1)}°", c.GRIS))
        return lineas

    cont.lector = lector
    return cont


def contenido_fresnel(sol: Solucion) -> Contenido:
    """Cuánta luz se refleja y cuánta pasa según el ángulo (ecuaciones de Fresnel)."""
    indices = _indices(sol)
    if indices is None:
        return Contenido(mensaje="Sin los dos índices no se puede dibujar la curva.")
    n1, n2 = indices
    curva = curva_fresnel(n1, n2)
    cont = Contenido(series=[
        Serie([(x, f.r * 100) for x, f in curva], c.RAYO, 2.6, etiqueta="se refleja (R)"),
        Serie([(x, f.t * 100) for x, f in curva], c.THETA2, 2.6, etiqueta="pasa (T)"),
        Serie([(x, f.rs * 100) for x, f in curva], c.con_alfa(c.RAYO, 0.6), 1.3,
              Qt.PenStyle.DashLine, "R con luz polarizada s"),
        Serie([(x, f.rp * 100) for x, f in curva], c.con_alfa(c.BREWSTER, 0.7), 1.3,
              Qt.PenStyle.DotLine, "R con luz polarizada p"),
    ])
    critico = angulo_critico(n1, n2)
    if n1 != n2:                    # Brewster siempre queda antes del ángulo crítico
        brewster = angulo_brewster(n1, n2)
        cont.lineas.append(LineaV(brewster, c.BREWSTER, f"Brewster {ex.num(brewster, 1)}°"))
    if critico is not None:
        cont.zonas.append(Zona(critico, 90, c.con_alfa(c.CRITICO, 0.07)))
        cont.lineas.append(LineaV(critico, c.CRITICO, f"θc = {ex.num(critico, 1)}°"))
    theta1 = _theta1(sol)
    if theta1 is not None:
        f = fresnel(n1, n2, theta1)
        cont.marcas += [Marca(theta1, f.r * 100, c.RAYO), Marca(theta1, f.t * 100, c.THETA2)]

    def lector(x: float) -> list[tuple[str, QColor]]:
        f = fresnel(n1, n2, x)
        return [
            (f"θ₁ = {ex.num(x, 1)}°", c.THETA1),
            (f"se refleja {ex.porcentaje(f.r)}", c.RAYO),
            (f"pasa {ex.porcentaje(f.t)}", c.THETA2),
            (f"s: {ex.porcentaje(f.rs)} · p: {ex.porcentaje(f.rp)}", c.GRIS),
        ]

    cont.lector = lector
    return cont


def grafica_refraccion(parent: QWidget | None = None) -> Grafica:
    return Grafica("θ₁ · ángulo de incidencia", c.THETA1, "θ₂ · ángulo refractado", c.THETA2,
                   90, 15, "°", parent)


def grafica_fresnel(parent: QWidget | None = None) -> Grafica:
    return Grafica("θ₁ · ángulo de incidencia", c.THETA1, "% de la luz", c.TEXTO,
                   100, 20, " %", parent)
