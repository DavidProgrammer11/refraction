"""Situaciones reales para empezar: cada una enseña una idea de la refracción."""
from __future__ import annotations

from dataclasses import dataclass

from .optica import Datos, Incognita


@dataclass(frozen=True)
class Ejemplo:
    titulo: str
    idea: str
    incognita: Incognita
    medio1: str
    medio2: str
    datos: Datos


EJEMPLOS: tuple[Ejemplo, ...] = (
    Ejemplo("Del aire al agua",
            "Al entrar en un medio más lento, el rayo se acerca a la normal.",
            Incognita.THETA2, "Aire", "Agua", Datos(1.0003, 1.333, 40.0, 0.0)),
    Ejemplo("Del agua al aire",
            "Al salir a un medio más rápido, el rayo se aleja de la normal: "
            "por eso el fondo de una piscina parece más cerca.",
            Incognita.THETA2, "Agua", "Aire", Datos(1.333, 1.0003, 35.0, 0.0)),
    Ejemplo("Reflexión total en el agua",
            "Desde dentro del agua, pasado el ángulo crítico (48,6°) la superficie "
            "hace de espejo.",
            Incognita.THETA2, "Agua", "Aire", Datos(1.333, 1.0003, 55.0, 0.0)),
    Ejemplo("Fibra óptica",
            "El núcleo de vidrio flint, rodeado de vidrio crown: la luz rebota dentro "
            "sin escaparse mientras supere el ángulo crítico.",
            Incognita.THETA2, "Vidrio flint (F2)", "Vidrio crown (BK7)", Datos(1.620, 1.517, 75.0, 0.0)),
    Ejemplo("Por qué brilla un diamante",
            "Su índice es tan alto que el ángulo crítico baja a 24,4°: casi toda la luz "
            "que entra rebota dentro antes de salir.",
            Incognita.THETA2, "Diamante", "Aire", Datos(2.417, 1.0003, 30.0, 0.0)),
    Ejemplo("Medir el índice de un vidrio",
            "Midiendo los dos ángulos se averigua el índice del material: sale el "
            "del vidrio crown.",
            Incognita.N2, "Aire", "Vidrio crown (BK7)", Datos(1.0003, 1.517, 45.0, 27.79)),
    Ejemplo("Ángulo de Brewster",
            "Con esta incidencia la luz reflejada en el vidrio sale polarizada; así "
            "funcionan las gafas de sol polarizadas.",
            Incognita.THETA2, "Aire", "Vidrio crown (BK7)", Datos(1.0003, 1.517, 56.6, 0.0)),
    Ejemplo("Incidencia perpendicular",
            "Si el rayo llega perpendicular (θ₁ = 0°) cambia de velocidad, pero no se desvía.",
            Incognita.THETA2, "Aire", "Vidrio crown (BK7)", Datos(1.0003, 1.517, 0.0, 0.0)),
)
