"""Índices de refracción de materiales corrientes (luz amarilla del sodio, 589 nm).

Son valores de tablas para luz visible; el índice cambia un poco con el color de
la luz (dispersión) y con la temperatura, así que basta con tres decimales.
"""
from __future__ import annotations

from dataclasses import dataclass

PERSONALIZADO = "Personalizado"
_TOLERANCIA = 5e-5          # el índice se escribe con 4 decimales (el aire es 1,0003)


@dataclass(frozen=True)
class Material:
    nombre: str
    n: float


MATERIALES: tuple[Material, ...] = (
    Material("Vacío", 1.0),
    Material("Aire", 1.0003),
    Material("Hielo", 1.309),
    Material("Agua", 1.333),
    Material("Etanol", 1.361),
    Material("Cuarzo fundido", 1.458),
    Material("Aceite de oliva", 1.467),
    Material("Glicerina", 1.473),
    Material("Metacrilato (PMMA)", 1.491),
    Material("Vidrio crown (BK7)", 1.517),
    Material("Sal común (NaCl)", 1.544),
    Material("Policarbonato", 1.585),
    Material("Vidrio flint (F2)", 1.620),
    Material("Zafiro", 1.768),
    Material("Circonita", 2.150),
    Material("Diamante", 2.417),
)


def por_nombre(nombre: str) -> Material | None:
    return next((m for m in MATERIALES if m.nombre == nombre), None)


def nombre_de(n: float) -> str:
    """El material con ese índice, o «Personalizado» si no hay ninguno."""
    cercano = mas_parecido(n)
    return cercano.nombre if abs(cercano.n - n) < _TOLERANCIA else PERSONALIZADO


def mas_parecido(n: float) -> Material:
    return min(MATERIALES, key=lambda m: abs(m.n - n))
