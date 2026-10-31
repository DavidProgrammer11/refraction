"""Física de la refracción: ley de Snell, ángulo crítico, Brewster y Fresnel.

No importa Qt, para poder probarlo todo sin interfaz. Los ángulos se miden desde
la normal y van en grados; los índices de refracción son adimensionales.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

C_VACIO_KM_S = 299_792.458          # velocidad de la luz en el vacío
ANGULO_MAX = 90.0                   # incidencia rasante
_TOLERANCIA = 1e-12                 # para no perder el ángulo crítico exacto por redondeo


class Incognita(str, Enum):
    N1 = "n1"
    N2 = "n2"
    THETA1 = "theta1"
    THETA2 = "theta2"

    @property
    def es_angulo(self) -> bool:
        return self in (Incognita.THETA1, Incognita.THETA2)

    @property
    def simbolo(self) -> str:
        return {"n1": "n₁", "n2": "n₂", "theta1": "θ₁", "theta2": "θ₂"}[self.value]


class Estado(str, Enum):
    OK = "ok"
    REFLEXION_TOTAL = "reflexion_total"   # se pedía θ₂ y no hay rayo refractado
    SIN_SOLUCION = "sin_solucion"         # los datos no los cumple ningún valor
    INDETERMINADA = "indeterminada"       # los datos los cumple cualquier valor


@dataclass(frozen=True)
class Datos:
    """Las cuatro magnitudes de la ley de Snell: n₁ · sen θ₁ = n₂ · sen θ₂."""

    n1: float = 1.0
    n2: float = 1.333
    theta1: float = 30.0
    theta2: float = 0.0

    def valor(self, incognita: Incognita) -> float:
        return getattr(self, incognita.value)

    def con(self, incognita: Incognita, valor: float) -> Datos:
        return replace(self, **{incognita.value: valor})


@dataclass(frozen=True)
class Solucion:
    incognita: Incognita
    datos: Datos            # los datos de entrada; el campo de la incógnita no se usa
    estado: Estado
    valor: float | None     # la incógnita, si se ha podido calcular

    @property
    def ok(self) -> bool:
        return self.estado is Estado.OK

    def completa(self) -> Datos | None:
        """Los cuatro valores con la incógnita resuelta, o None si no hay solución."""
        return self.datos.con(self.incognita, self.valor) if self.ok else None


# --- funciones básicas --------------------------------------------------------------

def sen(grados: float) -> float:
    """Seno de un ángulo en grados."""
    return math.sin(math.radians(grados))


def _arcsen(x: float) -> float | None:
    """arcsen en grados; None si |x| > 1 (no existe ese ángulo)."""
    if x > 1 + _TOLERANCIA:
        return None
    return math.degrees(math.asin(min(x, 1.0)))


def refractar(n1: float, n2: float, theta1: float) -> float | None:
    """Ángulo refractado θ₂, o None si hay reflexión total interna."""
    return _arcsen(n1 * sen(theta1) / n2)


def incidente(n1: float, n2: float, theta2: float) -> float | None:
    """Ángulo de incidencia θ₁ que produce θ₂, o None si ninguno lo produce.

    Es la misma cuenta con los medios intercambiados: la luz recorre el mismo
    camino en los dos sentidos.
    """
    return refractar(n2, n1, theta2)


def angulo_critico(n1: float, n2: float) -> float | None:
    """Incidencia a partir de la cual hay reflexión total (solo si n₁ > n₂)."""
    return math.degrees(math.asin(n2 / n1)) if n1 > n2 else None


def angulo_brewster(n1: float, n2: float) -> float:
    """Incidencia con la que la luz polarizada p no se refleja nada."""
    return math.degrees(math.atan2(n2, n1))


def velocidad(n: float) -> float:
    """Velocidad de la luz en el medio, en km/s."""
    return C_VACIO_KM_S / n


@dataclass(frozen=True)
class Fresnel:
    """Fracción de la potencia que se refleja (R) y que pasa (T)."""

    rs: float           # reflectancia, polarización s (perpendicular al plano de incidencia)
    rp: float           # reflectancia, polarización p (paralela)

    @property
    def r(self) -> float:
        """Reflectancia de la luz no polarizada (la media de s y p)."""
        return (self.rs + self.rp) / 2

    @property
    def t(self) -> float:
        return 1.0 - self.r


def fresnel(n1: float, n2: float, theta1: float) -> Fresnel:
    """Ecuaciones de Fresnel para medios transparentes."""
    if n1 == n2:
        return Fresnel(0.0, 0.0)            # no hay superficie que refleje
    sen_t = n1 * sen(theta1) / n2
    if sen_t >= 1:
        return Fresnel(1.0, 1.0)            # reflexión total (o rasante en el límite)
    cos_i = math.cos(math.radians(theta1))
    cos_t = math.sqrt(1 - sen_t * sen_t)
    rs = (n1 * cos_i - n2 * cos_t) / (n1 * cos_i + n2 * cos_t)
    rp = (n2 * cos_i - n1 * cos_t) / (n2 * cos_i + n1 * cos_t)
    return Fresnel(rs * rs, rp * rp)


# --- resolver la incógnita ----------------------------------------------------------

def validar(datos: Datos, incognita: Incognita) -> None:
    """Lanza ValueError con un mensaje para el usuario si algún dato no vale."""
    for campo in Incognita:
        if campo is incognita:
            continue
        valor = datos.valor(campo)
        nombre = campo.simbolo
        if not math.isfinite(valor):
            raise ValueError(f"{nombre} no es un número.")
        if campo.es_angulo and not 0 <= valor <= ANGULO_MAX:
            raise ValueError(f"{nombre} tiene que estar entre 0° y 90° (se mide desde la normal).")
        if not campo.es_angulo and valor <= 0:
            raise ValueError(f"{nombre} tiene que ser mayor que 0.")


def resolver(datos: Datos, incognita: Incognita) -> Solucion:
    """Despeja la incógnita de n₁ · sen θ₁ = n₂ · sen θ₂."""
    validar(datos, incognita)
    d = datos
    if incognita is Incognita.THETA2:
        valor = refractar(d.n1, d.n2, d.theta1)
        estado = Estado.OK if valor is not None else Estado.REFLEXION_TOTAL
    elif incognita is Incognita.THETA1:
        valor = incidente(d.n1, d.n2, d.theta2)
        estado = Estado.OK if valor is not None else Estado.SIN_SOLUCION
    else:
        # n₁ = n₂ · sen θ₂ / sen θ₁   y   n₂ = n₁ · sen θ₁ / sen θ₂
        if incognita is Incognita.N1:
            conocido, sen_arriba, sen_abajo = d.n2, sen(d.theta2), sen(d.theta1)
        else:
            conocido, sen_arriba, sen_abajo = d.n1, sen(d.theta1), sen(d.theta2)
        if sen_abajo == 0:
            valor = None
            estado = Estado.INDETERMINADA if sen_arriba == 0 else Estado.SIN_SOLUCION
        elif sen_arriba == 0:
            valor, estado = None, Estado.SIN_SOLUCION      # saldría n = 0
        else:
            valor, estado = conocido * sen_arriba / sen_abajo, Estado.OK
    return Solucion(incognita, datos, estado, valor)


def invariante(n: float, theta: float) -> float:
    """n · sen θ: lo que la ley de Snell dice que se conserva al cruzar la superficie."""
    return n * sen(theta)


# --- curvas para las gráficas -------------------------------------------------------

def curva_refraccion(n1: float, n2: float, puntos: int = 361) -> list[tuple[float, float]]:
    """Puntos (θ₁, θ₂) de 0° a 90°, cortados en el ángulo crítico si lo hay."""
    critico = angulo_critico(n1, n2)
    fin = critico if critico is not None else ANGULO_MAX
    xs = [fin * i / (puntos - 1) for i in range(puntos)]
    return [(x, refractar(n1, n2, x)) for x in xs]


def curva_fresnel(n1: float, n2: float, puntos: int = 361) -> list[tuple[float, Fresnel]]:
    """Puntos (θ₁, Fresnel) de 0° a 90°, con el ángulo crítico incluido si lo hay."""
    xs = [ANGULO_MAX * i / (puntos - 1) for i in range(puntos)]
    critico = angulo_critico(n1, n2)
    if critico is not None and critico not in xs:
        xs = sorted([*xs, critico])
    return [(x, fresnel(n1, n2, x)) for x in xs]
