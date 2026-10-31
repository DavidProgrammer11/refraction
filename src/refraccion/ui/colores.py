"""Colores de la app. Los mismos en el diagrama, las gráficas y el paso a paso,
para que θ₁ se vea siempre azul y θ₂ siempre verde y se reconozcan de un vistazo."""
from PySide6.QtGui import QColor

FONDO = QColor("#F4F6F8")
TARJETA = QColor("#FFFFFF")
BORDE = QColor("#DCE3EC")
TEXTO = QColor("#1F2933")
GRIS = QColor("#6B7280")
GRIS_CLARO = QColor("#A7B0BC")
PRIMARIO = QColor("#0070C0")

RAYO = QColor("#E8590C")            # la luz
THETA1 = QColor("#0070C0")          # θ₁ y n₁
THETA2 = QColor("#12805C")          # θ₂ y n₂
CRITICO = QColor("#C92A2A")         # ángulo crítico y reflexión total
BREWSTER = QColor("#7048E8")
MEDIO = QColor("#0070C0")           # el tono de los medios, más intenso cuanto mayor es n


def medio(n: float) -> QColor:
    """Color de fondo de un medio: casi blanco el vacío, azul más intenso cuanto más denso."""
    densidad = max(0.0, min(1.0, (n - 1.0) / 1.5))
    color = QColor(MEDIO)
    color.setAlphaF(0.04 + 0.30 * densidad)
    return color


def con_alfa(color: QColor, alfa: float) -> QColor:
    copia = QColor(color)
    copia.setAlphaF(max(0.0, min(1.0, alfa)))
    return copia
