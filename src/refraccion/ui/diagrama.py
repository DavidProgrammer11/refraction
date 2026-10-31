"""Diagrama de la refracción: los dos medios, la normal, los rayos y sus ángulos.

Los rayos se arrastran con el ratón para cambiar el ángulo. Los frentes de onda
animados enseñan por qué se dobla la luz: al cruzar no cambia la frecuencia, pero
en el medio más denso va más despacio, las ondas se aprietan (λ = λ₀ / n) y, para
no romperse en la superficie, tienen que girar.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetricsF, QGradient, QImage, QLinearGradient, QMouseEvent,
    QPainter, QPainterPath, QPen, QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import explicacion as ex
from ..optica import Estado, Incognita, Solucion, angulo_critico, fresnel
from . import colores as c

BANDA = 50                  # alto reservado arriba y abajo para los rótulos de cada medio
ANCHO_ROTULOS = 320         # lo que ocupan, desde el borde, los rótulos de las esquinas
PASO_FASE = 0.018           # avance de los frentes de onda en cada fotograma (en periodos)
SEMIANCHO = 0.22            # medio ancho del haz de ondas, en fracción del largo del rayo


def anchos_de_haz(largo: float, theta1: float, theta2: float | None) -> tuple[float, float, float]:
    """(huella en la superficie, medio ancho del haz incidente y reflejado, del refractado).

    Los haces comparten la huella en la superficie, así que el refractado es más ancho
    o más estrecho según θ₂. Con incidencia casi rasante la huella se limita.
    """
    huella = largo * SEMIANCHO / max(math.cos(math.radians(theta1)), 0.2)
    ancho1 = huella * math.cos(math.radians(theta1))
    ancho2 = huella * math.cos(math.radians(theta2)) if theta2 is not None else 0.0
    return huella, ancho1, ancho2


def longitud_de_onda(largo: float, n: float) -> float:
    """En el dibujo λ₀ es un sexto del rayo; en un medio de índice n, λ = λ₀ / n."""
    return largo / 6.0 / n


@dataclass(frozen=True)
class Cota:
    """Una cota de una longitud de onda junto a un haz."""

    avance: tuple[float, float]       # hacia dónde va la luz
    desde: float                      # dónde empieza, medido desde la superficie a lo largo del haz
    largo: float                      # una longitud de onda
    aparte: float                     # distancia al eje del haz: por fuera de él
    rotulo: str
    medio: int


def cotas_lambda(largo: float, n1: float, n2: float, t1: float, t2: float | None) -> list[Cota]:
    """Las cotas de λ₁ y λ₂ (λ₂ solo si hay refractado): se ve que λ₂ / λ₁ = n₁ / n₂."""
    _, ancho1, ancho2 = anchos_de_haz(largo, t1, t2)
    a1 = math.radians(t1)
    cotas = [Cota((math.sin(a1), math.cos(a1)), -0.8 * largo, longitud_de_onda(largo, n1),
                  ancho1 + 9, "λ₁", 1)]
    if t2 is not None:
        a2 = math.radians(t2)
        cotas.append(Cota((math.sin(a2), math.cos(a2)), 0.5 * largo, longitud_de_onda(largo, n2),
                          ancho2 + 9, "λ₂", 2))
    return cotas


def _punto(o: QPointF, grados_mat: float, radio: float) -> QPointF:
    """Punto a `radio` de `o` en la dirección `grados_mat` (0° a la derecha, 90° arriba)."""
    a = math.radians(grados_mat)
    return QPointF(o.x() + radio * math.cos(a), o.y() - radio * math.sin(a))


class Diagrama(QWidget):
    """Dibuja una Solucion. Emite anguloArrastrado(medio, grados) al arrastrar un rayo."""

    anguloArrastrado = Signal(int, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._sol: Solucion | None = None
        self._medios = ("", "")
        self._arrastrables = (True, False)
        self._arrastrando: int | None = None
        self.frentes = True
        self.animar = True
        self.fase = 0.0
        self._reloj = QTimer(self)
        self._reloj.setInterval(33)
        self._reloj.timeout.connect(self._avanzar)

    def sizeHint(self) -> QSize:
        return QSize(720, 420)

    def minimumSizeHint(self) -> QSize:
        return QSize(380, 300)

    # --- lo que se muestra -----------------------------------------------------------

    @property
    def solucion(self) -> Solucion | None:
        return self._sol

    def mostrar(self, sol: Solucion, medio1: str, medio2: str) -> None:
        self._sol = sol
        self._medios = (medio1, medio2)
        self.update()

    def set_arrastrables(self, medio1: bool, medio2: bool) -> None:
        """Qué rayos se pueden arrastrar: solo los ángulos que son datos, no la incógnita."""
        self._arrastrables = (medio1, medio2)
        if self._arrastrando and not self._arrastrables[self._arrastrando - 1]:
            self._arrastrando = None

    def set_frentes(self, activo: bool) -> None:
        self.frentes = activo
        self._ajustar_reloj()
        self.update()

    def set_animar(self, activo: bool) -> None:
        self.animar = activo
        self._ajustar_reloj()

    @property
    def animando(self) -> bool:
        return self._reloj.isActive()

    def _ajustar_reloj(self) -> None:
        # al minimizar, Qt manda hideEvent a los hijos pero isVisible() sigue diciendo que sí
        if self.frentes and self.animar and self.isVisible() and not self.window().isMinimized():
            self._reloj.start()
        else:
            self._reloj.stop()

    def _avanzar(self) -> None:
        self.fase = (self.fase + PASO_FASE) % 1.0
        self.update()

    def showEvent(self, evento) -> None:
        super().showEvent(evento)
        self._ajustar_reloj()

    def hideEvent(self, evento) -> None:
        super().hideEvent(evento)
        self._ajustar_reloj()

    # --- geometría ---------------------------------------------------------------------

    @staticmethod
    def geometria(r: QRectF) -> tuple[QPointF, float]:
        """El punto de incidencia (centro) y el largo de los rayos.

        Los rayos solo se meten en las bandas de rótulos si el dibujo es tan ancho
        que no pueden llegar a los textos de las esquinas.
        """
        o = QPointF(r.center().x(), r.top() + r.height() / 2)
        sin_bandas = r.height() / 2 - BANDA - 8
        hasta_textos = r.width() / 2 - ANCHO_ROTULOS
        largo = min(r.width() / 2 - 24, r.height() / 2 - 16, max(sin_bandas, hasta_textos))
        return o, max(40.0, largo)

    def _modelo(self) -> tuple[float | None, float | None, float | None, float | None]:
        """(n₁, n₂, θ₁, θ₂) que se dibujan; None lo que no se conoce."""
        sol = self._sol
        d = sol.completa() or sol.datos
        desconocida = None if sol.ok else sol.incognita
        n1 = None if desconocida is Incognita.N1 else d.n1
        n2 = None if desconocida is Incognita.N2 else d.n2
        t1 = None if desconocida is Incognita.THETA1 else d.theta1
        t2 = None if desconocida is Incognita.THETA2 else d.theta2
        return n1, n2, t1, t2

    # --- ratón: arrastrar un rayo ---------------------------------------------------------

    def _medio_en(self, pos: QPointF) -> int:
        o, _ = self.geometria(QRectF(self.rect()))
        return 1 if pos.y() < o.y() else 2

    def _angulo_en(self, pos: QPointF, medio: int) -> float:
        o, _ = self.geometria(QRectF(self.rect()))
        dx = abs(pos.x() - o.x())
        dy = (o.y() - pos.y()) if medio == 1 else (pos.y() - o.y())
        if dy <= 0:
            return 90.0
        return round(math.degrees(math.atan2(dx, dy)), 1)

    def mousePressEvent(self, evento: QMouseEvent) -> None:
        if evento.button() != Qt.MouseButton.LeftButton or self._sol is None:
            return super().mousePressEvent(evento)
        medio = self._medio_en(evento.position())
        if self._arrastrables[medio - 1]:
            self._arrastrando = medio
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.anguloArrastrado.emit(medio, self._angulo_en(evento.position(), medio))

    def mouseMoveEvent(self, evento: QMouseEvent) -> None:
        if self._arrastrando:
            self.anguloArrastrado.emit(self._arrastrando,
                                       self._angulo_en(evento.position(), self._arrastrando))
            return
        medio = self._medio_en(evento.position())
        if self._sol is not None and self._arrastrables[medio - 1]:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()

    def mouseReleaseEvent(self, evento: QMouseEvent) -> None:
        if self._arrastrando and evento.button() == Qt.MouseButton.LeftButton:
            self._arrastrando = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(evento)

    # --- pintar ------------------------------------------------------------------------

    def paintEvent(self, evento) -> None:
        p = QPainter(self)
        self.pintar(p, QRectF(self.rect()))
        p.end()

    def imagen(self, escala: float = 2.0, tamano: QSize | None = None) -> QImage:
        """El diagrama en una imagen, a `escala` × su tamaño (u otro `tamano`, para imprimir)."""
        tamano = tamano or self.size()
        img = QImage(int(tamano.width() * escala), int(tamano.height() * escala),
                     QImage.Format.Format_ARGB32_Premultiplied)
        img.setDevicePixelRatio(escala)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        self.pintar(p, QRectF(0, 0, tamano.width(), tamano.height()))
        p.end()
        return img

    def pintar(self, p: QPainter, r: QRectF) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setFont(self.font())
        tarjeta = QPainterPath()
        tarjeta.addRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        p.fillPath(tarjeta, c.TARJETA)
        if self._sol is None:
            return
        p.save()
        p.setClipPath(tarjeta)

        n1, n2, t1, t2 = self._modelo()
        sol = self._sol
        o, largo = self.geometria(r)
        firme = sol.ok or sol.estado is Estado.REFLEXION_TOTAL
        total = sol.estado is Estado.REFLEXION_TOTAL

        # los dos medios: más azul cuanto mayor es el índice
        arriba = QRectF(r.left(), r.top(), r.width(), o.y() - r.top())
        abajo = QRectF(r.left(), o.y(), r.width(), r.bottom() - o.y())
        p.fillRect(arriba, c.medio(n1) if n1 is not None else c.con_alfa(c.GRIS, 0.06))
        p.fillRect(abajo, c.medio(n2) if n2 is not None else c.con_alfa(c.GRIS, 0.06))

        critico = angulo_critico(n1, n2) if n1 is not None and n2 is not None else None
        if critico is not None:
            self._zona_reflexion_total(p, o, largo, critico)
        if sol.estado is Estado.SIN_SOLUCION and sol.incognita is Incognita.THETA1:
            self._zona_imposible(p, o, largo, angulo_critico(n2, n1))

        reflejada = 0.0
        if firme and t1 is not None:
            reflejada = 1.0 if total else fresnel(n1, n2, t1).r
            if self.frentes:
                self._frentes(p, o, largo, n1, n2, t1, None if total else t2, reflejada)
                self._cotas_lambda(p, r, o, largo, n1, n2, t1, None if total else t2)

        # superficie y normal
        p.setPen(QPen(QColor("#8A96A6"), 1.4))
        p.drawLine(QPointF(r.left(), o.y()), QPointF(r.right(), o.y()))
        self._escribir(p, r.right() - 14, o.y() - 16, "superficie", c.GRIS, 8, derecha=True, halo=True)
        normal = QPen(c.GRIS, 1.2, Qt.PenStyle.DashLine)
        p.setPen(normal)
        p.drawLine(QPointF(o.x(), o.y() - largo - 4), QPointF(o.x(), o.y() + largo + 4))
        self._escribir(p, o.x() + 5, o.y() - largo - 4, "normal", c.GRIS, 8)

        # ángulos
        radio = max(26.0, largo * 0.30)
        if t1 is not None:
            self._arco(p, o, radio, 90, t1, c.THETA1 if firme else c.GRIS, "θ₁")
        if t2 is not None:
            self._arco(p, o, radio * 0.86, 270, t2, c.THETA2 if firme else c.GRIS, "θ₂")

        # rayos: incidente, reflejado y refractado (rótulos fuera del haz de frentes)
        aparte1 = aparte2 = 7.0
        if self.frentes and firme and t1 is not None:
            _, ancho1, ancho2 = anchos_de_haz(largo, t1, t2)
            aparte1, aparte2 = ancho1 + 6, max(ancho2 + 6, 7.0)
        if t1 is not None:
            inicio = _punto(o, 90 + t1, largo)
            if firme and reflejada > 0:
                fin_reflejo = _punto(o, 90 - t1, largo)
                alfa = 0.18 + 0.82 * math.sqrt(reflejada)
                self._rayo(p, o, fin_reflejo, c.con_alfa(c.RAYO, alfa), 1.4 + 1.6 * reflejada)
                self._rotulo_rayo(p, o, fin_reflejo, "reflejado",
                                  c.con_alfa(c.RAYO, max(alfa, .6)), aparte1)
            self._rayo(p, inicio, o, c.RAYO if firme else c.GRIS_CLARO, 3.0, not firme)
            self._rotulo_rayo(p, inicio, o, "incidente", c.RAYO if firme else c.GRIS, aparte1,
                              desde_fin=True)
        if t2 is not None:
            fin = _punto(o, 270 + t2, largo)
            pasa = 1.0 - reflejada
            color = c.con_alfa(c.RAYO, 0.35 + 0.65 * pasa) if firme else c.GRIS_CLARO
            self._rayo(p, o, fin, color, 1.4 + 1.6 * pasa if firme else 3.0, not firme)
            self._rotulo_rayo(p, o, fin, "refractado", color if firme else c.GRIS, aparte2)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c.TEXTO)
        p.drawEllipse(o, 3.2, 3.2)

        self._bandas(p, r, n1, n2, t1, t2, reflejada, firme, total)
        if not sol.ok:
            self._aviso(p, r, o, largo)
        p.restore()
        p.setPen(QPen(c.BORDE, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(tarjeta)

    # --- piezas del dibujo ----------------------------------------------------------------

    def _zona_reflexion_total(self, p: QPainter, o: QPointF, largo: float, critico: float) -> None:
        """Las incidencias que superan el ángulo crítico, sombreadas en rojo."""
        caja = QRectF(o.x() - largo, o.y() - largo, 2 * largo, 2 * largo)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c.con_alfa(c.CRITICO, 0.07))
        p.drawPie(caja, int((90 + critico) * 16), int((90 - critico) * 16))
        fin = _punto(o, 90 + critico, largo)
        p.setPen(QPen(c.con_alfa(c.CRITICO, 0.75), 1.3, Qt.PenStyle.DashLine))
        p.drawLine(o, fin)
        texto = f"θc = {ex.num(critico, 1)}°"
        ancho = QFontMetricsF(self._fuente(p, 8)).horizontalAdvance(texto)
        self._escribir(p, fin.x() - ancho - 6, fin.y() - 8, texto, c.CRITICO, 8, halo=True)

    def _zona_imposible(self, p: QPainter, o: QPointF, largo: float, limite: float) -> None:
        """Los ángulos refractados a los que no llega ningún rayo (n₂ > n₁)."""
        caja = QRectF(o.x() - largo, o.y() - largo, 2 * largo, 2 * largo)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c.con_alfa(c.CRITICO, 0.07))
        p.drawPie(caja, int((270 + limite) * 16), int((90 - limite) * 16))
        fin = _punto(o, 270 + limite, largo)
        p.setPen(QPen(c.con_alfa(c.CRITICO, 0.75), 1.3, Qt.PenStyle.DashLine))
        p.drawLine(o, fin)
        self._escribir(p, fin.x() + 6, fin.y() - 4, f"θ₂ máx = {ex.num(limite, 1)}°", c.CRITICO, 8,
                       halo=True)

    def _frentes(self, p: QPainter, o: QPointF, largo: float, n1: float, n2: float,
                 t1: float, t2: float | None, reflejada: float) -> None:
        """Frentes de onda de un haz alrededor de cada rayo.

        En todos los haces la fase avanza igual (misma frecuencia); lo que cambia de
        un medio a otro es la separación entre frentes, λ₀ / n. Como n₁ sen θ₁ = n₂ sen θ₂,
        los frentes de los dos lados se juntan justo en la superficie.
        """
        huella, _, _ = anchos_de_haz(largo, t1, t2)
        lam1 = longitud_de_onda(largo, n1)
        a1 = math.radians(t1)
        incidente = QPointF(math.sin(a1), math.cos(a1))          # hacia donde va la luz
        reflejo = QPointF(math.sin(a1), -math.cos(a1))
        self._haz(p, o, huella, incidente * -1.0, incidente, lam1, largo, 1.0)
        if reflejada > 0:
            self._haz(p, o, huella, reflejo, reflejo, lam1, largo, math.sqrt(reflejada))
        if t2 is not None:
            a2 = math.radians(t2)
            refractado = QPointF(math.sin(a2), math.cos(a2))
            self._haz(p, o, huella, refractado, refractado, longitud_de_onda(largo, n2), largo, 1.0)

    def _haz(self, p: QPainter, o: QPointF, huella: float, hacia: QPointF, avance: QPointF,
             lam: float, largo: float, intensidad: float) -> None:
        izq, der = QPointF(o.x() - huella, o.y()), QPointF(o.x() + huella, o.y())

        def hasta_el_final(desde: QPointF) -> QPointF:
            # el haz acaba a `largo` de o medido a lo largo del rayo: corte perpendicular
            recorrido = largo - ((desde.x() - o.x()) * hacia.x() + (desde.y() - o.y()) * hacia.y())
            return desde + hacia * recorrido

        camino = QPainterPath()
        camino.addPolygon(QPolygonF([izq, der, hasta_el_final(der), hasta_el_final(izq)]))
        camino.closeSubpath()
        p.save()
        p.setClipPath(camino, Qt.ClipOperation.IntersectClip)
        # la onda: bandas que se repiten cada λ, cresta naranja y valle casi transparente
        inicio = o + avance * (lam * self.fase)
        onda = QLinearGradient(inicio, inicio + avance * lam)
        onda.setSpread(QGradient.Spread.RepeatSpread)
        for i in range(9):
            posicion = i / 8
            onda.setColorAt(posicion, c.con_alfa(
                c.RAYO, intensidad * (0.05 + 0.30 * math.cos(math.pi * posicion) ** 2)))
        p.fillPath(camino, QBrush(onda))
        # y una línea fina en cada cresta: el frente de onda
        p.setPen(QPen(c.con_alfa(c.RAYO, 0.55 * intensidad), 1.3))
        perpendicular = QPointF(-avance.y(), avance.x())
        alcance = largo + huella
        for m in range(math.floor(-alcance / lam) - 2, math.ceil(alcance / lam) + 2):
            centro = o + avance * (lam * (m + self.fase))
            p.drawLine(centro - perpendicular * (2 * alcance), centro + perpendicular * (2 * alcance))
        p.restore()

    def _cotas_lambda(self, p: QPainter, r: QRectF, o: QPointF, largo: float, n1: float,
                      n2: float, t1: float, t2: float | None) -> None:
        """Una cota de una longitud de onda junto a cada haz."""
        for cota in cotas_lambda(largo, n1, n2, t1, t2):
            self._cota(p, r, o, QPointF(*cota.avance), cota.desde, cota.largo, cota.aparte,
                       cota.rotulo, c.THETA1 if cota.medio == 1 else c.THETA2, cota.medio)

    def _cota(self, p: QPainter, r: QRectF, o: QPointF, avance: QPointF, desde: float,
              lam: float, aparte: float, rotulo: str, color: QColor, medio: int) -> None:
        """Cota de largo λ paralela al haz, por fuera; si no cabe en su medio, no se dibuja."""
        lado = QPointF(-avance.y(), avance.x())          # el lado contrario al nombre del rayo

        def cabe(punto: QPointF) -> bool:
            # a lo ancho siempre cabe: el rayo mide como mucho medio ancho menos 24 px
            if medio == 1:
                return r.top() + BANDA <= punto.y() <= o.y() - 6
            return o.y() + 6 <= punto.y() <= r.bottom() - BANDA

        for signo in (1.0, -1.0):
            a = o + avance * desde + lado * (signo * aparte)
            b = a + avance * lam
            texto = (a + b) * 0.5 + lado * (signo * 11)
            if cabe(a) and cabe(b) and cabe(texto):
                break
        else:
            return
        p.setPen(QPen(color, 1.2))
        p.drawLine(a, b)
        for extremo in (a, b):
            p.drawLine(extremo - lado * 4, extremo + lado * 4)
        fuente = self._fuente(p, 9, negrita=True)
        m = QFontMetricsF(fuente)
        base = QPointF(texto.x() - m.horizontalAdvance(rotulo) / 2, texto.y() + m.ascent() / 2 - 1)
        self._con_halo(p, base, rotulo, fuente, color)

    def _arco(self, p: QPainter, o: QPointF, radio: float, desde: float, grados: float,
              color: QColor, simbolo: str) -> None:
        caja = QRectF(o.x() - radio, o.y() - radio, 2 * radio, 2 * radio)
        p.setPen(QPen(color, 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(caja, int(desde * 16), int(grados * 16))
        # el símbolo dentro del arco si cabe; si el ángulo es pequeño, por fuera
        dentro = grados >= 16
        medio = desde + (grados / 2 if dentro else grados + 9)
        punto = _punto(o, medio, radio * 0.62 if dentro else radio + 4)
        fuente = self._fuente(p, 10, negrita=True)
        m = QFontMetricsF(fuente)
        ancho = m.horizontalAdvance(simbolo)
        x = punto.x() - ancho / 2 if dentro else (
            punto.x() - ancho if punto.x() < o.x() else punto.x())
        self._con_halo(p, QPointF(x, punto.y() + m.ascent() / 2 - 1), simbolo, fuente, color)

    @staticmethod
    def _rayo(p: QPainter, desde: QPointF, hasta: QPointF, color: QColor, ancho: float,
              discontinuo: bool = False) -> None:
        if not discontinuo:
            # un halo ancho y suave debajo: se lee como luz, no como una línea
            brillo = QPen(c.con_alfa(color, color.alphaF() * 0.22), ancho * 3.4)
            brillo.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(brillo)
            p.drawLine(desde, hasta)
        pluma = QPen(color, ancho)
        pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
        if discontinuo:
            pluma.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pluma)
        p.drawLine(desde, hasta)
        dx, dy = hasta.x() - desde.x(), hasta.y() - desde.y()
        largo = math.hypot(dx, dy)
        if largo < 1 or discontinuo:
            return
        ux, uy = dx / largo, dy / largo
        punta = QPointF(desde.x() + ux * largo * 0.6, desde.y() + uy * largo * 0.6)
        tam = 6 + ancho * 1.8
        base = QPointF(punta.x() - ux * tam, punta.y() - uy * tam)
        lado = QPointF(-uy * tam * 0.5, ux * tam * 0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPolygon(QPolygonF([punta, base + lado, base - lado]))

    def _rotulo_rayo(self, p: QPainter, desde: QPointF, hasta: QPointF, texto: str,
                     color: QColor, aparte: float, desde_fin: bool = False) -> None:
        """Nombre del rayo, girado con él, cerca de su extremo libre."""
        f = 0.2 if desde_fin else 0.8
        punto = QPointF(desde.x() + (hasta.x() - desde.x()) * f,
                        desde.y() + (hasta.y() - desde.y()) * f)
        # incidente y refractado bajan hacia la derecha y el reflejado sube: entre -90° y 90°,
        # así que el texto nunca sale boca abajo
        angulo = math.degrees(math.atan2(hasta.y() - desde.y(), hasta.x() - desde.x()))
        fuente = self._fuente(p, 8)
        ancho = QFontMetricsF(fuente).horizontalAdvance(texto)
        p.save()
        p.translate(punto)
        p.rotate(angulo)
        p.setPen(color)
        p.drawText(QPointF(-ancho / 2, -aparte), texto)
        p.restore()

    def _bandas(self, p: QPainter, r: QRectF, n1, n2, t1, t2, reflejada: float,
                firme: bool, total: bool) -> None:
        """Rótulos de cada medio: nombre, índice, velocidad, ángulo y cuánta luz lleva."""
        sol = self._sol
        izq, der = r.left() + 14, r.right() - 14
        for medio, n, theta, color, y in ((1, n1, t1, c.THETA1, r.top() + 10),
                                          (2, n2, t2, c.THETA2, r.bottom() - BANDA + 6)):
            sub = "₁" if medio == 1 else "₂"
            nombre = self._medios[medio - 1] or "—"
            self._escribir(p, izq, y, f"MEDIO {medio} · {nombre.upper()}", c.GRIS, 8, True)
            if n is None:
                datos = f"n{sub} = ?"
            else:
                datos = f"n{sub} = {ex.indice(n)}    v{sub} = {ex.rapidez(n)}"
                if self.frentes:
                    datos += f"    λ{sub} = {ex.num(1 / n, 3)} λ₀"
            self._escribir(p, izq, y + 16, datos, color, 9)

            calculado = sol.ok and sol.incognita.value == f"theta{medio}"
            if theta is None:
                angulo = f"θ{sub}: no hay" if total else f"θ{sub} = ?"
            else:
                angulo = f"θ{sub} = {ex.angulo(theta)}" + ("  (calculado)" if calculado else "")
            self._escribir(p, der, y - 1, angulo, color if firme else c.GRIS, 10, True, derecha=True)
            if firme:
                if medio == 1:
                    luz = f"se refleja el {ex.porcentaje(reflejada)}"
                else:
                    luz = "no pasa luz" if total else f"pasa el {ex.porcentaje(1 - reflejada)}"
                self._escribir(p, der, y + 17, luz, c.RAYO, 8.5, derecha=True)

    def _aviso(self, p: QPainter, r: QRectF, o: QPointF, largo: float) -> None:
        """Recuadro rojo donde faltaría el rayo, con el motivo."""
        sol = self._sol
        titular, detalle = ex.resumen(sol)
        if sol.estado is Estado.REFLEXION_TOTAL:
            centro = _punto(o, 270 + 40, largo * 0.62)          # donde iría el refractado
            texto = "Reflexión total interna\nno pasa luz al medio 2"
        elif sol.incognita is Incognita.THETA1:
            centro = _punto(o, 90 + 40, largo * 0.62)           # donde iría el incidente
            texto = f"{titular}: {detalle}"
        else:
            centro = _punto(o, 270 - 42, largo * 0.62)          # el cuadrante libre
            texto = f"{titular}: {detalle}"
        fuente = self._fuente(p, 9, negrita=True)
        m = QFontMetricsF(fuente)
        ancho = min(230.0, r.width() * 0.42)
        caja = m.boundingRect(QRectF(0, 0, ancho, 400),
                              int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter), texto)
        caja.moveCenter(centro)
        fondo = caja.adjusted(-10, -7, 10, 7)
        # que no se salga del dibujo ni pise las bandas de rótulos
        dx = max(r.left() + 8 - fondo.left(), 0) + min(r.right() - 8 - fondo.right(), 0)
        dy = max(r.top() + BANDA - fondo.top(), 0) + min(r.bottom() - BANDA - fondo.bottom(), 0)
        fondo.translate(dx, dy)
        caja.translate(dx, dy)
        p.setPen(QPen(c.con_alfa(c.CRITICO, 0.5), 1))
        p.setBrush(QColor("#FFF5F5"))
        p.drawRoundedRect(fondo, 6, 6)
        p.setPen(c.CRITICO)
        p.drawText(caja, int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter), texto)

    # --- texto ---------------------------------------------------------------------------

    def _fuente(self, p: QPainter, puntos: float, negrita: bool = False) -> QFont:
        fuente = QFont(self.font())
        fuente.setPointSizeF(puntos)
        fuente.setBold(negrita)
        p.setFont(fuente)
        return fuente

    def _escribir(self, p: QPainter, x: float, y: float, texto: str, color: QColor,
                  puntos: float = 9, negrita: bool = False, derecha: bool = False,
                  halo: bool = False) -> None:
        """Una línea de texto con su parte de arriba en `y`."""
        fuente = self._fuente(p, puntos, negrita)
        m = QFontMetricsF(fuente)
        if derecha:
            x -= m.horizontalAdvance(texto)
        if halo:
            self._con_halo(p, QPointF(x, y + m.ascent()), texto, fuente, color)
        else:
            p.setPen(color)
            p.drawText(QPointF(x, y + m.ascent()), texto)

    @staticmethod
    def _con_halo(p: QPainter, base: QPointF, texto: str, fuente: QFont, color: QColor) -> None:
        """Texto con un borde blanco, para que se lea encima de los rayos y las ondas."""
        camino = QPainterPath()
        camino.addText(base, fuente, texto)
        halo = QPen(c.con_alfa(c.TARJETA, 0.92), 3.2)
        halo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.strokePath(camino, halo)
        p.fillPath(camino, color)
