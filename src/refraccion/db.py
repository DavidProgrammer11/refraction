"""Base de datos SQLite con migraciones numeradas (PRAGMA user_version).

Guarda el historial de cálculos y los ajustes de la ventana. No importa Qt, para
poder probar la lógica de datos sin interfaz.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .optica import Datos, Incognita, Solucion

# Cada migración se aplica una sola vez, en orden y dentro de una transacción.
# Para cambiar el esquema, AÑADE una migración al final; no edites las que ya se
# han entregado, porque los clientes tienen bases de datos creadas con ellas.
MIGRATIONS: list[str] = [
    # 1: historial de cálculos y ajustes (clave → valor en JSON)
    """
    CREATE TABLE calculos (
        id        INTEGER PRIMARY KEY,
        creado    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        incognita TEXT NOT NULL CHECK (incognita IN ('n1', 'n2', 'theta1', 'theta2')),
        estado    TEXT NOT NULL,
        medio1    TEXT NOT NULL,
        medio2    TEXT NOT NULL,
        n1        REAL,
        n2        REAL,
        theta1    REAL,
        theta2    REAL
    );
    CREATE TABLE ajustes (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    );
    """,
]


def connect(ruta: Path | str) -> sqlite3.Connection:
    """Abre (o crea) la base de datos y aplica las migraciones pendientes."""
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection) -> int:
    """Aplica las migraciones pendientes y devuelve la versión final del esquema."""
    actual = schema_version(conn)
    if actual > len(MIGRATIONS):
        raise RuntimeError(
            f"La base de datos está en la versión {actual} del esquema, más nueva que esta "
            f"app ({len(MIGRATIONS)}). Actualiza la aplicación."
        )
    for version, sql in enumerate(MIGRATIONS[actual:], start=actual + 1):
        # executescript hace COMMIT antes de empezar, así que la transacción se abre
        # dentro del propio script: si falla, no queda la migración a medias.
        try:
            conn.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {version};\nCOMMIT;")
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
    return schema_version(conn)


# --- historial de cálculos ---------------------------------------------------------

def guardar_calculo(conn: sqlite3.Connection, sol: Solucion, medio1: str, medio2: str) -> int:
    """Apunta un cálculo. La incógnita se guarda como NULL si no tuvo solución."""
    valores = {campo.value: sol.datos.valor(campo) for campo in Incognita}
    valores[sol.incognita.value] = sol.valor
    with conn:
        cursor = conn.execute(
            "INSERT INTO calculos (incognita, estado, medio1, medio2, n1, n2, theta1, theta2)"
            " VALUES (:incognita, :estado, :medio1, :medio2, :n1, :n2, :theta1, :theta2)",
            {"incognita": sol.incognita.value, "estado": sol.estado.value,
             "medio1": medio1, "medio2": medio2, **valores},
        )
    return cursor.lastrowid


def listar_calculos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Los cálculos, del más reciente al más antiguo."""
    return conn.execute("SELECT * FROM calculos ORDER BY id DESC").fetchall()


def leer_calculo(conn: sqlite3.Connection, calculo_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM calculos WHERE id = ?", (calculo_id,)).fetchone()


def borrar_calculo(conn: sqlite3.Connection, calculo_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM calculos WHERE id = ?", (calculo_id,))


def vaciar_historial(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("DELETE FROM calculos")


def datos_de(fila: sqlite3.Row) -> tuple[Datos, Incognita]:
    """Los datos de entrada de un cálculo guardado, para volver a cargarlo."""
    incognita = Incognita(fila["incognita"])
    valores = {campo.value: fila[campo.value] for campo in Incognita}
    valores[incognita.value] = valores[incognita.value] or 0.0
    return Datos(**valores), incognita


# --- ajustes -----------------------------------------------------------------------

def leer_ajuste(conn: sqlite3.Connection, clave: str, defecto: Any = None) -> Any:
    fila = conn.execute("SELECT valor FROM ajustes WHERE clave = ?", (clave,)).fetchone()
    if fila is None:
        return defecto
    try:
        return json.loads(fila["valor"])
    except ValueError:
        return defecto


def guardar_ajuste(conn: sqlite3.Connection, clave: str, valor: Any) -> None:
    with conn:
        conn.execute(
            "INSERT INTO ajustes (clave, valor) VALUES (?, ?)"
            " ON CONFLICT (clave) DO UPDATE SET valor = excluded.valor",
            (clave, json.dumps(valor, ensure_ascii=False)),
        )
