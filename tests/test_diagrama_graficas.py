"""Lo que se dibuja: se leen píxeles del diagrama y se comprueba que las gráficas
y el paso a paso dicen lo que dice la física."""
import math

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from refraccion.optica import Datos, Incognita, angulo_critico, refractar, resolver
from refraccion.ui import colores as c
from refraccion.ui.diagrama import Diagrama
from refraccion.ui.grafica import (
    Contenido, LineaV, Serie, contenido_fresnel, contenido_refraccion, grafica_fresnel,
    grafica_refraccion,
)
from refraccion.ui.paso_a_paso import PasoAPaso, colorear, formula, html

ANCHO, ALTO = 760, 430


def dibujar(qapp, datos, incognita, frentes=False, fase=0.0) -> tuple[QImage, QPointF, float]:
    d = Diagrama()
    d.resize(ANCHO, ALTO)
    d.set_frentes(frentes)
    d.fase = fase
    d.mostrar(resolver(datos, incognita), "uno", "dos")
    o, largo = Diagrama.geometria(QRectF(0, 0, ANCHO, ALTO))
    return d.imagen(1.0), o, largo


def es_luz(img: QImage, x: float, y: float, radio: int = 2) -> bool:
    """¿Hay naranja de rayo (#E8590C) cerca de (x, y)?"""
    for dx in range(-radio, radio + 1):
        for dy in range(-radio, radio + 1):
            color = img.pixelColor(round(x) + dx, round(y) + dy)
            if color.red() > 190 and 50 < color.green() < 150 and color.blue() < 90:
                return True
    return False


def hacia(o: QPointF, largo: float, grados_mat: float, fraccion: float) -> tuple[float, float]:
    a = math.radians(grados_mat)
    return o.x() + largo * fraccion * math.cos(a), o.y() - largo * fraccion * math.sin(a)


# --- el diagrama --------------------------------------------------------------------------------

def test_se_dibujan_el_rayo_incidente_y_el_refractado_en_su_angulo(qapp):
    theta2 = refractar(1.0003, 1.333, 40)
    img, o, largo = dibujar(qapp, Datos(1.0003, 1.333, 40, 0), Incognita.THETA2)
    assert es_luz(img, *hacia(o, largo, 90 + 40, 0.8))            # incidente, arriba a la izquierda
    assert es_luz(img, *hacia(o, largo, 270 + theta2, 0.8))       # refractado a θ₂ de la normal
    assert not es_luz(img, *hacia(o, largo, 270 + 40, 0.8))       # no sigue recto: se ha doblado
    assert not es_luz(img, *hacia(o, largo, 90 - 40, 0.8))        # el reflejo (2 %) es tenue


def test_con_reflexion_total_no_hay_refractado_y_el_reflejo_es_fuerte(qapp):
    img, o, largo = dibujar(qapp, Datos(1.5, 1.0, 60, 0), Incognita.THETA2)
    assert es_luz(img, *hacia(o, largo, 90 - 60, 0.8))            # reflejado entero
    for grados in range(275, 360, 10):                              # nada en todo el medio 2
        assert not es_luz(img, *hacia(o, largo, grados, 0.7))


def test_la_zona_de_reflexion_total_se_sombrea_en_rojo(qapp):
    critico = angulo_critico(1.5, 1.0)
    img, o, largo = dibujar(qapp, Datos(1.5, 1.0, 30, 0), Incognita.THETA2)
    dentro = img.pixelColor(*map(round, hacia(o, largo, 90 + (critico + 90) / 2, 0.5)))
    fuera = img.pixelColor(*map(round, hacia(o, largo, 90 + critico / 2, 0.5)))
    assert dentro.red() - dentro.blue() > fuera.red() - fuera.blue()   # más rojizo pasado θc


def contar_frentes(img: QImage, o: QPointF, largo: float, theta: float, medio: int) -> int:
    """Frentes de onda que corta una línea paralela al rayo, dentro del haz."""
    a = math.radians(theta)
    if medio == 1:
        avance, lado = (-math.sin(a), -math.cos(a)), (-math.cos(a), math.sin(a))
    else:
        avance, lado = (math.sin(a), math.cos(a)), (-math.cos(a), math.sin(a))
    cortes, antes = 0, False
    pasos = int(largo * 0.55 * 2)
    for i in range(pasos):
        s = largo * 0.35 + i * 0.5
        x = o.x() + s * avance[0] + 0.07 * largo * lado[0]
        y = o.y() + s * avance[1] + 0.07 * largo * lado[1]
        color = img.pixelColor(round(x), round(y))
        ahora = color.red() > 200 and color.green() < 185 and color.blue() < 150
        cortes += ahora and not antes
        antes = ahora
    return cortes


def test_los_frentes_de_onda_se_aprietan_segun_el_indice(qapp):
    # λ = λ₀ / n: en un medio con n = 2 caben el doble de frentes que en el vacío
    theta2 = refractar(1.0, 2.0, 30)
    img, o, largo = dibujar(qapp, Datos(1.0, 2.0, 30, 0), Incognita.THETA2, frentes=True)
    arriba = contar_frentes(img, o, largo, 30, 1)
    abajo = contar_frentes(img, o, largo, theta2, 2)
    assert arriba >= 3
    assert 1.6 <= abajo / arriba <= 2.5


def test_los_frentes_avanzan_con_la_animacion(qapp):
    quieto, _, _ = dibujar(qapp, Datos(1.0, 1.5, 30, 0), Incognita.THETA2, frentes=True, fase=0.0)
    luego, _, _ = dibujar(qapp, Datos(1.0, 1.5, 30, 0), Incognita.THETA2, frentes=True, fase=0.5)
    sin_frentes, _, _ = dibujar(qapp, Datos(1.0, 1.5, 30, 0), Incognita.THETA2)
    assert quieto != luego and quieto != sin_frentes


@pytest.mark.parametrize("datos, incognita", [
    (Datos(1.0, 1.5, 0, 50), Incognita.THETA1),        # θ₁ imposible: zona prohibida en rojo
    (Datos(1.0, 1.5, 0, 0), Incognita.N2),             # indeterminado
    (Datos(1.0, 1.5, 30, 0), Incognita.N1),            # sin solución, n₁ desconocido
    (Datos(1.4, 1.4, 90, 0), Incognita.THETA2),        # medios iguales y rasante
    (Datos(1.0, 1.5, 89, 0), Incognita.THETA2),        # haz muy tendido
])
def test_los_casos_raros_se_dibujan_sin_errores(qapp, datos, incognita):
    img, _, _ = dibujar(qapp, datos, incognita, frentes=True)
    assert not img.isNull()


def test_sin_solucion_los_rayos_dados_salen_en_gris_y_discontinuos(qapp):
    img, o, largo = dibujar(qapp, Datos(1.0, 1.5, 0, 50), Incognita.THETA1)
    assert not es_luz(img, *hacia(o, largo, 270 + 50, 0.8))       # no es luz «de verdad»
    gris = img.pixelColor(*map(round, hacia(o, largo, 270 + 50, 0.62)))
    assert abs(gris.red() - gris.blue()) < 40


def test_un_diagrama_sin_solucion_todavia_no_falla(qapp):
    d = Diagrama()
    d.resize(300, 200)
    assert not d.imagen().isNull() and d.solucion is None


def test_arrastrar_no_hace_nada_si_no_hay_nada_que_arrastrar(qtbot):
    d = Diagrama()
    qtbot.addWidget(d)
    d.resize(ANCHO, ALTO)
    d.mostrar(resolver(Datos(), Incognita.THETA2), "a", "b")
    d.set_arrastrables(False, False)
    with qtbot.assertNotEmitted(d.anguloArrastrado):
        qtbot.mousePress(d, Qt.MouseButton.LeftButton, pos=QPoint(100, 50))
        qtbot.mouseMove(d, pos=QPoint(120, 60))
    assert d.cursor().shape() == Qt.CursorShape.ArrowCursor


def test_dejar_de_poder_arrastrar_a_medias_corta_el_arrastre(qtbot):
    d = Diagrama()
    qtbot.addWidget(d)
    d.resize(ANCHO, ALTO)
    d.mostrar(resolver(Datos(), Incognita.THETA2), "a", "b")
    with qtbot.waitSignal(d.anguloArrastrado):
        qtbot.mousePress(d, Qt.MouseButton.LeftButton, pos=QPoint(300, 100))
    d.set_arrastrables(False, True)
    with qtbot.assertNotEmitted(d.anguloArrastrado):
        qtbot.mouseMove(d, pos=QPoint(320, 120))


# --- las gráficas ---------------------------------------------------------------------------------

def test_curva_de_refraccion_con_angulo_critico():
    cont = contenido_refraccion(resolver(Datos(1.5, 1.0, 30, 0), Incognita.THETA2))
    critico = angulo_critico(1.5, 1.0)
    assert [(z.x0, z.x1) for z in cont.zonas] == [(critico, 90)]
    assert [l.etiqueta for l in cont.lineas] == ["θc = 41,8° · reflexión total"]
    marca = cont.marcas[0]
    # 1,5 · sen 30° = 0,75 → θ₂ = 48,59°
    assert (marca.x, marca.y) == pytest.approx((30, 48.5904), abs=1e-3)
    assert cont.lector(50) == [("θ₁ = 50,0°", c.THETA1), ("reflexión total", c.CRITICO)]
    # a 20°: arcsen (1,5 · 0,34202) = 30,87°, se desvía 10,87°
    assert cont.lector(20) == [("θ₁ = 20,0°", c.THETA1), ("θ₂ = 30,9°", c.THETA2),
                               ("se desvía 10,9°", c.GRIS)]


def test_con_medios_iguales_la_lectura_no_habla_de_desvio():
    cont = contenido_refraccion(resolver(Datos(1.2, 1.2, 30, 0), Incognita.THETA2))
    assert len(cont.lector(45)) == 2


def test_en_reflexion_total_se_marca_theta1_con_una_linea():
    cont = contenido_refraccion(resolver(Datos(1.5, 1.0, 60, 0), Incognita.THETA2))
    assert cont.marcas == []
    assert "θ₁ = 60,0°" in [l.etiqueta for l in cont.lineas]


def test_sin_los_dos_indices_no_hay_curva():
    sol = resolver(Datos(1.0, 1.5, 0, 0), Incognita.N2)           # indeterminado
    assert contenido_refraccion(sol).mensaje and contenido_refraccion(sol).series == []
    assert contenido_fresnel(sol).mensaje


def test_si_se_calcula_un_indice_la_curva_usa_el_calculado():
    sol = resolver(Datos(1.0, 0, 30, math.degrees(math.asin(1 / 3))), Incognita.N2)   # n₂ = 1,5
    assert "n₂ = 1,500" in contenido_refraccion(sol).series[1].etiqueta


def test_fresnel_marca_brewster_y_lo_que_se_refleja():
    cont = contenido_fresnel(resolver(Datos(1.0, 1.5, 0, 0), Incognita.THETA2))
    assert [l.etiqueta for l in cont.lineas] == ["Brewster 56,3°"]
    r, t = cont.marcas
    assert (r.y, t.y) == pytest.approx((4.0, 96.0))                 # 4 % con incidencia normal
    assert [texto for texto, _ in cont.lector(0)][1:3] == ["se refleja 4,0\u00a0%", "pasa 96,0\u00a0%"]


def test_fresnel_entre_medios_iguales_no_tiene_brewster():
    cont = contenido_fresnel(resolver(Datos(1.3, 1.3, 10, 0), Incognita.THETA2))
    assert cont.lineas == []


def test_fresnel_hacia_un_medio_menos_denso_marca_el_angulo_critico():
    cont = contenido_fresnel(resolver(Datos(1.5, 1.0, 10, 0), Incognita.THETA2))
    assert [l.etiqueta for l in cont.lineas] == ["Brewster 33,7°", "θc = 41,8°"]


def test_la_grafica_se_pinta_y_lee_donde_esta_el_raton(qtbot):
    g = grafica_refraccion()
    qtbot.addWidget(g)
    g.resize(640, 300)
    g.mostrar(contenido_refraccion(resolver(Datos(1.0, 1.5, 30, 0), Incognita.THETA2)))
    g.show()
    centro = g.a_pantalla(45, 10)
    qtbot.mouseMove(g, pos=QPoint(round(centro.x()), round(centro.y())))
    assert g.raton_x == pytest.approx(45, abs=0.3)
    assert not g.grab().isNull()
    qtbot.mouseMove(g, pos=QPoint(2, 2))                             # fuera de los ejes
    assert g.raton_x is None


def test_una_grafica_diminuta_o_con_mensaje_no_falla(qtbot):
    g = grafica_fresnel()
    qtbot.addWidget(g)
    g.resize(60, 40)
    assert not g.grab().isNull()
    g.resize(400, 250)
    g.mostrar(contenido_fresnel(resolver(Datos(1.0, 1.5, 0, 0), Incognita.N2)))
    assert not g.grab().isNull()


# --- el paso a paso en HTML -------------------------------------------------------------------------

def test_colorear_escapa_el_html_y_pinta_los_simbolos():
    resultado = colorear("<b>n₁ · sen θ₁</b> & θc")
    assert "<b>" not in resultado and "&lt;b&gt;" in resultado and "&amp;" in resultado
    assert f'color:{c.THETA1.name()}; font-weight:600;">θ₁</span>' in resultado
    assert f'color:{c.THETA1.name()}; font-weight:600;">n₁</span>' in resultado
    assert f'color:{c.CRITICO.name()}; font-weight:600;">θc</span>' in resultado


def test_el_html_numera_los_pasos_y_marca_los_avisos():
    documento = html(resolver(Datos(1.5, 1.0, 60, 0), Incognita.THETA2))
    assert "Buscamos" in documento and "Datos:" in documento
    assert documento.count('bgcolor="#') == 4                      # 4 pasos: ley, despeje, datos, aviso
    assert 'bgcolor="#FFF5F5"' in documento                          # el aviso, en rojo claro


def test_el_paso_a_paso_no_salta_arriba_al_recalcular(qtbot):
    p = PasoAPaso()
    qtbot.addWidget(p)
    p.resize(400, 150)
    p.show()
    sol = resolver(Datos(1.0, 1.333, 30, 0), Incognita.THETA2)
    p.mostrar(sol)
    barra = p.verticalScrollBar()
    assert barra.maximum() > 0
    barra.setValue(barra.maximum() // 2)
    posicion = barra.value()
    p.mostrar(resolver(Datos(1.0, 1.333, 31, 0), Incognita.THETA2))
    assert barra.value() == posicion


def test_casos_limite_de_la_grafica_generica(qtbot):
    g = grafica_refraccion()
    qtbot.addWidget(g)
    g.resize(330, 220)                                            # estrecha: la leyenda no cabe entera
    largas = [Serie([(0, 0), (90, 90)], c.RAYO, etiqueta=f"una etiqueta bastante larga {i}")
              for i in range(4)]
    g.mostrar(Contenido(
        series=[Serie([], c.GRIS), Serie([(10, 10)], c.GRIS), *largas, Serie([(0, 5), (90, 5)], c.GRIS)],
        lineas=[LineaV(30, c.GRIS), LineaV(89, c.CRITICO, "pegada al borde"),
                LineaV(88, c.BREWSTER, "otra encima")],
        lector=lambda x: [] if x < 45 else [("lectura", c.TEXTO)]))
    g.show()
    for x in (20, 88):                                             # sin lectura y pegado a la derecha
        punto = g.a_pantalla(x, 45)
        qtbot.mouseMove(g, pos=QPoint(round(punto.x()), round(punto.y())))
        assert not g.grab().isNull()
    QApplication.sendEvent(g, QEvent(QEvent.Type.Leave))
    assert g.raton_x is None


def test_sin_theta1_valido_la_curva_no_marca_nada():
    sol = resolver(Datos(1.0, 1.5, 0, 50), Incognita.THETA1)      # θ₁ imposible
    assert contenido_refraccion(sol).marcas == []
    assert contenido_fresnel(sol).marcas == []


def test_pasar_el_raton_por_el_medio_que_se_arrastra_pone_la_mano(qtbot):
    d = Diagrama()
    qtbot.addWidget(d)
    d.resize(ANCHO, ALTO)
    d.mostrar(resolver(Datos(), Incognita.THETA2), "a", "b")
    d.show()
    qtbot.mouseMove(d, pos=QPoint(200, 80))                       # medio 1: θ₁ es un dato
    assert d.cursor().shape() == Qt.CursorShape.OpenHandCursor
    qtbot.mouseMove(d, pos=QPoint(500, 380))                      # medio 2: θ₂ es la incógnita
    assert d.cursor().shape() == Qt.CursorShape.ArrowCursor
    qtbot.mouseRelease(d, Qt.MouseButton.LeftButton, pos=QPoint(500, 380))   # soltar sin arrastrar


def test_una_division_se_escribe_como_fraccion():
    documento = formula("sen θ₂ = n₁ · sen θ₁ / n₂")
    assert "border-bottom:1px solid" in documento                  # la raya de la fracción
    numerador = documento.split("border-bottom")[1]
    assert numerador.index("sen") < numerador.index("</td>")        # el numerador va encima
    assert ">θ₂</span> =</td>" in documento


@pytest.mark.parametrize("texto", [
    "n₁ · sen θ₁ = n₂ · sen θ₂",                                    # sin división
    "θ₂ = arcsen 0,3751 = 22,03°",                                   # dos signos «=»
    "n₁ · sen θ₁ = 1,000 · 0,5000 = 0,5000",
])
def test_lo_que_no_es_una_division_va_en_una_linea(texto):
    assert "border-bottom" not in formula(texto)


def test_la_raya_de_la_fraccion_se_dibuja_de_verdad(qapp):
    from PySide6.QtGui import QColor, QFont, QPainter, QTextDocument

    doc = QTextDocument()
    doc.setDefaultFont(QFont("Segoe UI", 10))
    doc.setHtml(formula("sen θ₂ = 1,000 · sen 30,00° / 1,333"))
    imagen = QImage(400, 90, QImage.Format.Format_RGB32)
    imagen.fill(QColor("white"))
    pintor = QPainter(imagen)
    doc.drawContents(pintor)
    pintor.end()

    def tramo_mas_largo(y):
        mejor = seguidos = 0
        for x in range(400):
            seguidos = seguidos + 1 if imagen.pixelColor(x, y).lightness() < 120 else 0
            mejor = max(mejor, seguidos)
        return mejor

    # la raya es un tramo oscuro seguido; las letras, aunque sumen muchos píxeles, no
    # (medido: unos 140 px con fracción frente a menos de 20 con la fórmula en línea)
    assert max(tramo_mas_largo(y) for y in range(90)) > 80


def test_las_cotas_de_lambda_salen_con_las_ondas_y_no_sin_ellas(qapp):
    from refraccion.ui.diagrama import anchos_de_haz

    def azul_cerca(img, punto, radio=5):
        return any(abs(img.pixelColor(round(punto.x()) + dx, round(punto.y()) + dy).red() - 0) < 60
                   and img.pixelColor(round(punto.x()) + dx, round(punto.y()) + dy).blue() > 150
                   and img.pixelColor(round(punto.x()) + dx, round(punto.y()) + dy).green() < 150
                   for dx in range(-radio, radio + 1) for dy in range(-radio, radio + 1))

    datos = Datos(1.0, 1.333, 40, 0)
    con, o, largo = dibujar(qapp, datos, Incognita.THETA2, frentes=True)
    sin, _, _ = dibujar(qapp, datos, Incognita.THETA2, frentes=False)
    _, ancho1, _ = anchos_de_haz(largo, 40, refractar(1.0, 1.333, 40))
    a = math.radians(40)
    avance, lado = QPointF(math.sin(a), math.cos(a)), QPointF(-math.cos(a), math.sin(a))
    # la raya de la cota de λ₁: a 0,8 del largo antes de la superficie y por fuera del haz
    cota = o + avance * (-0.8 * largo + 0.5 * largo / 6.0) + lado * (ancho1 + 9)
    assert azul_cerca(con, cota)
    assert not azul_cerca(sin, cota)


def test_con_incidencia_rasante_la_cota_pasa_al_otro_lado_sin_fallar(qapp):
    # a 88° el lado de fuera del haz cae en el medio 2: la cota tiene que ir por el otro
    d = Diagrama()
    d.resize(320, 300)
    d.mostrar(resolver(Datos(1.0, 1.5, 88, 0), Incognita.THETA2), "a", "b")
    assert not d.imagen(1.0).isNull()


def test_las_bandas_de_la_onda_van_con_sus_frentes(qapp):
    # con la fase a medio periodo: en una cresta hay naranja y entre dos crestas, casi blanco
    img, o, largo = dibujar(qapp, Datos(1.0, 1.333, 45, 0), Incognita.THETA2, frentes=True, fase=0.5)
    lam = largo / 6.0                                              # λ₁ con n₁ = 1
    a = math.radians(45)
    avance, lado = QPointF(math.sin(a), math.cos(a)), QPointF(-math.cos(a), math.sin(a))

    def color(s):
        p = o + avance * s + lado * (0.07 * largo)
        return img.pixelColor(round(p.x()), round(p.y()))

    cresta, valle = color(-2.5 * lam), color(-3.0 * lam)           # crestas en s = λ (m + 0,5)
    assert cresta.green() < 200                                    # naranja: línea y banda
    assert valle.green() > 230                                     # casi el fondo


@pytest.mark.parametrize("n1, n2", [(1.0, 1.333), (1.0, 2.417), (1.5, 1.0003)])
def test_las_cotas_miden_lo_mismo_que_la_separacion_de_los_frentes(n1, n2):
    from refraccion.ui.diagrama import cotas_lambda, longitud_de_onda

    largo = 150.0
    theta2 = refractar(n1, n2, 20)
    l1, l2 = cotas_lambda(largo, n1, n2, 20, theta2)
    assert (l1.rotulo, l2.rotulo, l1.medio, l2.medio) == ("λ₁", "λ₂", 1, 2)
    assert l1.largo == longitud_de_onda(largo, n1) == pytest.approx(25 / n1)   # λ₀ = largo / 6
    assert l2.largo / l1.largo == pytest.approx(n1 / n2)                         # λ₂ / λ₁ = n₁ / n₂
    assert l1.desde < 0 < l2.desde                                               # cada una en su medio


def test_sin_refractado_solo_hay_cota_de_lambda1():
    from refraccion.ui.diagrama import cotas_lambda

    assert [c.rotulo for c in cotas_lambda(150.0, 1.5, 1.0, 60, None)] == ["λ₁"]


@pytest.mark.parametrize("theta1, theta2", [(60, 40), (30, 22), (0, 0), (45, 70)])
def test_el_haz_refractado_cambia_de_ancho_como_en_la_realidad(theta1, theta2):
    # los dos haces comparten la huella en la superficie: anchos en razón cos θ₂ / cos θ₁
    from refraccion.ui.diagrama import SEMIANCHO, anchos_de_haz

    huella, ancho1, ancho2 = anchos_de_haz(100.0, theta1, theta2)
    assert ancho1 == pytest.approx(100.0 * SEMIANCHO)
    assert ancho2 / ancho1 == pytest.approx(math.cos(math.radians(theta2)) / math.cos(math.radians(theta1)))
    assert huella == pytest.approx(ancho1 / math.cos(math.radians(theta1)))


def test_con_incidencia_casi_rasante_la_huella_se_limita():
    from refraccion.ui.diagrama import SEMIANCHO, anchos_de_haz

    huella, ancho1, _ = anchos_de_haz(100.0, 89.0, None)
    assert huella == pytest.approx(100.0 * SEMIANCHO / 0.2)       # no se va al infinito
    assert ancho1 < 100.0 * SEMIANCHO
