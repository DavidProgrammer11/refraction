"""Historial a CSV para abrirlo con doble clic en Excel en español.

Separador «;», coma decimal y UTF-8 con BOM (sin BOM, Excel lee mal las tildes).
"""
from __future__ import annotations

import csv
import io
import sqlite3
from collections.abc import Iterable

from . import explicacion
from .db import datos_de
from .optica import Estado, Incognita, Solucion

CABECERA = ("Fecha", "Calculado", "Medio 1", "n₁", "θ₁ (°)", "Medio 2", "n₂", "θ₂ (°)", "Resultado")


def _numero(valor: float | None, decimales: int) -> str:
    return "" if valor is None else f"{valor:.{decimales}f}".replace(".", ",")


def _texto(valor: str) -> str:
    # Excel ejecuta lo que empieza por = + - @ como fórmula: se escribe como texto
    return f"'{valor}" if valor[:1] in ("=", "+", "-", "@", "\t", "\r") else valor


def _resultado(fila: sqlite3.Row) -> str:
    datos, incognita = datos_de(fila)
    sol = Solucion(incognita, datos, Estado(fila["estado"]), fila[incognita.value])
    return explicacion.resumen(sol)[0]


def historial_csv(filas: Iterable[sqlite3.Row]) -> bytes:
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(CABECERA)
    for fila in filas:
        escritor.writerow((
            fila["creado"],
            Incognita(fila["incognita"]).simbolo,
            _texto(fila["medio1"]),
            _numero(fila["n1"], 4),
            _numero(fila["theta1"], 2),
            _texto(fila["medio2"]),
            _numero(fila["n2"], 4),
            _numero(fila["theta2"], 2),
            _texto(_resultado(fila)),
        ))
    return "\ufeff".encode("utf-8") + salida.getvalue().encode("utf-8")
