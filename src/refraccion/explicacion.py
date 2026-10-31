"""El cálculo contado paso a paso, con los números del usuario.

Devuelve texto llano (la interfaz le pone los colores). No importa Qt.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import materiales
from .optica import (
    Datos, Estado, Incognita, Solucion, angulo_brewster, angulo_critico, fresnel,
    invariante, velocidad, sen,
)

NORMAL, RESULTADO, AVISO, NOTA = "normal", "resultado", "aviso", "nota"
_ESPACIO_MILES = "\u202f"       # espacio fino que no parte la cifra
_ESPACIO_FIJO = "\u00a0"


@dataclass(frozen=True)
class Paso:
    titulo: str
    formulas: tuple[str, ...] = ()
    texto: tuple[str, ...] = ()
    tipo: str = NORMAL


# --- números en español --------------------------------------------------------------

def num(x: float, decimales: int = 2) -> str:
    """Coma decimal y, a partir de 10 000, espacio de millares (norma RAE)."""
    x = round(x, decimales) or 0.0               # sin «-0,00»
    texto = f"{x:,.{decimales}f}"
    separador = _ESPACIO_MILES if abs(x) >= 10_000 else ""   # ya redondeado: 9999,999 → 10 000
    return texto.replace(",", separador).replace(".", ",")


def indice(n: float) -> str:
    """Índice de refracción con 3 o 4 decimales: 1,333 · 1,0003 · 2,417."""
    texto = f"{n:.4f}"
    if texto.endswith("0"):
        texto = texto[:-1]
    return texto.replace(".", ",")


def angulo(grados: float) -> str:
    return f"{num(grados, 2)}°"


def seno(x: float) -> str:
    return num(x, 4)


def porcentaje(fraccion: float) -> str:
    return f"{num(fraccion * 100, 1)}{_ESPACIO_FIJO}%"


def rapidez(n: float) -> str:
    return f"{num(velocidad(n), 0)}{_ESPACIO_FIJO}km/s"


def formatear(incognita: Incognita, valor: float) -> str:
    return angulo(valor) if incognita.es_angulo else indice(valor)


# --- la explicación -------------------------------------------------------------------

_DESPEJE = {
    Incognita.THETA2: "sen θ₂ = n₁ · sen θ₁ / n₂",
    Incognita.THETA1: "sen θ₁ = n₂ · sen θ₂ / n₁",
    Incognita.N1: "n₁ = n₂ · sen θ₂ / sen θ₁",
    Incognita.N2: "n₂ = n₁ · sen θ₁ / sen θ₂",
}


_OBJETIVO = {
    Incognita.THETA2: "Buscamos θ₂: hacia dónde sale el rayo refractado.",
    Incognita.THETA1: "Buscamos θ₁: con qué ángulo tiene que llegar el rayo.",
    Incognita.N1: "Buscamos n₁: el índice de refracción del medio 1.",
    Incognita.N2: "Buscamos n₂: el índice de refracción del medio 2.",
}


def objetivo(sol: Solucion) -> str:
    return _OBJETIVO[sol.incognita]


def datos_conocidos(sol: Solucion) -> str:
    """Los tres datos del problema: «n₁ = 1,0003 · n₂ = 1,333 · θ₁ = 30,00°»."""
    partes = []
    for campo in Incognita:
        if campo is not sol.incognita:
            partes.append(f"{campo.simbolo} = {formatear(campo, sol.datos.valor(campo))}")
    return " · ".join(partes)


def explicar(sol: Solucion) -> list[Paso]:
    pasos = [
        Paso("La ley de Snell", ("n₁ · sen θ₁ = n₂ · sen θ₂",),
             ("Al cruzar la superficie se conserva n · sen θ.",)),
        Paso(f"Despejamos {'sen ' if sol.incognita.es_angulo else ''}{sol.incognita.simbolo}",
             (_DESPEJE[sol.incognita],)),
    ]
    if sol.incognita.es_angulo:
        pasos += _pasos_angulo(sol)
    else:
        pasos += _pasos_indice(sol)
    completa = sol.completa()
    if completa is not None:
        pasos.append(_comprobacion(completa))
        pasos.append(_significado(completa))
    return pasos


def _pasos_angulo(sol: Solucion) -> list[Paso]:
    d = sol.datos
    if sol.incognita is Incognita.THETA2:
        n_a, n_b, theta, sim, sim_dato = d.n1, d.n2, d.theta1, "θ₂", "θ₁"
    else:
        n_a, n_b, theta, sim, sim_dato = d.n2, d.n1, d.theta2, "θ₁", "θ₂"
    x = n_a * sen(theta) / n_b
    pasos = [Paso("Sustituimos los datos", (
        f"sen {sim} = {indice(n_a)} · sen {angulo(theta)} / {indice(n_b)}",
        f"sen {sim} = {indice(n_a)} · {seno(sen(theta))} / {indice(n_b)}",
        f"sen {sim} = {seno(x)}",
    ))]
    if sol.ok:
        pasos.append(Paso("Calculamos el ángulo",
                          (f"{sim} = arcsen {seno(x)} = {angulo(sol.valor)}",), tipo=RESULTADO))
    elif sol.estado is Estado.REFLEXION_TOTAL:
        critico = angulo_critico(d.n1, d.n2)
        pasos.append(Paso("No existe θ₂: reflexión total interna", texto=(
            f"Ningún ángulo tiene un seno mayor que 1, y aquí saldría {seno(x)}.",
            "No hay rayo refractado: toda la luz se refleja hacia el medio 1.",
            f"Ocurre a partir del ángulo crítico θc = arcsen (n₂ / n₁) = "
            f"arcsen ({indice(d.n2)} / {indice(d.n1)}) = {angulo(critico)}, "
            f"y {sim_dato} = {angulo(theta)} lo supera.",
        ), tipo=AVISO))
    else:
        limite = angulo_critico(d.n2, d.n1)
        pasos.append(Paso("No existe θ₁", texto=(
            f"Ningún ángulo tiene un seno mayor que 1, y aquí saldría {seno(x)}.",
            f"Ningún rayo del medio 1 sale con θ₂ = {angulo(theta)}: los refractados solo "
            f"llegan hasta arcsen (n₁ / n₂) = {angulo(limite)}.",
        ), tipo=AVISO))
    return pasos


def _pasos_indice(sol: Solucion) -> list[Paso]:
    d = sol.datos
    if sol.incognita is Incognita.N1:
        sim, n_dato, th_arriba, th_abajo = "n₁", d.n2, d.theta2, d.theta1
        sim_arriba, sim_abajo = "θ₂", "θ₁"
    else:
        sim, n_dato, th_arriba, th_abajo = "n₂", d.n1, d.theta1, d.theta2
        sim_arriba, sim_abajo = "θ₁", "θ₂"
    lineas = [
        f"{sim} = {indice(n_dato)} · sen {angulo(th_arriba)} / sen {angulo(th_abajo)}",
        f"{sim} = {indice(n_dato)} · {seno(sen(th_arriba))} / {seno(sen(th_abajo))}",
    ]
    if sol.ok:
        lineas.append(f"{sim} = {indice(sol.valor)}")
        pasos = [Paso("Sustituimos los datos", tuple(lineas), tipo=RESULTADO)]
        if sol.valor < 0.9995:                     # se ve por debajo de 1,000
            pasos.append(Paso("Ojo: índice menor que 1", texto=(
                f"Con {sim} < 1 la luz iría más rápido que en el vacío. Solo pasa en casos "
                "especiales (rayos X, plasmas); en un material corriente, revisa los ángulos.",
            ), tipo=AVISO))
        return pasos
    pasos = [Paso("Sustituimos los datos", tuple(lineas))]
    if sol.estado is Estado.INDETERMINADA:
        pasos.append(Paso(f"{sim} no se puede despejar", texto=(
            "Con θ₁ = θ₂ = 0° los dos lados valen 0 sea cual sea el índice: 0 / 0 no da un número.",
            "Un rayo perpendicular a la superficie no se desvía con ningún par de medios.",
            "Elige ángulos distintos de 0° para poder medir el índice.",
        ), tipo=AVISO))
    elif sen(th_abajo) == 0:
        pasos.append(Paso("Sin solución", texto=(
            f"Con {sim_abajo} = 0° habría que dividir entre 0.",
            f"Un rayo perpendicular no se desvía: {sim_arriba} también tendría que ser 0°.",
        ), tipo=AVISO))
    else:
        pasos.append(Paso("Sin solución", texto=(
            f"Saldría {sim} = 0, y ningún medio tiene índice 0.",
            f"Si el rayo va inclinado a un lado ({sim_abajo} > 0°), al otro lado también "
            f"({sim_arriba} > 0°).",
        ), tipo=AVISO))
    return pasos


def _comprobacion(d: Datos) -> Paso:
    return Paso("Comprobación", (
        f"n₁ · sen θ₁ = {indice(d.n1)} · {seno(sen(d.theta1))} = {seno(invariante(d.n1, d.theta1))}",
        f"n₂ · sen θ₂ = {indice(d.n2)} · {seno(sen(d.theta2))} = {seno(invariante(d.n2, d.theta2))}",
    ), ("Los dos lados dan lo mismo: el resultado cumple la ley.",))


def _significado(d: Datos) -> Paso:
    lineas = []
    if d.n1 == d.n2:
        lineas.append("Los dos medios tienen el mismo índice: la luz no nota la superficie "
                      "y sigue recta (θ₂ = θ₁).")
    else:
        if d.n2 > d.n1:
            lineas.append(f"En el medio 2 la luz va más despacio ({rapidez(d.n2)} frente a "
                          f"{rapidez(d.n1)}), y por eso se acerca a la normal: θ₂ < θ₁.")
        else:
            lineas.append(f"En el medio 2 la luz va más deprisa ({rapidez(d.n2)} frente a "
                          f"{rapidez(d.n1)}), y por eso se aleja de la normal: θ₂ > θ₁.")
        if d.theta1 == 0:
            lineas.append("Pero llega perpendicular (θ₁ = 0°): cambia de velocidad sin desviarse.")
        critico = angulo_critico(d.n1, d.n2)
        if critico is not None:
            lineas.append(f"Si θ₁ pasara de θc = {angulo(critico)}, no saldría luz al medio 2 "
                          "(reflexión total interna).")
        f = fresnel(d.n1, d.n2, d.theta1)
        lineas.append(f"De la luz que llega se refleja el {porcentaje(f.r)} y pasa el "
                      f"{porcentaje(f.t)} (ecuaciones de Fresnel, luz no polarizada).")
        brewster = angulo_brewster(d.n1, d.n2)
        lineas.append(f"Con θ₁ = θB = arctan (n₂ / n₁) = {angulo(brewster)} "
                      "la luz reflejada sale polarizada (ángulo de Brewster).")
        if abs(d.theta1 - brewster) < 0.5:
            lineas.append(f"Estás en él: θ₁ + θ₂ = {angulo(d.theta1 + d.theta2)}, así que el rayo "
                          "reflejado y el refractado salen en ángulo recto.")
    return Paso("Qué significa", texto=tuple(lineas), tipo=NOTA)


# --- el resumen de la tarjeta de resultado --------------------------------------------

def _en_frase(nombre: str) -> str:
    """«Vidrio crown (BK7)» → «vidrio crown (BK7)»: sin tocar las siglas."""
    return nombre[:1].lower() + nombre[1:]


def resumen(sol: Solucion) -> tuple[str, str]:
    """(titular, detalle) para mostrar el resultado en grande."""
    d = sol.datos
    if sol.ok:
        titular = f"{sol.incognita.simbolo} = {formatear(sol.incognita, sol.valor)}"
        if sol.incognita.es_angulo:
            completa = sol.completa()
            if completa.n1 == completa.n2 or completa.theta1 == 0:
                detalle = "El rayo no se desvía"
            elif completa.n2 > completa.n1:
                detalle = "El rayo se acerca a la normal"
            else:
                detalle = "El rayo se aleja de la normal"
        else:
            cercano = materiales.mas_parecido(sol.valor)
            distancia = abs(cercano.n - sol.valor)
            if distancia < 5e-4:
                detalle = f"Coincide con: {_en_frase(cercano.nombre)}"
            elif distancia <= 0.1:
                detalle = f"El más parecido: {_en_frase(cercano.nombre)} ({indice(cercano.n)})"
            else:
                detalle = "No se parece a ningún material de la lista"
        return titular, detalle
    if sol.estado is Estado.REFLEXION_TOTAL:
        critico = angulo_critico(d.n1, d.n2)
        return "Reflexión total", f"θ₁ supera el ángulo crítico ({angulo(critico)})"
    if sol.estado is Estado.INDETERMINADA:
        return "Indeterminado", "Con los dos ángulos a 0° vale cualquier índice"
    if sol.incognita is Incognita.THETA1:
        return "Sin solución", f"θ₂ no puede pasar de {angulo(angulo_critico(d.n2, d.n1))}"
    return "Sin solución", "Si un ángulo es 0°, el otro también tiene que serlo"
