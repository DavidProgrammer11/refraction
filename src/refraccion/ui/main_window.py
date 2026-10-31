"""Ventana principal: los datos a la izquierda; el diagrama, el paso a paso y las
gráficas a la derecha. Todo se recalcula al momento, al escribir o al arrastrar un rayo.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, QStandardPaths, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSplitter,
    QTabWidget, QVBoxLayout, QWidget,
)

from .. import APP_NAME, ORG_NAME, __version__, db, ejemplos, exportar, materiales, paths
from .. import explicacion as ex
from ..optica import Datos, Incognita, Solucion, resolver
from . import colores as c
from . import informe
from .campos import CampoNumero
from .diagrama import Diagrama
from .grafica import contenido_fresnel, contenido_refraccion, grafica_fresnel, grafica_refraccion
from .historial import PanelHistorial
from .paso_a_paso import PasoAPaso

log = logging.getLogger(__name__)

ORDEN = (Incognita.THETA2, Incognita.THETA1, Incognita.N2, Incognita.N1)
DESCRIPCION = {
    Incognita.THETA2: "θ₂: hacia dónde sale el rayo",
    Incognita.THETA1: "θ₁: con qué ángulo tiene que llegar",
    Incognita.N2: "n₂: el índice del medio de abajo",
    Incognita.N1: "n₁: el índice del medio de arriba",
}
SE_CALCULA = "(se calcula)"
INICIAL = Datos(n1=1.0003, n2=1.333, theta1=40.0, theta2=28.84)


def _color(texto: str, color) -> str:
    return f'<span style="color:{color.name()};">{texto}</span>'


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn
        self.setWindowTitle(APP_NAME)
        self.incognita = Incognita.THETA2
        self.solucion: Solucion | None = None
        self.ejemplo: ejemplos.Ejemplo | None = None
        self.combos: dict[int, QComboBox] = {}
        self.campos: dict[Incognita, CampoNumero] = {}
        self._cargando = True
        self._construir()
        self._construir_menu()
        self._cargar_estado()
        self._cargando = False
        self.set_incognita(self.incognita, conservar=False)
        self.refrescar_historial()

    # ==================================================================
    # construcción
    # ==================================================================

    def _construir(self) -> None:
        central = QWidget(self)
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._cabecera())
        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(14, 12, 14, 12)
        cuerpo.setSpacing(14)
        cuerpo.addWidget(self._columna_datos(), 0)
        cuerpo.addWidget(self._zona_vista(), 1)
        raiz.addLayout(cuerpo, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Elige qué quieres calcular y cambia los datos o arrastra los rayos")

    def _cabecera(self) -> QFrame:
        barra = QFrame(self)
        barra.setObjectName("Cabecera")
        caja = QHBoxLayout(barra)
        caja.setContentsMargins(18, 10, 18, 10)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        marca = QLabel(APP_NAME, barra)
        marca.setObjectName("Marca")
        self.lema = QLabel("La ley de Snell, explicada y dibujada", barra)
        self.lema.setObjectName("Lema")
        textos.addWidget(marca)
        textos.addWidget(self.lema)
        caja.addLayout(textos)
        caja.addStretch(1)
        self.formula = QLabel(
            f'{_color("n₁ · sen θ₁", c.THETA1)} = {_color("n₂ · sen θ₂", c.THETA2)}', barra)
        self.formula.setObjectName("Formula")
        self.formula.setToolTip("Ley de Snell: lo que se conserva al cruzar es n · sen θ")
        caja.addWidget(self.formula)
        return barra

    def _columna_datos(self) -> QScrollArea:
        panel = QWidget()
        panel.setObjectName("Transparente")
        caja = QVBoxLayout(panel)
        caja.setContentsMargins(0, 0, 6, 0)
        caja.setSpacing(8)                  # con 10 ya no cabía a 1260 × 800 y salía la barra
        caja.addWidget(self._tarjeta_incognita())
        caja.addWidget(self._tarjeta_medio(1))
        caja.addWidget(self._tarjeta_medio(2))
        caja.addWidget(self._tarjeta_angulos())
        caja.addWidget(self._tarjeta_resultado())
        caja.addStretch(1)

        lienzo = QScrollArea(self)
        lienzo.setObjectName("Lienzo")
        lienzo.setWidget(panel)
        lienzo.setWidgetResizable(True)
        lienzo.setFrameShape(QFrame.Shape.NoFrame)
        lienzo.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # lo que pide el contenido, más la barra de desplazamiento por si el alto no llega
        barra = lienzo.verticalScrollBar().sizeHint().width()
        lienzo.setFixedWidth(max(312, panel.minimumSizeHint().width() + barra))
        return lienzo

    def _tarjeta_incognita(self) -> QGroupBox:
        tarjeta = QGroupBox("¿QUÉ QUIERES CALCULAR?")
        caja = QVBoxLayout(tarjeta)
        fila = QHBoxLayout()
        fila.setSpacing(0)
        self.grupo_incognita = QButtonGroup(self)
        self.botones_incognita: dict[Incognita, QPushButton] = {}
        for i, incognita in enumerate(ORDEN):
            boton = QPushButton(incognita.simbolo, tarjeta)
            boton.setObjectName("Segmento")
            boton.setProperty("posicion", "primero" if i == 0 else "ultimo" if i == len(ORDEN) - 1 else "")
            boton.setCheckable(True)
            boton.setToolTip(DESCRIPCION[incognita])
            boton.clicked.connect(lambda _=False, inc=incognita: self._elegir_incognita(inc))
            self.grupo_incognita.addButton(boton)
            self.botones_incognita[incognita] = boton
            fila.addWidget(boton)
        caja.addLayout(fila)
        self.descripcion = QLabel(tarjeta)
        self.descripcion.setObjectName("Pista")
        caja.addWidget(self.descripcion)
        return tarjeta

    def _tarjeta_medio(self, medio: int) -> QGroupBox:
        tarjeta = QGroupBox(f"MEDIO {medio} · {'ARRIBA' if medio == 1 else 'ABAJO'}")
        tarjeta.setObjectName(f"Medio{medio}")
        rejilla = QGridLayout(tarjeta)
        rejilla.setHorizontalSpacing(8)
        rejilla.setVerticalSpacing(4)
        combo = QComboBox(tarjeta)
        for material in materiales.MATERIALES:
            combo.addItem(material.nombre, material.nombre)
            combo.setItemData(combo.count() - 1, f"n = {ex.indice(material.n)}",
                              Qt.ItemDataRole.ToolTipRole)
        combo.addItem(materiales.PERSONALIZADO, materiales.PERSONALIZADO)
        combo.setPlaceholderText("Se calcula")
        # que el nombre más largo no ensanche la columna: si no cabe, se recorta
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(10)
        combo.setToolTip("Material del medio (índices para luz amarilla, 589 nm)")
        combo.activated.connect(lambda indice, m=medio: self._material_elegido(m, indice))
        campo = CampoNumero(0.1, 5.0, 4, 0.01, parent=tarjeta)
        campo.setFixedWidth(92)
        campo.cambiado.connect(self._dato_cambiado)
        simbolo = QLabel(f"n{'₁' if medio == 1 else '₂'}", tarjeta)
        simbolo.setObjectName(f"Simbolo{medio}")
        rejilla.addWidget(simbolo, 0, 0)
        rejilla.addWidget(combo, 0, 1)
        rejilla.addWidget(campo, 0, 2)
        rejilla.setColumnStretch(1, 1)
        if medio == 2:
            intercambiar = QPushButton("⇅  Intercambiar los medios", tarjeta)
            intercambiar.setObjectName("Enlace")
            intercambiar.setToolTip("La luz va al revés: del medio 2 al medio 1 (Ctrl+I)")
            intercambiar.clicked.connect(self.intercambiar_medios)
            rejilla.addWidget(intercambiar, 1, 0, 1, 3, Qt.AlignmentFlag.AlignRight)
        self.combos[medio] = combo
        self.campos[Incognita.N1 if medio == 1 else Incognita.N2] = campo
        return tarjeta

    def _tarjeta_angulos(self) -> QGroupBox:
        tarjeta = QGroupBox("ÁNGULOS · DESDE LA NORMAL")
        rejilla = QGridLayout(tarjeta)
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(8)
        for fila, (incognita, nombre, medio) in enumerate(
                ((Incognita.THETA1, "incidencia", 1), (Incognita.THETA2, "refracción", 2))):
            simbolo = QLabel(incognita.simbolo, tarjeta)
            simbolo.setObjectName(f"Simbolo{medio}")
            etiqueta = QLabel(nombre, tarjeta)
            etiqueta.setObjectName("Etiqueta")
            campo = CampoNumero(0.0, 90.0, 2, 1.0, "°", tarjeta)
            campo.cambiado.connect(self._dato_cambiado)
            rejilla.addWidget(simbolo, fila, 0)
            rejilla.addWidget(etiqueta, fila, 1)
            rejilla.addWidget(campo, fila, 2)
            self.campos[incognita] = campo
        rejilla.setColumnStretch(2, 1)
        return tarjeta

    def _tarjeta_resultado(self) -> QGroupBox:
        tarjeta = QGroupBox("RESULTADO")
        caja = QVBoxLayout(tarjeta)
        caja.setSpacing(4)
        self.titular = QLabel(tarjeta)
        self.titular.setObjectName("Titular")
        self.detalle = QLabel(tarjeta)
        self.detalle.setObjectName("Detalle")
        self.detalle.setWordWrap(True)
        self.boton_guardar = QPushButton("Guardar en el historial", tarjeta)
        self.boton_guardar.setObjectName("Primario")
        self.boton_guardar.setToolTip("Apunta este cálculo en la pestaña Historial (Ctrl+S)")
        self.boton_guardar.clicked.connect(self.guardar_en_historial)
        self.boton_pdf = QPushButton("Exportar el cálculo a PDF", tarjeta)
        self.boton_pdf.setObjectName("Enlace")
        self.boton_pdf.setToolTip("El diagrama y el paso a paso en un A4, para imprimir o entregar (Ctrl+P)")
        self.boton_pdf.clicked.connect(self.exportar_pdf)
        caja.addWidget(self.titular)
        caja.addWidget(self.detalle)
        caja.addSpacing(6)
        caja.addWidget(self.boton_guardar)
        caja.addWidget(self.boton_pdf, 0, Qt.AlignmentFlag.AlignHCenter)
        return tarjeta

    def _zona_vista(self) -> QSplitter:
        arriba = QWidget(self)
        arriba.setObjectName("Transparente")
        caja = QVBoxLayout(arriba)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(6)
        barra = QHBoxLayout()
        self.pista = QLabel(arriba)
        self.pista.setObjectName("Pista")
        self.pista.setWordWrap(True)
        self.ver_frentes = QCheckBox("Frentes de onda", arriba)
        self.ver_frentes.setToolTip("Las ondas de luz: se aprietan en el medio más lento y por eso giran")
        self.ver_frentes.setChecked(True)
        self.ver_frentes.toggled.connect(self._cambiar_frentes)
        self.ver_animacion = QCheckBox("Animar", arriba)
        self.ver_animacion.setChecked(True)
        self.ver_animacion.toggled.connect(self._cambiar_animacion)
        barra.addWidget(self.pista, 1)
        barra.addWidget(self.ver_frentes)
        barra.addWidget(self.ver_animacion)
        caja.addLayout(barra)
        self.diagrama = Diagrama(arriba)
        self.diagrama.anguloArrastrado.connect(self._angulo_arrastrado)
        caja.addWidget(self.diagrama, 1)

        self.pestanas = QTabWidget(self)
        self.pasos = PasoAPaso(self)
        self.pestanas.addTab(self.pasos, "Paso a paso")
        self.curva = grafica_refraccion(self)
        self.pestanas.addTab(self._con_pie(
            self.curva, "Cada punto de la curva es la ley de Snell para una incidencia. "
                        "Pasa el ratón por encima para leerla."), "Curva θ₂ (θ₁)")
        self.fresnel = grafica_fresnel(self)
        self.pestanas.addTab(self._con_pie(
            self.fresnel, "Cuanto más rasante llega la luz, más se refleja. Con luz polarizada p "
                          "el reflejo desaparece en el ángulo de Brewster."), "Luz reflejada")
        self.historial = PanelHistorial(self)
        self.historial.cargar.connect(self.cargar_calculo)
        self.historial.borrar.connect(self.borrar_calculo)
        self.historial.exportar.connect(self.exportar_historial)
        self.historial.vaciar.connect(self.vaciar_historial)
        self.pestanas.addTab(self.historial, "Historial")

        self.divisor = QSplitter(Qt.Orientation.Vertical, self)
        self.divisor.setChildrenCollapsible(False)
        self.divisor.addWidget(arriba)
        self.divisor.addWidget(self.pestanas)
        self.divisor.setStretchFactor(0, 3)
        self.divisor.setStretchFactor(1, 2)
        self.divisor.setSizes([440, 320])
        return self.divisor

    def _con_pie(self, grafica: QWidget, texto: str) -> QWidget:
        envoltorio = QWidget(self)
        envoltorio.setObjectName("Transparente")
        caja = QVBoxLayout(envoltorio)
        caja.setContentsMargins(0, 8, 0, 0)
        caja.setSpacing(6)
        pie = QLabel(texto, envoltorio)
        pie.setObjectName("Pista")
        pie.setWordWrap(True)
        caja.addWidget(pie)
        caja.addWidget(grafica, 1)
        return envoltorio

    def _construir_menu(self) -> None:
        def accion(menu, texto, funcion, atajo=None) -> QAction:
            a = QAction(texto, self)
            if atajo:
                a.setShortcut(QKeySequence(atajo))
            a.triggered.connect(lambda _=False: funcion())
            menu.addAction(a)
            return a

        archivo = self.menuBar().addMenu("&Archivo")
        accion(archivo, "Guardar en el historial", self.guardar_en_historial, "Ctrl+S")
        accion(archivo, "Exportar el cálculo a PDF…", self.exportar_pdf, "Ctrl+P")
        accion(archivo, "Guardar el diagrama como imagen…", self.guardar_imagen, "Ctrl+E")
        accion(archivo, "Copiar el diagrama", self.copiar_imagen, "Ctrl+Shift+C")
        accion(archivo, "Exportar el historial a Excel (CSV)…", self.exportar_historial)
        archivo.addSeparator()
        accion(archivo, "Abrir carpeta de datos", self.open_data_dir)
        archivo.addSeparator()
        accion(archivo, "Salir", self.close, "Ctrl+Q")

        menu_ejemplos = self.menuBar().addMenu("&Ejemplos")
        for ejemplo in ejemplos.EJEMPLOS:
            a = accion(menu_ejemplos, ejemplo.titulo, lambda e=ejemplo: self.aplicar_ejemplo(e))
            a.setStatusTip(ejemplo.idea)

        ver = self.menuBar().addMenu("&Ver")
        self.accion_frentes = QAction("Frentes de onda", self, checkable=True, checked=True)
        self.accion_frentes.toggled.connect(self.ver_frentes.setChecked)
        self.ver_frentes.toggled.connect(self.accion_frentes.setChecked)
        self.accion_animar = QAction("Animar las ondas", self, checkable=True, checked=True)
        self.accion_animar.toggled.connect(self.ver_animacion.setChecked)
        self.ver_animacion.toggled.connect(self.accion_animar.setChecked)
        ver.addAction(self.accion_frentes)
        ver.addAction(self.accion_animar)
        ver.addSeparator()
        accion(ver, "Intercambiar los medios", self.intercambiar_medios, "Ctrl+I")

        ayuda = self.menuBar().addMenu("A&yuda")
        accion(ayuda, "Cómo se usa", self.mostrar_ayuda, "F1")
        accion(ayuda, f"Acerca de {APP_NAME}", self.show_about)

    # ==================================================================
    # cálculo
    # ==================================================================

    def datos(self) -> Datos:
        return Datos(**{campo.value: self.campos[campo].valor() for campo in Incognita})

    def nombre_medio(self, medio: int) -> str:
        if self.campos[Incognita.N1 if medio == 1 else Incognita.N2].es_incognita:
            return SE_CALCULA
        return self.combos[medio].currentData() or materiales.PERSONALIZADO

    def recalcular(self) -> None:
        sol = resolver(self.datos(), self.incognita)
        self.solucion = sol
        self.campos[self.incognita].mostrar_resultado(
            ex.formatear(self.incognita, sol.valor) if sol.ok else "—")
        titular, detalle = ex.resumen(sol)
        self.titular.setText(titular)
        self.titular.setProperty("estado", "ok" if sol.ok else "aviso")
        self.titular.style().unpolish(self.titular)
        self.titular.style().polish(self.titular)
        self.detalle.setText(detalle)

        arrastra1 = self.incognita is not Incognita.THETA1
        arrastra2 = self.incognita is not Incognita.THETA2
        self.diagrama.set_arrastrables(arrastra1, arrastra2)
        self.diagrama.mostrar(sol, self.nombre_medio(1), self.nombre_medio(2))
        self.pasos.mostrar(sol)
        self.curva.mostrar(contenido_refraccion(sol))
        self.fresnel.mostrar(contenido_fresnel(sol))
        if self.ejemplo is None:
            self.pista.setText(self._pista_arrastre(arrastra1, arrastra2))

    @staticmethod
    def _pista_arrastre(arrastra1: bool, arrastra2: bool) -> str:
        if arrastra1 and arrastra2:
            return "Arrastra cualquiera de los dos rayos para cambiar su ángulo."
        if arrastra1:
            return "Arrastra el rayo incidente para cambiar θ₁."
        return "Arrastra el rayo refractado para cambiar θ₂."

    def set_incognita(self, incognita: Incognita, conservar: bool = True) -> None:
        """Cambia lo que se calcula. Con `conservar`, el resultado anterior pasa a ser dato."""
        if conservar and self.solucion is not None and self.solucion.ok:
            self.campos[self.incognita].poner(self.solucion.valor, emitir=False)
        self.incognita = incognita
        for campo, widget in self.campos.items():
            widget.set_incognita(campo is incognita)
        self.botones_incognita[incognita].setChecked(True)
        self.descripcion.setText(DESCRIPCION[incognita])
        self._sincronizar_materiales()
        self.recalcular()

    def _elegir_incognita(self, incognita: Incognita) -> None:
        self.ejemplo = None
        self.set_incognita(incognita)

    def _sincronizar_materiales(self) -> None:
        """Cada lista de materiales enseña el material de su índice (o «Personalizado»)."""
        for medio, combo in self.combos.items():
            campo = self.campos[Incognita.N1 if medio == 1 else Incognita.N2]
            bloqueado = combo.blockSignals(True)
            if campo.es_incognita:
                combo.setCurrentIndex(-1)
                combo.setEnabled(False)
            else:
                combo.setEnabled(True)
                combo.setCurrentIndex(combo.findData(materiales.nombre_de(campo.valor())))
            combo.blockSignals(bloqueado)

    def _dato_cambiado(self, _valor: float = 0.0) -> None:
        if self._cargando:
            return
        self.ejemplo = None
        self._sincronizar_materiales()
        self.recalcular()

    def _material_elegido(self, medio: int, indice: int) -> None:
        material = materiales.por_nombre(self.combos[medio].itemData(indice))
        if material is not None:
            self.campos[Incognita.N1 if medio == 1 else Incognita.N2].poner(material.n)

    def _angulo_arrastrado(self, medio: int, grados: float) -> None:
        campo = self.campos[Incognita.THETA1 if medio == 1 else Incognita.THETA2]
        if not campo.es_incognita:
            campo.poner(grados)

    def _poner_datos(self, datos: Datos, incognita: Incognita) -> None:
        self._cargando = True
        for campo in Incognita:
            if campo is not incognita:
                self.campos[campo].poner(datos.valor(campo))
        self._cargando = False
        self.set_incognita(incognita, conservar=False)

    def aplicar_ejemplo(self, ejemplo: ejemplos.Ejemplo) -> None:
        self.ejemplo = ejemplo
        self._poner_datos(ejemplo.datos, ejemplo.incognita)
        self.pista.setText(f"<b>{ejemplo.titulo}.</b> {ejemplo.idea}")
        self.pestanas.setCurrentWidget(self.pasos)
        self.statusBar().showMessage(f"Ejemplo: {ejemplo.titulo}", 6000)

    def intercambiar_medios(self) -> None:
        """La luz al revés: el medio 1 pasa abajo y el 2 arriba."""
        if self.solucion is not None and self.solucion.ok:
            self.campos[self.incognita].poner(self.solucion.valor, emitir=False)
        n1, n2 = self.campos[Incognita.N1].valor(), self.campos[Incognita.N2].valor()
        self._cargando = True
        self.campos[Incognita.N1].poner(n2)
        self.campos[Incognita.N2].poner(n1)
        self._cargando = False
        self.ejemplo = None
        otra = {Incognita.N1: Incognita.N2, Incognita.N2: Incognita.N1}
        self.set_incognita(otra.get(self.incognita, self.incognita), conservar=False)
        self.statusBar().showMessage("Medios intercambiados", 4000)

    # ==================================================================
    # vista
    # ==================================================================

    def _cambiar_frentes(self, activo: bool) -> None:
        self.diagrama.set_frentes(activo)
        self.ver_animacion.setEnabled(activo)

    def _cambiar_animacion(self, activo: bool) -> None:
        self.diagrama.set_animar(activo)

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self._adaptar()

    def _adaptar(self) -> None:
        """En ventanas estrechas se esconde lo accesorio, nunca los datos."""
        ancho = self.width()
        self.formula.setVisible(ancho >= 1020)
        self.lema.setVisible(ancho >= 860)

    # ==================================================================
    # historial
    # ==================================================================

    def refrescar_historial(self) -> None:
        self.historial.mostrar(db.listar_calculos(self.conn))

    def guardar_en_historial(self) -> None:
        db.guardar_calculo(self.conn, self.solucion, self.nombre_medio(1), self.nombre_medio(2))
        self.refrescar_historial()
        self.statusBar().showMessage(f"Guardado en el historial: {ex.resumen(self.solucion)[0]}", 5000)

    def cargar_calculo(self, calculo_id: int) -> None:
        fila = db.leer_calculo(self.conn, calculo_id)
        if fila is None:
            return
        datos, incognita = db.datos_de(fila)
        self.ejemplo = None
        self._poner_datos(datos, incognita)
        self.statusBar().showMessage(f"Cálculo del {fila['creado']} cargado", 5000)

    def borrar_calculo(self, calculo_id: int) -> None:
        db.borrar_calculo(self.conn, calculo_id)
        self.refrescar_historial()

    def vaciar_historial(self) -> None:
        respuesta = QMessageBox.question(
            self, "Vaciar el historial",
            "¿Borrar todos los cálculos guardados? No se puede deshacer.")
        if respuesta == QMessageBox.StandardButton.Yes:
            db.vaciar_historial(self.conn)
            self.refrescar_historial()

    # ==================================================================
    # exportar
    # ==================================================================

    def _carpeta_exportar(self) -> str:
        defecto = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        carpeta = db.leer_ajuste(self.conn, "carpeta_exportar", defecto)
        return carpeta if isinstance(carpeta, str) and Path(carpeta).is_dir() else defecto

    def _pedir_ruta(self, titulo: str, nombre: str, filtro: str) -> Path | None:
        ruta, _ = QFileDialog.getSaveFileName(
            self, titulo, str(Path(self._carpeta_exportar()) / nombre), filtro)
        if not ruta:
            return None
        ruta = Path(ruta)
        db.guardar_ajuste(self.conn, "carpeta_exportar", str(ruta.parent))
        return ruta

    def guardar_imagen(self) -> None:
        ruta = self._pedir_ruta("Guardar el diagrama", "Refracción.png", "Imagen PNG (*.png)")
        if ruta is None:
            return
        if ruta.suffix.lower() != ".png":
            ruta = ruta.with_suffix(".png")
        if self.diagrama.imagen(2.0).save(str(ruta), "PNG"):
            self.statusBar().showMessage(f"Diagrama guardado en {ruta}", 6000)
        else:
            QMessageBox.warning(self, "No se pudo guardar",
                                f"No se pudo guardar la imagen en:\n{ruta}")

    def exportar_pdf(self) -> None:
        ruta = self._pedir_ruta("Exportar el cálculo a PDF", informe.nombre_de_archivo(self.solucion),
                                "Documento PDF (*.pdf)")
        if ruta is None:
            return
        if ruta.suffix.lower() != ".pdf":
            ruta = ruta.with_suffix(".pdf")
        # el diagrama con un tamaño fijo, apaisado, para que todos los PDF salgan iguales
        imagen = self.diagrama.imagen(2.5, QSize(900, 480))
        contenido = informe.pdf(self.solucion, self.nombre_medio(1), self.nombre_medio(2), imagen,
                                informe.imagen_de_curva(self.solucion))
        try:
            ruta.write_bytes(contenido)
        except OSError as error:
            log.warning("No se pudo exportar el PDF a %s: %s", ruta, error)
            QMessageBox.warning(self, "No se pudo exportar",
                                f"No se pudo escribir el archivo:\n{ruta}\n\n"
                                "Si está abierto en un visor de PDF, ciérralo y vuelve a probar.")
            return
        self.statusBar().showMessage(f"PDF guardado en {ruta}", 6000)

    def copiar_imagen(self) -> None:
        QGuiApplication.clipboard().setImage(self.diagrama.imagen(2.0))
        self.statusBar().showMessage("Diagrama copiado: pégalo en Word, PowerPoint o un correo", 5000)

    def exportar_historial(self) -> None:
        filas = db.listar_calculos(self.conn)
        if not filas:
            self.statusBar().showMessage("El historial está vacío", 4000)
            return
        ruta = self._pedir_ruta("Exportar el historial", "Historial de refracción.csv",
                                "CSV para Excel (*.csv)")
        if ruta is None:
            return
        if ruta.suffix.lower() != ".csv":
            ruta = ruta.with_suffix(".csv")
        try:
            ruta.write_bytes(exportar.historial_csv(filas))
        except OSError as error:
            log.warning("No se pudo exportar el historial a %s: %s", ruta, error)
            QMessageBox.warning(self, "No se pudo exportar",
                                f"No se pudo escribir el archivo:\n{ruta}\n\n"
                                "Si está abierto en Excel, ciérralo y vuelve a probar.")
            return
        self.statusBar().showMessage(f"{len(filas)} cálculos exportados a {ruta}", 6000)

    def open_data_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.data_dir())))

    # ==================================================================
    # ayuda
    # ==================================================================

    def mostrar_ayuda(self) -> None:
        QMessageBox.information(self, "Cómo se usa", (
            "<p><b>1.</b> Elige arriba a la izquierda qué quieres calcular.</p>"
            "<p><b>2.</b> Escribe los otros tres datos o elige los materiales.</p>"
            "<p><b>3.</b> Arrastra los rayos del dibujo para cambiar los ángulos: todo se "
            "recalcula al momento.</p>"
            "<p><b>4.</b> Debajo tienes el cálculo paso a paso con tus números, la curva de "
            "la ley de Snell y cuánta luz se refleja.</p>"
            f"<p>Los colores son siempre los mismos: {_color('θ₁ y n₁', c.THETA1)} en azul, "
            f"{_color('θ₂ y n₂', c.THETA2)} en verde, la luz en naranja y "
            f"{_color('el ángulo crítico', c.CRITICO)} en rojo.</p>"
            "<p>En el menú <b>Ejemplos</b> hay situaciones reales para empezar.</p>"))

    def about_text(self) -> str:
        return (f"<b>{APP_NAME}</b> {__version__}<br>La ley de Snell, explicada y dibujada."
                f"<br><br>Desarrollado por {ORG_NAME}")

    def show_about(self) -> None:
        QMessageBox.about(self, f"Acerca de {APP_NAME}", self.about_text())

    # ==================================================================
    # estado entre sesiones
    # ==================================================================

    def _cargar_estado(self) -> None:
        estado = db.leer_ajuste(self.conn, "estado", {})
        if not isinstance(estado, dict):
            estado = {}
        try:
            self.incognita = Incognita(estado.get("incognita", Incognita.THETA2.value))
        except ValueError:
            self.incognita = Incognita.THETA2
        for campo in Incognita:
            valor = estado.get(campo.value, INICIAL.valor(campo))
            if not isinstance(valor, (int, float)) or isinstance(valor, bool):
                valor = INICIAL.valor(campo)
            self.campos[campo].poner(float(valor), emitir=False)
        self.ver_frentes.setChecked(bool(estado.get("frentes", True)))
        self.ver_animacion.setChecked(bool(estado.get("animar", True)))
        pestana = estado.get("pestana", 0)
        if isinstance(pestana, int) and 0 <= pestana < self.pestanas.count():
            self.pestanas.setCurrentIndex(pestana)
        divisor = estado.get("divisor")
        if isinstance(divisor, list) and len(divisor) == 2 and all(isinstance(x, int) for x in divisor):
            self.divisor.setSizes(divisor)
        geometria = db.leer_ajuste(self.conn, "geometria")
        if not (isinstance(geometria, str) and self.restoreGeometry(QByteArray.fromBase64(geometria.encode()))):
            self.resize(1260, 800)

    def guardar_estado(self) -> None:
        estado = {campo.value: self.campos[campo].valor() for campo in Incognita}
        if self.solucion is not None and self.solucion.ok:
            estado[self.incognita.value] = self.solucion.valor
        estado.update(incognita=self.incognita.value,
                      frentes=self.ver_frentes.isChecked(),
                      animar=self.ver_animacion.isChecked(),
                      pestana=self.pestanas.currentIndex(),
                      divisor=self.divisor.sizes())
        db.guardar_ajuste(self.conn, "estado", estado)
        db.guardar_ajuste(self.conn, "geometria", self.saveGeometry().toBase64().data().decode())

    def closeEvent(self, evento) -> None:
        try:
            self.guardar_estado()
        except sqlite3.Error:
            log.exception("No se pudo guardar el estado de la ventana")
        super().closeEvent(evento)
