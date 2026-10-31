"""La lista de materiales y los ejemplos del menú: que lo que dicen sea verdad."""
import pytest

from refraccion import ejemplos, materiales
from refraccion import explicacion as ex
from refraccion.optica import Estado, angulo_brewster, angulo_critico, resolver


def test_materiales_ordenados_de_menos_a_mas_denso_y_sin_repetir():
    ns = [m.n for m in materiales.MATERIALES]
    assert ns == sorted(ns) and len(set(ns)) == len(ns)
    nombres = [m.nombre for m in materiales.MATERIALES]
    assert len(set(nombres)) == len(nombres)
    assert materiales.PERSONALIZADO not in nombres
    assert all(1.0 <= n < 2.5 for n in ns)


@pytest.mark.parametrize("nombre, n", [
    ("Vacío", 1.0), ("Agua", 1.333), ("Diamante", 2.417), ("Vidrio crown (BK7)", 1.517)])
def test_valores_de_tabla(nombre, n):
    assert materiales.por_nombre(nombre).n == n


def test_material_desconocido():
    assert materiales.por_nombre("Kriptonita") is None
    assert materiales.por_nombre("") is None


def test_el_aire_no_se_confunde_con_el_vacio():
    # regresión: con tolerancia de 3 decimales el aire (1,0003) salía como «Vacío»
    assert materiales.nombre_de(1.0003) == "Aire"
    assert materiales.nombre_de(1.0) == "Vacío"


@pytest.mark.parametrize("n, esperado", [
    (1.33304, "Agua"),            # dentro de la tolerancia (redondea igual a 4 decimales)
    (1.33306, materiales.PERSONALIZADO),
    (1.5, materiales.PERSONALIZADO),
    (4.0, materiales.PERSONALIZADO),
])
def test_nombre_de_un_indice(n, esperado):
    assert materiales.nombre_de(n) == esperado


def test_mas_parecido():
    assert materiales.mas_parecido(1.52).nombre == "Vidrio crown (BK7)"
    assert materiales.mas_parecido(9.0).nombre == "Diamante"


# --- ejemplos ------------------------------------------------------------------------------

@pytest.mark.parametrize("ejemplo", ejemplos.EJEMPLOS, ids=lambda e: e.titulo)
def test_los_medios_del_ejemplo_existen_y_cuadran_con_su_indice(ejemplo):
    for nombre, n in ((ejemplo.medio1, ejemplo.datos.n1), (ejemplo.medio2, ejemplo.datos.n2)):
        material = materiales.por_nombre(nombre)
        assert material is not None, nombre
        assert material.n == n
        assert materiales.nombre_de(n) == nombre       # la lista de la ventana lo enseña


@pytest.mark.parametrize("ejemplo", ejemplos.EJEMPLOS, ids=lambda e: e.titulo)
def test_cada_ejemplo_se_puede_calcular(ejemplo):
    sol = resolver(ejemplo.datos, ejemplo.incognita)
    reflexion_total = any(palabra in ejemplo.titulo + ejemplo.idea for palabra in
                          ("Reflexión total", "rebota"))
    assert sol.estado is (Estado.REFLEXION_TOTAL if reflexion_total else Estado.OK)


def _ejemplo(titulo):
    return next(e for e in ejemplos.EJEMPLOS if e.titulo == titulo)


def test_las_cifras_que_citan_los_ejemplos_son_las_calculadas():
    agua = _ejemplo("Reflexión total en el agua")
    assert f"{ex.num(angulo_critico(agua.datos.n1, agua.datos.n2), 1)}°" in agua.idea      # 48,6°
    diamante = _ejemplo("Por qué brilla un diamante")
    assert f"{ex.num(angulo_critico(diamante.datos.n1, diamante.datos.n2), 1)}°" in diamante.idea
    fibra = _ejemplo("Fibra óptica")
    assert fibra.datos.theta1 > angulo_critico(fibra.datos.n1, fibra.datos.n2)


def test_el_ejemplo_de_brewster_esta_en_el_angulo_de_brewster():
    brewster = _ejemplo("Ángulo de Brewster")
    assert brewster.datos.theta1 == pytest.approx(
        angulo_brewster(brewster.datos.n1, brewster.datos.n2), abs=0.05)


def test_medir_el_indice_da_el_del_vidrio_crown():
    medir = _ejemplo("Medir el índice de un vidrio")
    sol = resolver(medir.datos, medir.incognita)
    assert sol.valor == pytest.approx(1.517, abs=1e-3)
    assert ex.resumen(sol)[1] == "Coincide con: vidrio crown (BK7)"


def test_del_agua_al_aire_se_aleja_y_del_aire_al_agua_se_acerca():
    assert ex.resumen(resolver(_ejemplo("Del agua al aire").datos, _ejemplo("Del agua al aire").incognita))[1] \
        == "El rayo se aleja de la normal"
    entra = _ejemplo("Del aire al agua")
    assert ex.resumen(resolver(entra.datos, entra.incognita))[1] == "El rayo se acerca a la normal"
