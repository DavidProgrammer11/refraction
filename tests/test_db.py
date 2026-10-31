"""Base de datos real en archivos temporales (sin mocks del motor)."""
import sqlite3

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from refraccion import db
from refraccion.optica import Datos, Incognita, resolver


@pytest.fixture
def conn(tmp_path):
    carpeta = tmp_path / "carpeta con ñ"          # como C:\Programación
    carpeta.mkdir()
    conexion = db.connect(carpeta / "datos.sqlite3")
    yield conexion
    conexion.close()


# --- migraciones ---------------------------------------------------------------------------

def test_base_nueva_queda_en_la_ultima_version(conn):
    assert db.schema_version(conn) == len(db.MIGRATIONS)
    tablas = {f["name"] for f in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"calculos", "ajustes"} <= tablas


def test_reabrir_no_vuelve_a_aplicar_migraciones(tmp_path):
    ruta = tmp_path / "prueba.sqlite3"
    conexion = db.connect(ruta)
    db.guardar_ajuste(conexion, "x", 1)
    conexion.close()
    conexion = db.connect(ruta)            # fallaría con "table already exists" si se reaplicaran
    assert db.schema_version(conexion) == len(db.MIGRATIONS)
    assert db.leer_ajuste(conexion, "x") == 1
    conexion.close()


def test_migracion_que_falla_no_deja_cambios_a_medias(tmp_path, monkeypatch):
    conexion = sqlite3.connect(tmp_path / "prueba.sqlite3")
    rota = "CREATE TABLE a (id INTEGER); CREATE TABLE a (id INTEGER);"   # la segunda falla
    monkeypatch.setattr(db, "MIGRATIONS", [rota])
    with pytest.raises(sqlite3.OperationalError):
        db.migrate(conexion)
    assert db.schema_version(conexion) == 0
    assert conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall() == []
    conexion.close()


def test_base_mas_nueva_que_la_app_da_error_claro(tmp_path):
    conexion = sqlite3.connect(tmp_path / "prueba.sqlite3")
    conexion.execute(f"PRAGMA user_version = {len(db.MIGRATIONS) + 1}")
    with pytest.raises(RuntimeError, match="Actualiza la aplicación"):
        db.migrate(conexion)
    conexion.close()


# --- historial -----------------------------------------------------------------------------

def test_guardar_y_releer_un_calculo(conn):
    sol = resolver(Datos(1.0, 1.333, 30, 0), Incognita.THETA2)
    calculo = db.guardar_calculo(conn, sol, "Vacío", "Agua")
    fila = db.leer_calculo(conn, calculo)
    assert (fila["incognita"], fila["estado"], fila["medio1"], fila["medio2"]) == (
        "theta2", "ok", "Vacío", "Agua")
    assert fila["theta2"] == pytest.approx(sol.valor)       # se guarda el resultado, no el dato viejo
    datos, incognita = db.datos_de(fila)
    assert incognita is Incognita.THETA2
    assert (datos.n1, datos.n2, datos.theta1) == (1.0, 1.333, 30)
    assert fila["creado"]


def test_sin_solucion_la_incognita_queda_vacia(conn):
    sol = resolver(Datos(1.5, 1.0, 60, 12.5), Incognita.THETA2)
    fila = db.leer_calculo(conn, db.guardar_calculo(conn, sol, "Vidrio", "Aire"))
    assert fila["estado"] == "reflexion_total"
    assert fila["theta2"] is None
    datos, _ = db.datos_de(fila)
    assert datos.theta2 == 0.0


def test_lista_del_mas_reciente_al_mas_antiguo_y_borrar(conn):
    ids = [db.guardar_calculo(conn, resolver(Datos(1, 1.5, t, 0), Incognita.THETA2), "a", "b")
           for t in (10, 20, 30)]
    assert [f["id"] for f in db.listar_calculos(conn)] == ids[::-1]
    db.borrar_calculo(conn, ids[1])
    assert [f["id"] for f in db.listar_calculos(conn)] == [ids[2], ids[0]]
    db.borrar_calculo(conn, 9999)                                 # no existe: no pasa nada
    db.vaciar_historial(conn)
    assert db.listar_calculos(conn) == []
    assert db.leer_calculo(conn, ids[0]) is None


def test_nombre_con_sql_se_guarda_literal(conn):
    malicioso = "x'); DROP TABLE calculos; --"
    calculo = db.guardar_calculo(conn, resolver(Datos(), Incognita.THETA2), malicioso, "ñandú 💧")
    fila = db.leer_calculo(conn, calculo)
    assert (fila["medio1"], fila["medio2"]) == (malicioso, "ñandú 💧")


def test_la_base_rechaza_una_incognita_inventada(conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        with conn:
            conn.execute("INSERT INTO calculos (incognita, estado, medio1, medio2)"
                         " VALUES ('n3', 'ok', 'a', 'b')")
    assert db.listar_calculos(conn) == []


# --- ajustes -------------------------------------------------------------------------------

def test_ajuste_que_no_existe_da_el_valor_por_defecto(conn):
    assert db.leer_ajuste(conn, "nada") is None
    assert db.leer_ajuste(conn, "nada", {"a": 1}) == {"a": 1}


def test_guardar_un_ajuste_dos_veces_lo_sustituye(conn):
    db.guardar_ajuste(conn, "estado", {"incognita": "n1"})
    db.guardar_ajuste(conn, "estado", {"incognita": "theta1"})
    assert db.leer_ajuste(conn, "estado") == {"incognita": "theta1"}
    assert conn.execute("SELECT COUNT(*) FROM ajustes").fetchone()[0] == 1


def test_ajuste_corrupto_da_el_valor_por_defecto(conn):
    with conn:
        conn.execute("INSERT INTO ajustes (clave, valor) VALUES ('estado', '{roto')")
    assert db.leer_ajuste(conn, "estado", {}) == {}


@given(valor=st.recursive(
    st.none() | st.booleans() | st.integers(-10**9, 10**9) | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20),
    lambda hijos: st.lists(hijos, max_size=4) | st.dictionaries(st.text(max_size=8), hijos, max_size=4),
    max_leaves=12))
@settings(max_examples=150)
def test_cualquier_ajuste_vuelve_igual(valor):
    conexion = db.connect(":memory:")
    db.guardar_ajuste(conexion, "clave ñ", valor)
    assert db.leer_ajuste(conexion, "clave ñ") == valor
    conexion.close()
