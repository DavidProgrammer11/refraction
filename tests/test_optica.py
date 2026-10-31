"""El motor físico. Los valores esperados salen de tablas y de cálculos a mano,
no de lo que devuelve el código."""
import math

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from refraccion import optica as o
from refraccion.optica import Datos, Estado, Incognita

indices = st.floats(min_value=1.0, max_value=3.0, allow_nan=False)
angulos = st.floats(min_value=0.0, max_value=90.0, allow_nan=False)


# --- valores de libro -----------------------------------------------------------------

def test_del_aire_al_agua_a_30_grados():
    # sen θ₂ = 0,5 / 1,333 = 0,37509 → θ₂ = 22,03° (cualquier libro de 2.º de bachillerato)
    assert o.refractar(1.0, 1.333, 30) == pytest.approx(22.0305, abs=1e-3)


@pytest.mark.parametrize("n1, n2, critico", [
    (1.333, 1.0, 48.6066),      # agua → aire
    (1.5, 1.0, 41.8103),        # vidrio → aire
    (2.417, 1.0, 24.4406),      # diamante → aire
])
def test_angulo_critico_de_tablas(n1, n2, critico):
    assert o.angulo_critico(n1, n2) == pytest.approx(critico, abs=1e-3)


@pytest.mark.parametrize("n1, n2", [(1.0, 1.333), (1.5, 1.5), (1.0003, 1.0003)])
def test_sin_angulo_critico_si_el_segundo_medio_no_es_menos_denso(n1, n2):
    assert o.angulo_critico(n1, n2) is None


def test_angulo_de_brewster_aire_vidrio():
    assert o.angulo_brewster(1.0, 1.5) == pytest.approx(56.3099, abs=1e-3)   # arctan 1,5


def test_velocidad_en_el_vacio_y_en_el_agua():
    assert o.velocidad(1.0) == 299_792.458
    assert o.velocidad(1.333) == pytest.approx(224_900.568, abs=1e-2)


@pytest.mark.parametrize("n2, reflejada", [(1.5, 0.04), (1.333, 0.020373)])
def test_reflexion_con_incidencia_normal(n2, reflejada):
    # R = ((n₁ - n₂) / (n₁ + n₂))²: 4 % en el vidrio, 2,04 % en el agua
    f = o.fresnel(1.0, n2, 0)
    assert f.r == pytest.approx(reflejada, abs=1e-6)
    assert f.rs == pytest.approx(f.rp)
    assert f.t == pytest.approx(1 - reflejada, abs=1e-6)


def test_en_el_angulo_de_brewster_la_luz_p_no_se_refleja():
    brewster = o.angulo_brewster(1.0, 1.5)
    f = o.fresnel(1.0, 1.5, brewster)
    assert f.rp == pytest.approx(0, abs=1e-12)
    # Rs = sen²(θ₁ - θ₂) porque θ₁ + θ₂ = 90°: sen²(56,31° - 33,69°) = 0,1479
    assert f.rs == pytest.approx(0.147929, abs=1e-5)


def test_con_incidencia_rasante_se_refleja_todo():
    assert o.fresnel(1.0, 1.5, 90).r == pytest.approx(1, abs=1e-9)


def test_reflexion_total_refleja_el_cien_por_cien():
    f = o.fresnel(1.5, 1.0, 60)
    assert (f.rs, f.rp, f.r, f.t) == (1.0, 1.0, 1.0, 0.0)


def test_medios_iguales_no_reflejan_ni_siquiera_rasante():
    for theta in (0, 45, 90):
        assert o.fresnel(1.333, 1.333, theta).r == 0


# --- límites ---------------------------------------------------------------------------

def test_incidencia_perpendicular_no_se_desvia():
    assert o.refractar(1.0, 2.417, 0) == 0


def test_incidencia_rasante_sale_por_el_angulo_critico_del_reves():
    # de 90° en el aire al agua: θ₂ = arcsen (1 / 1,333), el ángulo límite
    assert o.refractar(1.0, 1.333, 90) == pytest.approx(48.6066, abs=1e-3)


def test_justo_en_el_angulo_critico_sale_rasante_y_una_centesima_despues_no_sale():
    critico = o.angulo_critico(1.5, 1.0)
    assert o.refractar(1.5, 1.0, critico) == pytest.approx(90, abs=1e-4)
    assert o.refractar(1.5, 1.0, critico + 0.01) is None


@given(n1=st.floats(1.01, 3.0), proporcion=st.floats(0.3, 0.99))
@settings(max_examples=300)
def test_el_angulo_critico_exacto_no_se_pierde_por_redondeo(n1, proporcion):
    n2 = n1 * proporcion
    critico = o.angulo_critico(n1, n2)
    assert o.refractar(n1, n2, critico) == pytest.approx(90, abs=1e-3)


# --- propiedades -------------------------------------------------------------------------

@given(n1=indices, n2=indices, theta1=angulos)
@settings(max_examples=400)
def test_se_conserva_n_por_seno_o_hay_reflexion_total(n1, n2, theta1):
    theta2 = o.refractar(n1, n2, theta1)
    lado_izquierdo = n1 * math.sin(math.radians(theta1))
    if theta2 is None:
        assert lado_izquierdo > n2                        # reflexión total: no hay seno posible
    else:
        assert 0 <= theta2 <= 90
        assert lado_izquierdo == pytest.approx(n2 * math.sin(math.radians(theta2)), abs=1e-9)


@given(n1=indices, n2=indices, theta1=angulos)
@settings(max_examples=300)
def test_el_rayo_se_acerca_a_la_normal_si_entra_en_un_medio_mas_denso(n1, n2, theta1):
    theta2 = o.refractar(n1, n2, theta1)
    assume(theta2 is not None)
    if n2 > n1:
        assert theta2 <= theta1 + 1e-9
    elif n2 < n1:
        assert theta2 >= theta1 - 1e-9


@given(n1=indices, n2=indices, theta1=st.floats(0, 85))
@settings(max_examples=300)
def test_la_luz_hace_el_mismo_camino_al_reves(n1, n2, theta1):
    theta2 = o.refractar(n1, n2, theta1)
    assume(theta2 is not None and theta2 <= 85)          # lejos de 90°, donde arcsen se dispara
    assert o.incidente(n1, n2, theta2) == pytest.approx(theta1, abs=1e-7)


@given(n1=st.floats(1.0, 2.5), n2=st.floats(1.0, 2.5), theta1=st.floats(1, 80))
@settings(max_examples=300)
def test_despejar_cualquier_incognita_devuelve_el_valor_original(n1, n2, theta1):
    theta2 = o.refractar(n1, n2, theta1)
    assume(theta2 is not None and 1 <= theta2 <= 80)
    completos = Datos(n1, n2, theta1, theta2)
    for incognita in Incognita:
        # la incógnita entra como NaN: no se mira y no debe estorbar
        sol = o.resolver(completos.con(incognita, math.nan), incognita)
        assert sol.estado is Estado.OK
        assert sol.valor == pytest.approx(completos.valor(incognita), rel=1e-7)
        resuelta = sol.completa()
        for campo in Incognita:
            assert resuelta.valor(campo) == pytest.approx(completos.valor(campo), rel=1e-7)


@given(n1=indices, n2=indices, theta1=angulos)
@settings(max_examples=300)
def test_fresnel_reflejado_mas_transmitido_es_uno_y_s_refleja_mas_que_p(n1, n2, theta1):
    f = o.fresnel(n1, n2, theta1)
    assert 0 <= f.rp <= f.rs + 1e-12 <= 1 + 1e-12
    assert f.r + f.t == pytest.approx(1)


@given(n1=indices, n2=indices, theta1=st.floats(0, 89))
@settings(max_examples=300)
def test_se_refleja_lo_mismo_por_los_dos_lados_de_la_superficie(n1, n2, theta1):
    # relaciones de Stokes: R(1→2, θ₁) = R(2→1, θ₂)
    theta2 = o.refractar(n1, n2, theta1)
    assume(theta2 is not None and theta2 < 89.9)
    ida, vuelta = o.fresnel(n1, n2, theta1), o.fresnel(n2, n1, theta2)
    assert ida.rs == pytest.approx(vuelta.rs, abs=1e-9)
    assert ida.rp == pytest.approx(vuelta.rp, abs=1e-9)


# --- resolver: casos sin solución --------------------------------------------------------

def test_resolver_theta2_con_reflexion_total():
    sol = o.resolver(Datos(1.5, 1.0, 60, 0), Incognita.THETA2)
    assert sol.estado is Estado.REFLEXION_TOTAL
    assert sol.valor is None and not sol.ok and sol.completa() is None


def test_resolver_theta1_imposible_si_theta2_pasa_del_limite():
    # del vacío al vidrio 1,5 los refractados no pasan de arcsen (1/1,5) = 41,81°
    assert o.resolver(Datos(1.0, 1.5, 0, 50), Incognita.THETA1).estado is Estado.SIN_SOLUCION
    en_el_limite = o.resolver(Datos(1.0, 1.5, 0, 41.8103), Incognita.THETA1)
    assert en_el_limite.valor == pytest.approx(90, abs=0.05)


@pytest.mark.parametrize("incognita", [Incognita.N1, Incognita.N2])
def test_indice_indeterminado_con_los_dos_angulos_a_cero(incognita):
    sol = o.resolver(Datos(1.0, 1.5, 0, 0), incognita)
    assert sol.estado is Estado.INDETERMINADA and sol.valor is None


@pytest.mark.parametrize("incognita, theta1, theta2", [
    (Incognita.N1, 0, 20),       # dividir entre sen θ₁ = 0
    (Incognita.N1, 20, 0),       # saldría n₁ = 0
    (Incognita.N2, 20, 0),       # dividir entre sen θ₂ = 0
    (Incognita.N2, 0, 20),       # saldría n₂ = 0
])
def test_indice_sin_solucion_si_solo_un_angulo_es_cero(incognita, theta1, theta2):
    assert o.resolver(Datos(1.0, 1.5, theta1, theta2), incognita).estado is Estado.SIN_SOLUCION


def test_medir_el_indice_de_un_vidrio():
    # 1,0003 · sen 45° / sen 27,79° = 0,70732 / 0,46625 = 1,5170
    sol = o.resolver(Datos(1.0003, 0, 45, 27.79), Incognita.N2)
    assert sol.ok and sol.valor == pytest.approx(1.5170, abs=2e-4)


# --- validación ----------------------------------------------------------------------------

@pytest.mark.parametrize("datos, incognita, mensaje", [
    (Datos(0, 1.5, 30, 0), Incognita.THETA2, "n₁ tiene que ser mayor que 0"),
    (Datos(1, -1.5, 30, 0), Incognita.THETA2, "n₂ tiene que ser mayor que 0"),
    (Datos(math.nan, 1.5, 30, 0), Incognita.THETA2, "n₁ no es un número"),
    (Datos(1, math.inf, 30, 0), Incognita.THETA2, "n₂ no es un número"),
    (Datos(1, 1.5, -0.01, 0), Incognita.THETA2, "θ₁ tiene que estar entre 0° y 90°"),
    (Datos(1, 1.5, 90.01, 0), Incognita.THETA2, "θ₁ tiene que estar entre 0° y 90°"),
    (Datos(1, 1.5, 0, math.nan), Incognita.N1, "θ₂ no es un número"),
])
def test_datos_invalidos_dan_un_error_claro(datos, incognita, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        o.resolver(datos, incognita)


def test_la_incognita_no_se_valida():
    assert o.resolver(Datos(-5, 1.5, 30, 22), Incognita.N1).ok


@pytest.mark.parametrize("theta", [0.0, 90.0])
def test_los_extremos_del_rango_de_angulos_valen(theta):
    assert o.resolver(Datos(1.0, 1.5, theta, 0), Incognita.THETA2).ok


# --- curvas --------------------------------------------------------------------------------

def test_curva_hacia_un_medio_mas_denso_llega_a_90_y_sube_siempre():
    puntos = o.curva_refraccion(1.0, 1.5)
    assert len(puntos) == 361
    assert puntos[0] == (0, 0)
    assert puntos[-1][0] == 90 and puntos[-1][1] == pytest.approx(41.8103, abs=1e-3)
    ys = [y for _, y in puntos]
    assert all(a < b for a, b in zip(ys, ys[1:]))


def test_curva_hacia_un_medio_menos_denso_acaba_en_el_angulo_critico():
    puntos = o.curva_refraccion(1.5, 1.0)
    critico = o.angulo_critico(1.5, 1.0)
    assert puntos[-1][0] == pytest.approx(critico)
    assert puntos[-1][1] == pytest.approx(90, abs=1e-4)
    assert all(y is not None for _, y in puntos)


def test_curva_de_fresnel_incluye_el_angulo_critico_y_luego_todo_se_refleja():
    critico = o.angulo_critico(1.5, 1.0)
    curva = o.curva_fresnel(1.5, 1.0)
    xs = [x for x, _ in curva]
    assert critico in xs and xs == sorted(xs)
    assert all(f.r == 1 for x, f in curva if x >= critico)
    assert all(f.r < 1 for x, f in curva if x < critico - 1)


def test_curva_de_fresnel_sin_angulo_critico_tiene_los_puntos_justos():
    assert len(o.curva_fresnel(1.0, 1.5)) == 361


def test_incognita_sabe_si_es_angulo_y_su_simbolo():
    assert [i.simbolo for i in Incognita] == ["n₁", "n₂", "θ₁", "θ₂"]
    assert [i.es_angulo for i in Incognita] == [False, False, True, True]


def test_invariante_es_n_por_seno():
    assert o.invariante(2.0, 30) == pytest.approx(1.0)
