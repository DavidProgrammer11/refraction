"""El paso a paso: números en español y cuentas que coinciden con las hechas a mano."""
import math

import pytest

from refraccion import explicacion as ex
from refraccion.optica import Datos, Estado, Incognita, Solucion, resolver

MILES = "\u202f"        # espacio fino de millares
FIJO = "\u00a0"         # espacio que no parte «2,1 %»


def titulos(sol):
    return [p.titulo for p in ex.explicar(sol)]


def paso(sol, titulo):
    return next(p for p in ex.explicar(sol) if p.titulo == titulo)


def todo_el_texto(sol):
    return "\n".join(linea for p in ex.explicar(sol) for linea in (*p.formulas, *p.texto))


# --- números ------------------------------------------------------------------------------

@pytest.mark.parametrize("x, decimales, esperado", [
    (1234.5, 2, "1234,50"),                    # cuatro cifras: sin espacio (RAE)
    (12345.678, 2, f"12{MILES}345,68"),
    (299792.458, 0, f"299{MILES}792"),
    (-3.14159, 2, "-3,14"),
    (-0.0001, 2, "0,00"),                      # nunca «-0,00»
    (-0.004, 2, "0,00"),
    (0.5, 4, "0,5000"),
    (9999.999, 2, f"10{MILES}000,00"),         # al redondear pasa a cinco cifras
])
def test_numeros_con_coma_decimal_y_espacio_de_millares(x, decimales, esperado):
    assert ex.num(x, decimales) == esperado


@pytest.mark.parametrize("n, esperado", [
    (1.0003, "1,0003"), (1.5, "1,500"), (2.417, "2,417"), (1.33333, "1,3333"),
    (0.99999531, "1,000"), (1.0, "1,000"),
])
def test_indices_con_tres_o_cuatro_decimales(n, esperado):
    assert ex.indice(n) == esperado


def test_angulos_porcentajes_y_velocidades():
    assert ex.angulo(22.0305) == "22,03°"
    assert ex.porcentaje(0.021437) == f"2,1{FIJO}%"
    assert ex.rapidez(1.333) == f"224{MILES}901{FIJO}km/s"          # 299 792,458 / 1,333
    assert ex.formatear(Incognita.THETA1, 30) == "30,00°"
    assert ex.formatear(Incognita.N2, 1.333) == "1,333"


# --- θ₂ con solución: aire → agua a 30° -------------------------------------------------------

AIRE_AGUA = resolver(Datos(1.0, 1.333, 30, 0), Incognita.THETA2)


@pytest.mark.parametrize("incognita, despeje", [
    # n₁ · sen θ₁ = n₂ · sen θ₂, despejado a mano
    (Incognita.THETA2, "sen θ₂ = n₁ · sen θ₁ / n₂"),
    (Incognita.THETA1, "sen θ₁ = n₂ · sen θ₂ / n₁"),
    (Incognita.N1, "n₁ = n₂ · sen θ₂ / sen θ₁"),
    (Incognita.N2, "n₂ = n₁ · sen θ₁ / sen θ₂"),
])
def test_el_despeje_de_cada_incognita(incognita, despeje):
    segundo = ex.explicar(resolver(Datos(1.0, 1.5, 30, 19.47), incognita))[1]
    assert segundo.formulas == (despeje,)
    assert segundo.titulo == f"Despejamos {'sen ' if incognita.es_angulo else ''}{incognita.simbolo}"


def test_los_pasos_van_en_orden():
    assert titulos(AIRE_AGUA) == ["La ley de Snell", "Despejamos sen θ₂", "Sustituimos los datos",
                                  "Calculamos el ángulo", "Comprobación", "Qué significa"]


def test_la_sustitucion_lleva_los_numeros_del_usuario():
    # 1 · 0,5 / 1,333 = 0,37509
    assert paso(AIRE_AGUA, "Sustituimos los datos").formulas == (
        "sen θ₂ = 1,000 · sen 30,00° / 1,333",
        "sen θ₂ = 1,000 · 0,5000 / 1,333",
        "sen θ₂ = 0,3751",
    )
    resultado = paso(AIRE_AGUA, "Calculamos el ángulo")
    assert resultado.formulas == ("θ₂ = arcsen 0,3751 = 22,03°",)
    assert resultado.tipo == ex.RESULTADO


def test_la_comprobacion_da_lo_mismo_a_los_dos_lados():
    izquierda, derecha = paso(AIRE_AGUA, "Comprobación").formulas
    assert izquierda == "n₁ · sen θ₁ = 1,000 · 0,5000 = 0,5000"
    assert derecha == "n₂ · sen θ₂ = 1,333 · 0,3751 = 0,5000"


def test_que_significa_explica_velocidad_reflejo_y_brewster():
    texto = " ".join(paso(AIRE_AGUA, "Qué significa").texto)
    assert "más despacio" in texto and "se acerca a la normal" in texto
    assert f"224{MILES}901{FIJO}km/s" in texto
    # Fresnel a 30°: Rs = 0,03094 y Rp = 0,01194 → R = 2,14 %
    assert f"se refleja el 2,1{FIJO}% y pasa el 97,9{FIJO}%" in texto
    assert "53,12°" in texto                                   # arctan 1,333
    assert "ángulo crítico" not in texto and "θc" not in texto  # hacia un medio más denso no hay


def test_al_salir_a_un_medio_menos_denso_avisa_del_angulo_critico():
    texto = " ".join(paso(resolver(Datos(1.5, 1.0, 30, 0), Incognita.THETA2), "Qué significa").texto)
    assert "se aleja de la normal" in texto and "θc = 41,81°" in texto


@pytest.mark.parametrize("datos, frase", [
    (Datos(1.333, 1.333, 30, 0), "la luz no nota la superficie"),
    (Datos(1.0, 1.5, 0, 0), "llega perpendicular"),
])
def test_casos_sin_desviacion(datos, frase):
    assert frase in todo_el_texto(resolver(datos, Incognita.THETA2))


# --- sin solución -------------------------------------------------------------------------------

def test_reflexion_total_explica_por_que_no_hay_angulo():
    sol = resolver(Datos(1.5, 1.0, 60, 0), Incognita.THETA2)
    assert titulos(sol)[-1] == "No existe θ₂: reflexión total interna"
    aviso = ex.explicar(sol)[-1]
    assert aviso.tipo == ex.AVISO
    texto = " ".join(aviso.texto)
    assert "1,2990" in texto                                   # 1,5 · sen 60° = 1,29904
    assert "θc = arcsen (n₂ / n₁) = arcsen (1,000 / 1,500) = 41,81°" in texto
    assert "Comprobación" not in titulos(sol)


def test_theta1_imposible_dice_hasta_donde_llegan_los_refractados():
    sol = resolver(Datos(1.0, 1.5, 0, 50), Incognita.THETA1)
    texto = todo_el_texto(sol)
    assert "sen θ₁ = 1,1491" in texto                          # 1,5 · sen 50° = 1,14907
    assert "arcsen (n₁ / n₂) = 41,81°" in texto


def test_despejar_un_indice_paso_a_paso():
    # θ₂ = arcsen (1/3): n₂ = 1 · 0,5 / 0,3333 = 1,5
    sol = resolver(Datos(1.0, 0, 30, math.degrees(math.asin(1 / 3))), Incognita.N2)
    assert paso(sol, "Sustituimos los datos").formulas == (
        "n₂ = 1,000 · sen 30,00° / sen 19,47°",
        "n₂ = 1,000 · 0,5000 / 0,3333",
        "n₂ = 1,500",
    )
    assert "Ojo: índice menor que 1" not in titulos(sol)


def test_indice_menor_que_uno_avisa():
    # sen 20° / sen 30° = 0,684: más rápido que en el vacío
    sol = resolver(Datos(0, 1.0, 30, 20), Incognita.N1)
    assert "n₁ = 0,684" in todo_el_texto(sol)
    assert paso(sol, "Ojo: índice menor que 1").tipo == ex.AVISO


def test_no_avisa_de_indice_menor_que_uno_por_un_redondeo():
    # regresión: n₁ = 0,999995 se ve como 1,000 y no debe dar el aviso
    sol = resolver(Datos(0, 1.333, 30, 22.03), Incognita.N1)
    assert sol.valor < 1
    assert "Ojo: índice menor que 1" not in titulos(sol)


@pytest.mark.parametrize("datos, incognita, frase", [
    (Datos(1.0, 0, 0, 0), Incognita.N2, "0 / 0 no da un número"),
    (Datos(1.0, 0, 30, 0), Incognita.N2, "Con θ₂ = 0° habría que dividir entre 0."),
    (Datos(1.0, 0, 0, 20), Incognita.N2, "Saldría n₂ = 0"),
    (Datos(0, 1.5, 0, 20), Incognita.N1, "Con θ₁ = 0° habría que dividir entre 0."),
    (Datos(0, 1.5, 20, 0), Incognita.N1, "Saldría n₁ = 0"),
])
def test_indices_imposibles_explican_el_motivo(datos, incognita, frase):
    sol = resolver(datos, incognita)
    assert not sol.ok
    assert frase in todo_el_texto(sol)
    assert ex.explicar(sol)[-1].tipo == ex.AVISO


# --- resumen de la tarjeta de resultado -------------------------------------------------------------

@pytest.mark.parametrize("datos, incognita, esperado", [
    (Datos(1.0, 1.333, 30, 0), Incognita.THETA2, ("θ₂ = 22,03°", "El rayo se acerca a la normal")),
    (Datos(1.5, 1.0, 30, 0), Incognita.THETA2, ("θ₂ = 48,59°", "El rayo se aleja de la normal")),
    (Datos(1.0, 1.5, 0, 0), Incognita.THETA2, ("θ₂ = 0,00°", "El rayo no se desvía")),
    (Datos(1.4, 1.4, 25, 0), Incognita.THETA2, ("θ₂ = 25,00°", "El rayo no se desvía")),
    (Datos(1.5, 1.0, 60, 0), Incognita.THETA2, ("Reflexión total", "θ₁ supera el ángulo crítico (41,81°)")),
    (Datos(1.0, 1.5, 0, 50), Incognita.THETA1, ("Sin solución", "θ₂ no puede pasar de 41,81°")),
    (Datos(1.0, 1.5, 0, 0), Incognita.N1, ("Indeterminado", "Con los dos ángulos a 0° vale cualquier índice")),
    (Datos(1.0, 1.5, 20, 0), Incognita.N2, ("Sin solución", "Si un ángulo es 0°, el otro también tiene que serlo")),
])
def test_resumen(datos, incognita, esperado):
    # 1,5 · sen 30° = 0,75 → arcsen 0,75 = 48,59°
    assert ex.resumen(resolver(datos, incognita)) == esperado


def test_resumen_de_un_indice_reconoce_el_material():
    theta2 = math.degrees(math.asin(0.5 / 1.333))
    assert ex.resumen(resolver(Datos(1.0, 0, 30, theta2), Incognita.N2)) == (
        "n₂ = 1,333", "Coincide con: agua")
    # 1,5 queda entre el metacrilato (1,491) y el crown (1,517): el más cercano conserva las siglas
    theta2 = math.degrees(math.asin(1 / 3))
    assert ex.resumen(resolver(Datos(1.0, 0, 30, theta2), Incognita.N2))[1] == (
        "El más parecido: metacrilato (PMMA) (1,491)")
    theta2 = math.degrees(math.asin(0.5 / 4))
    assert ex.resumen(resolver(Datos(1.0, 0, 30, theta2), Incognita.N2))[1] == (
        "No se parece a ningún material de la lista")


def test_objetivo_y_datos_sin_la_incognita():
    sol = Solucion(Incognita.THETA2, Datos(1.0003, 1.333, 40, 99), Estado.OK, 28.84)
    assert ex.objetivo(sol) == "Buscamos θ₂: hacia dónde sale el rayo refractado."
    assert ex.datos_conocidos(sol) == "n₁ = 1,0003 · n₂ = 1,333 · θ₁ = 40,00°"
    assert all(ex.objetivo(resolver(Datos(), i)) for i in Incognita)


def test_en_el_angulo_de_brewster_lo_dice_y_suman_90_grados():
    # arctan 1,5 = 56,31°; θ₂ = arcsen (sen 56,31° / 1,5) = 33,69°: suman 90°
    sol = resolver(Datos(1.0, 1.5, 56.31, 0), Incognita.THETA2)
    assert "θ₁ + θ₂ = 90,00°" in todo_el_texto(sol)
    assert "Estás en él" not in todo_el_texto(resolver(Datos(1.0, 1.5, 50, 0), Incognita.THETA2))
