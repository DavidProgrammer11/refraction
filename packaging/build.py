"""Genera el ejecutable con PyInstaller y, opcionalmente, el instalador con Inno Setup.

Uso (desde la raíz del proyecto, con el entorno activado):
    python packaging/build.py               -> dist/Refraccion/Refraccion.exe
    python packaging/build.py --instalador  -> además dist/Refraccion-<versión>-setup.exe

La versión se lee de src/refraccion/__init__.py; no hay que cambiarla en ningún otro sitio.
Al acabar se quitan las piezas de Qt que la app no usa y se arranca el ejecutable con
--comprobar: si falta algo que sí hacía falta, la compilación falla en vez de entregarse.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAQUETE = RAIZ / "src" / "refraccion"
NOMBRE_EXE = "Refraccion"
ISCC_RUTAS = [
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
]

# Módulos de Python que la app no importa: sin ellos tampoco entran sus DLL (OpenSSL, red, QML)
EXCLUIDOS = [
    "ssl", "_ssl", "_hashlib",                      # sin red ni cifrado (hashlib tira de lo suyo)
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
]

# Lo que PyInstaller arrastra igualmente por las dependencias de los plugins de Qt. Se
# comprobó con objdump qué DLL necesita cada pieza que sí se usa (plataforma Windows,
# widgets, SVG); el resto sobra. La app lo dibuja todo con QPainter: sin OpenGL ni QML.
SOBRAN = [
    "PySide6/opengl32sw.dll",                       # 20 MB: OpenGL por software
    "PySide6/plugins/platforminputcontexts",        # el teclado virtual, que arrastra QML y Quick
    "PySide6/Qt6VirtualKeyboard.dll", "PySide6/Qt6Quick.dll", "PySide6/Qt6Qml.dll",
    "PySide6/Qt6QmlModels.dll", "PySide6/Qt6QmlMeta.dll", "PySide6/Qt6QmlWorkerScript.dll",
    "PySide6/Qt6OpenGL.dll",
    "PySide6/Qt6Pdf.dll", "PySide6/plugins/imageformats/qpdf.dll",   # leer PDF; escribirlos es de QtGui
    "PySide6/Qt6Network.dll", "PySide6/plugins/tls", "PySide6/plugins/networkinformation",
    "libcrypto-3-x64.dll", "libssl-3-x64.dll",      # el OpenSSL de Qt, solo para la red
    "PySide6/plugins/generic",                      # pantallas táctiles TUIO
    "PySide6/plugins/platforms/qdirect2d.dll", "PySide6/plugins/platforms/qminimal.dll",
    # formatos de imagen que no se leen (quedan SVG, para las casillas, e ICO)
    "PySide6/plugins/imageformats/qgif.dll", "PySide6/plugins/imageformats/qicns.dll",
    "PySide6/plugins/imageformats/qjpeg.dll", "PySide6/plugins/imageformats/qtga.dll",
    "PySide6/plugins/imageformats/qtiff.dll", "PySide6/plugins/imageformats/qwbmp.dll",
    "PySide6/plugins/imageformats/qwebp.dll",
]
TRADUCCIONES = {"qtbase_es.qm"}                     # los botones de Qt en español («Sí», «Cancelar»)


def leer_metadatos() -> tuple[str, str]:
    """Devuelve (versión, nombre visible) sin importar el paquete (no necesita Qt)."""
    texto = (PAQUETE / "__init__.py").read_text(encoding="utf-8")
    version = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', texto, re.M).group(1)
    nombre = re.search(r'^APP_NAME\s*=\s*["\']([^"\']+)["\']', texto, re.M).group(1)
    return version, nombre


def escribir_version_windows(destino: Path, version: str, nombre: str) -> Path:
    """Metadatos del .exe (Propiedades › Detalles en Windows): editor DZM y versión."""
    numeros = [int(n) for n in re.findall(r"\d+", version)[:3]]
    numeros += [0] * (4 - len(numeros))
    tupla = tuple(numeros)
    contenido = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tupla}, prodvers={tupla}),
  kids=[
    StringFileInfo([
      StringTable('0C0A04B0', [
        StringStruct('CompanyName', 'DZM'),
        StringStruct('FileDescription', {nombre!r}),
        StringStruct('FileVersion', {version!r}),
        StringStruct('InternalName', {NOMBRE_EXE!r}),
        StringStruct('OriginalFilename', {NOMBRE_EXE + '.exe'!r}),
        StringStruct('ProductName', {nombre!r}),
        StringStruct('ProductVersion', {version!r}),
        StringStruct('LegalCopyright', 'DZM'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0C0A, 1200])])
  ]
)
"""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")
    return destino


def borrar(carpeta: Path) -> None:
    """Como shutil.rmtree, pero quitando antes el «solo lectura» de Windows, que impide borrar.

    Una carpeta de build/ marcada así hacía fallar el --clean de PyInstaller con «Acceso denegado».
    """
    def quitar_solo_lectura(funcion, ruta, _error):
        os.chmod(ruta, stat.S_IWRITE)
        funcion(ruta)

    if not carpeta.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(carpeta, onexc=quitar_solo_lectura)
    else:  # pragma: no cover - Python 3.10 y 3.11
        shutil.rmtree(carpeta, onerror=quitar_solo_lectura)


def en_uso(exe: Path) -> bool:
    """Windows no deja abrir para escribir un .exe que se está ejecutando: así se sabe si está abierto."""
    if not exe.exists():
        return False
    try:
        with open(exe, "r+b"):
            return False
    except PermissionError:
        return True


def construir_ejecutable(version: str, nombre: str) -> Path:
    import PyInstaller.__main__  # importado aquí: solo hace falta al empaquetar

    trabajo = RAIZ / "build"
    destino = RAIZ / "dist" / NOMBRE_EXE
    if en_uso(destino / f"{NOMBRE_EXE}.exe"):
        sys.exit(f"{NOMBRE_EXE}.exe está abierto desde {destino}: ciérralo y vuelve a compilar.")
    borrar(trabajo / NOMBRE_EXE)                    # lo que --clean no siempre consigue borrar
    borrar(destino)
    args = [
        str(RAIZ / "run.py"),
        "--name", NOMBRE_EXE,
        "--windowed",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--paths", str(RAIZ / "src"),
        "--add-data", f"{PAQUETE / 'resources'}{os.pathsep}refraccion/resources",
        "--distpath", str(RAIZ / "dist"),
        "--workpath", str(trabajo),
        "--specpath", str(trabajo),
    ]
    icono = PAQUETE / "resources" / "icons" / "app.ico"
    if icono.exists():
        args += ["--icon", str(icono)]
    else:
        print("Aviso: falta resources/icons/app.ico; el ejecutable tendrá el icono por defecto.")
    if sys.platform == "win32":
        args += ["--version-file", str(escribir_version_windows(trabajo / "version_info.txt", version, nombre))]

    args += [arg for modulo in EXCLUIDOS for arg in ("--exclude-module", modulo)]

    try:
        PyInstaller.__main__.run(args)
    except PermissionError as error:
        sys.exit(f"No se pudo escribir la compilación ({error}).\n"
                 f"¿Está abierto {NOMBRE_EXE}.exe desde dist? Ciérralo y vuelve a probar.")
    return RAIZ / "dist" / NOMBRE_EXE


def aligerar(carpeta: Path) -> int:
    """Quita lo que PyInstaller arrastra y la app no usa. Devuelve los bytes ahorrados."""
    interna = carpeta / "_internal"
    ahorrado = 0
    candidatos = [interna / relativa for relativa in SOBRAN]
    traducciones = interna / "PySide6" / "translations"
    if traducciones.is_dir():
        candidatos += [qm for qm in traducciones.iterdir() if qm.name not in TRADUCCIONES]
    for ruta in candidatos:
        if ruta.is_dir():
            ahorrado += sum(f.stat().st_size for f in ruta.rglob("*") if f.is_file())
            shutil.rmtree(ruta)
        elif ruta.is_file():
            ahorrado += ruta.stat().st_size
            ruta.unlink()
    return ahorrado


def comprobar_ejecutable(carpeta: Path) -> None:
    """Arranca el .exe con --comprobar: si al aligerar sobró algo que hacía falta, aquí se ve."""
    with tempfile.TemporaryDirectory() as temporal:
        captura = Path(temporal) / "comprobacion.png"
        resultado = subprocess.run([str(carpeta / f"{NOMBRE_EXE}.exe"), "--comprobar", str(captura)],
                                   timeout=120)
        motivos = captura.with_suffix(".txt")
        if resultado.returncode != 0 or not captura.exists():
            detalle = motivos.read_text(encoding="utf-8") if motivos.exists() else "sin detalles"
            sys.exit(f"El ejecutable no pasa su comprobación (código {resultado.returncode}):\n{detalle}")
    print("Comprobación del ejecutable: bien (ventana, SVG, traducción, PDF y CSV)")


def tamano(carpeta: Path) -> float:
    return sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file()) / 1048576


def construir_instalador(version: str) -> None:
    iscc = shutil.which("iscc") or next((str(r) for r in ISCC_RUTAS if r.exists()), None)
    if iscc is None:
        sys.exit("No se encuentra Inno Setup 6 (ISCC.exe). Instálalo desde https://jrsoftware.org/isinfo.php")
    subprocess.run([iscc, f"/DMyAppVersion={version}", str(RAIZ / "packaging" / "installer.iss")], check=True)
    print(f"Instalador: {RAIZ / 'dist' / f'{NOMBRE_EXE}-{version}-setup.exe'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Empaqueta la app para entregarla.")
    parser.add_argument("--instalador", action="store_true", help="Compilar también el instalador (Windows)")
    parser.add_argument("--sin-comprobar", action="store_true",
                        help="No arrancar el ejecutable al acabar para comprobarlo")
    args = parser.parse_args()

    version, nombre = leer_metadatos()
    print(f"Empaquetando {nombre} {version}")
    carpeta = construir_ejecutable(version, nombre)
    ahorrado = aligerar(carpeta) / 1048576
    print(f"Ejecutable en: {carpeta} ({tamano(carpeta):.0f} MB; {ahorrado:.0f} MB quitados)")
    if not args.sin_comprobar:
        comprobar_ejecutable(carpeta)
    if args.instalador:
        construir_instalador(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
