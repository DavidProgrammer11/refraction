"""Pestaña del historial: los cálculos guardados, para volver a ellos o pasarlos a Excel."""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import explicacion as ex
from ..db import datos_de
from ..optica import Estado, Incognita, Solucion

COLUMNAS = ("Fecha", "Calculado", "Medio 1", "n₁", "θ₁", "Medio 2", "n₂", "θ₂", "Resultado")


def _celda(texto: str, dato: int | None = None, derecha: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(texto)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if dato is not None:
        item.setData(Qt.ItemDataRole.UserRole, dato)
    if derecha:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item


class PanelHistorial(QWidget):
    cargar = Signal(int)            # id del cálculo
    borrar = Signal(int)
    exportar = Signal()
    vaciar = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Transparente")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 8, 0, 0)
        caja.setSpacing(8)

        self.tabla = QTableWidget(0, len(COLUMNAS), self)
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setStretchLastSection(True)
        self.tabla.itemDoubleClicked.connect(self._doble_clic)
        self.tabla.itemSelectionChanged.connect(self._actualizar_botones)

        self.vacio = QLabel("Todavía no hay cálculos guardados. Pulsa «Guardar en el historial» "
                            "(Ctrl+S) para apuntar el que tienes en pantalla.", self)
        self.vacio.setObjectName("Pista")
        self.vacio.setWordWrap(True)

        fila = QHBoxLayout()
        self.boton_cargar = QPushButton("Volver a este cálculo", self)
        self.boton_borrar = QPushButton("Borrar", self)
        self.boton_exportar = QPushButton("Exportar a Excel (CSV)…", self)
        self.boton_vaciar = QPushButton("Vaciar historial…", self)
        for boton in (self.boton_cargar, self.boton_borrar, self.boton_exportar, self.boton_vaciar):
            boton.setObjectName("Menudo")
        self.boton_cargar.clicked.connect(lambda: self._emitir(self.cargar))
        self.boton_borrar.clicked.connect(lambda: self._emitir(self.borrar))
        self.boton_exportar.clicked.connect(self.exportar.emit)
        self.boton_vaciar.clicked.connect(self.vaciar.emit)
        fila.addWidget(self.boton_cargar)
        fila.addWidget(self.boton_borrar)
        fila.addStretch(1)
        fila.addWidget(self.boton_exportar)
        fila.addWidget(self.boton_vaciar)

        caja.addWidget(self.vacio)
        caja.addWidget(self.tabla, 1)
        caja.addLayout(fila)
        self._actualizar_botones()

    def seleccionado(self) -> int | None:
        filas = self.tabla.selectionModel().selectedRows()
        if not filas:
            return None
        return self.tabla.item(filas[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def _doble_clic(self, item: QTableWidgetItem) -> None:
        # la fila pulsada, aunque la selección esté en otra (o en ninguna)
        self.cargar.emit(self.tabla.item(item.row(), 0).data(Qt.ItemDataRole.UserRole))

    def _emitir(self, senal) -> None:
        calculo = self.seleccionado()
        if calculo is not None:
            senal.emit(calculo)

    def _actualizar_botones(self) -> None:
        hay_seleccion = self.seleccionado() is not None
        self.boton_cargar.setEnabled(hay_seleccion)
        self.boton_borrar.setEnabled(hay_seleccion)
        hay_filas = self.tabla.rowCount() > 0
        self.boton_exportar.setEnabled(hay_filas)
        self.boton_vaciar.setEnabled(hay_filas)
        self.vacio.setVisible(not hay_filas)

    def mostrar(self, filas: list[sqlite3.Row]) -> None:
        self.tabla.setRowCount(0)
        for fila in filas:
            datos, incognita = datos_de(fila)
            sol = Solucion(incognita, datos, Estado(fila["estado"]), fila[incognita.value])

            def numero(campo: Incognita) -> str:
                valor = fila[campo.value]
                return "—" if valor is None else ex.formatear(campo, valor)

            i = self.tabla.rowCount()
            self.tabla.insertRow(i)
            celdas = (
                _celda(fila["creado"], fila["id"]),
                _celda(incognita.simbolo),
                _celda(fila["medio1"]),
                _celda(numero(Incognita.N1), derecha=True),
                _celda(numero(Incognita.THETA1), derecha=True),
                _celda(fila["medio2"]),
                _celda(numero(Incognita.N2), derecha=True),
                _celda(numero(Incognita.THETA2), derecha=True),
                _celda(ex.resumen(sol)[0]),
            )
            for columna, celda in enumerate(celdas):
                self.tabla.setItem(i, columna, celda)
        self._actualizar_botones()
