"""Campos de datos: un número que se escribe o, si es la incógnita, el resultado."""
from __future__ import annotations

from PySide6.QtCore import QLocale, Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QLineEdit, QStackedLayout, QWidget

ESPANOL = QLocale(QLocale.Language.Spanish, QLocale.Country.Spain)


class SpinDecimal(QDoubleSpinBox):
    """Acepta el punto como coma decimal: «1.5» y «1,5» valen lo mismo.

    En español el punto es el separador de miles y Qt lo descartaría («1.5» → 1);
    aquí no hay números de cuatro cifras, así que el punto siempre es decimal.
    """

    def validate(self, texto: str, posicion: int):
        return super().validate(texto.replace(".", ","), posicion)

    def valueFromText(self, texto: str) -> float:
        return super().valueFromText(texto.replace(".", ","))


class CampoNumero(QWidget):
    """Casilla numérica que se convierte en «calculado» cuando es la incógnita."""

    cambiado = Signal(float)

    def __init__(self, minimo: float, maximo: float, decimales: int, paso: float,
                 sufijo: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Transparente")
        self.spin = SpinDecimal(self)
        self.spin.setLocale(ESPANOL)                     # coma decimal aunque Windows esté en inglés
        self.spin.setRange(minimo, maximo)
        self.spin.setDecimals(decimales)
        self.spin.setSingleStep(paso)
        self.spin.setSuffix(sufijo)
        # las flechas quedan invisibles en el QSS: se escribe, se usa la rueda o el teclado,
        # o se arrastra el rayo (con NoButtons, Qt 6.12 deja el texto sin ancho)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin.valueChanged.connect(self.cambiado.emit)

        self.resultado = QLineEdit(self)
        self.resultado.setObjectName("Calculado")
        self.resultado.setReadOnly(True)
        self.resultado.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.resultado.setToolTip("Este valor lo calcula la app con la ley de Snell")

        self._pila = QStackedLayout(self)
        self._pila.setContentsMargins(0, 0, 0, 0)
        self._pila.addWidget(self.spin)
        self._pila.addWidget(self.resultado)

    @property
    def es_incognita(self) -> bool:
        return self._pila.currentWidget() is self.resultado

    def set_incognita(self, es: bool) -> None:
        self._pila.setCurrentWidget(self.resultado if es else self.spin)

    def valor(self) -> float:
        return self.spin.value()

    def poner(self, valor: float, emitir: bool = True) -> None:
        bloqueado = self.spin.blockSignals(not emitir)
        self.spin.setValue(valor)
        self.spin.blockSignals(bloqueado)

    def mostrar_resultado(self, texto: str) -> None:
        self.resultado.setText(texto)
