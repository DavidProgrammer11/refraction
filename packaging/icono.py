"""Dibuja el icono de la app (un rayo que se dobla al cruzar dos medios).

Uso: python packaging/icono.py  ->  src/refraccion/resources/icons/app.png y app.ico
El .ico lleva dentro varios PNG (16, 24, 32, 48, 64 y 256 px), como piden Windows e Inno Setup.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen

DESTINO = Path(__file__).resolve().parents[1] / "src" / "refraccion" / "resources" / "icons"
TAMANOS = (16, 24, 32, 48, 64, 256)


def dibujar(lado: int) -> QImage:
    img = QImage(lado, lado, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(lado / 256, lado / 256)
    marco = QPainterPath()
    marco.addRoundedRect(QRectF(8, 8, 240, 240), 52, 52)
    p.setClipPath(marco)
    p.fillRect(QRectF(0, 0, 256, 128), QColor("#E4F1FB"))
    p.fillRect(QRectF(0, 128, 256, 128), QColor("#0070C0"))
    p.setClipping(False)
    if lado >= 48:
        p.setPen(QPen(QColor(31, 41, 51, 90), 6, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(128, 34), QPointF(128, 222))
    rayo = QPen(QColor("#E8590C"), 22 if lado >= 32 else 30)
    rayo.setCapStyle(Qt.PenCapStyle.RoundCap)
    rayo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(rayo)
    p.setBrush(Qt.BrushStyle.NoBrush)
    camino = QPainterPath(QPointF(52, 44))
    camino.lineTo(128, 128)
    camino.lineTo(168, 214)
    p.drawPath(camino)
    if lado >= 32:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(128, 128), 13, 13)
    p.end()
    return img


def png(img: QImage) -> bytes:
    datos = QByteArray()
    buffer = QBuffer(datos)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    return bytes(datos)


def ico(imagenes: list[QImage]) -> bytes:
    """Archivo .ico con cada tamaño guardado como PNG (válido desde Windows Vista)."""
    cuerpos = [png(img) for img in imagenes]
    cabecera = struct.pack("<HHH", 0, 1, len(cuerpos))
    entradas, desplazamiento = b"", 6 + 16 * len(cuerpos)
    for img, cuerpo in zip(imagenes, cuerpos):
        lado = img.width() if img.width() < 256 else 0          # 0 significa 256
        entradas += struct.pack("<BBBBHHII", lado, lado, 0, 0, 1, 32, len(cuerpo), desplazamiento)
        desplazamiento += len(cuerpo)
    return cabecera + entradas + b"".join(cuerpos)


def main() -> int:
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    DESTINO.mkdir(parents=True, exist_ok=True)
    dibujar(256).save(str(DESTINO / "app.png"), "PNG")
    (DESTINO / "app.ico").write_bytes(ico([dibujar(t) for t in TAMANOS]))
    print(f"Iconos en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
