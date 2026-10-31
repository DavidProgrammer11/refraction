"""El CSV del historial tiene que abrirse bien con doble clic en Excel en español."""
import csv
import io

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from refraccion import db, exportar
from refraccion.optica import Datos, Incognita, resolver


@pytest.fixture
def conn():
    conexion = db.connect(":memory:")
    yield conexion
    conexion.close()


def leer(contenido: bytes) -> list[list[str]]:
    assert contenido.startswith(b"\xef\xbb\xbf")                 # BOM: Excel lee bien las tildes
    texto = contenido[3:].decode("utf-8")
    assert "\r\n" in texto and "\r\r\n" not in texto             # saltos de Windows, sin duplicar
    return list(csv.reader(io.StringIO(texto, newline=""), delimiter=";"))


def test_cabecera_y_una_fila_con_coma_decimal(conn):
    db.guardar_calculo(conn, resolver(Datos(1.0003, 1.333, 40, 0), Incognita.THETA2), "Aire", "Agua")
    cabecera, fila = leer(exportar.historial_csv(db.listar_calculos(conn)))
    assert cabecera == list(exportar.CABECERA)
    assert fila[1:] == ["θ₂", "Aire", "1,0003", "40,00", "Agua", "1,3330", "28,84", "θ₂ = 28,84°"]
    assert len(fila[0]) == 19                                    # «2026-10-29 10:15:00»


def test_la_incognita_sin_solucion_queda_vacia(conn):
    db.guardar_calculo(conn, resolver(Datos(1.5, 1.0, 60, 0), Incognita.THETA2), "Vidrio", "Aire")
    _, fila = leer(exportar.historial_csv(db.listar_calculos(conn)))
    assert fila[7] == "" and fila[8] == "Reflexión total"


@pytest.mark.parametrize("nombre, esperado", [
    ("=HYPERLINK(\"http://x\")", "'=HYPERLINK(\"http://x\")"),
    ("+34 600", "'+34 600"),
    ("-1", "'-1"),
    ("@SUMA(A1)", "'@SUMA(A1)"),
    ("Agua; sal", "Agua; sal"),                                # el «;» va entre comillas, no corta
    ("Vidrio \"crown\"", "Vidrio \"crown\""),
])
def test_los_nombres_no_se_ejecutan_como_formulas(conn, nombre, esperado):
    db.guardar_calculo(conn, resolver(Datos(), Incognita.THETA2), nombre, "Agua")
    _, fila = leer(exportar.historial_csv(db.listar_calculos(conn)))
    assert fila[2] == esperado


def test_historial_vacio_solo_lleva_la_cabecera(conn):
    assert leer(exportar.historial_csv([])) == [list(exportar.CABECERA)]


@given(nombre=st.text(min_size=1, max_size=30).filter(lambda s: s[0] not in "=+-@\t\r"))
@settings(max_examples=150)
def test_cualquier_nombre_vuelve_igual_al_leer_el_csv(nombre):
    conexion = db.connect(":memory:")
    db.guardar_calculo(conexion, resolver(Datos(), Incognita.THETA2), nombre, "b")
    contenido = exportar.historial_csv(db.listar_calculos(conexion))
    conexion.close()
    texto = contenido[3:].decode("utf-8")
    filas = list(csv.reader(io.StringIO(texto, newline=""), delimiter=";"))
    assert filas[1][2] == nombre
