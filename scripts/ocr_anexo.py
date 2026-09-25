#!/usr/bin/env python3
"""
Transcribe un anexo de Licencias No Automáticas (páginas en imagen) a una lista
de posiciones arancelarias NCM, validada contra el nomenclador oficial.

    python3 scripts/ocr_anexo.py <dir-con-jpgs> <salida.txt> [ncm-valido.txt]

Usa únicamente la biblioteca estándar de Python, de modo que corre igual en
Linux, macOS y Windows. Lo único externo que necesita es el motor de
reconocimiento.

Comprobado sobre las 52 páginas del anexo de agosto de 2022: devuelve **las
mismas 1.492 posiciones** que la transcripción incluida en el paquete, sin una
sola diferencia. `auditar_ocr.py --rehacer` rehace esa comprobación.

ESTE PASO ES OPCIONAL. La cadena principal no lo necesita: la transcripción ya
viene hecha dentro del paquete, porque el OCR no da el mismo resultado entre
versiones del motor y congelarla es lo que hace reproducible al resto. Esto
existe para quien quiera auditar la transcripción contra las imágenes.

Para correrlo hace falta el programa `tesseract` (o Docker, como alternativa).
No se instala solo, y es deliberado: instalar software en la máquina de otro
requiere privilegios de administrador y depende del sistema operativo. Un
paquete académico que pide sudo es peor que uno que dice qué instalar. Si falta,
este programa imprime el comando exacto para el sistema donde está corriendo.

POR QUÉ ASÍ:
  --psm 4 (columna única de texto de tamaño variable) es el único modo que lee
  bien estas tablas. Con --psm 6 los bordes de la grilla se confunden con
  dígitos y el resultado es basura. Verificado contra la segunda transcripción.

  El filtro contra el nomenclador no es cosmético: descarta lo que no existe en
  el arancel. Los descartados NO son necesariamente errores de lectura, pueden
  ser códigos de una enmienda posterior, así que se listan para revisarlos a
  mano en vez de tirarlos en silencio.
"""

import argparse
import datetime
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

RE_NCM = re.compile(r"\d{4}\.\d{2}\.\d{2}")
IMAGEN_DOCKER = "jitesoft/tesseract-ocr:latest"


def instalacion_sugerida():
    """El comando exacto para este sistema. No lo ejecuta: lo imprime."""
    s = platform.system()
    if s == "Darwin":
        return "brew install tesseract"
    if s == "Windows":
        return "winget install UB-Mannheim.TesseractOCR"
    if Path("/etc/debian_version").exists():
        return "sudo apt-get install -y tesseract-ocr"
    if Path("/etc/redhat-release").exists():
        return "sudo dnf install -y tesseract"
    if Path("/etc/arch-release").exists():
        return "sudo pacman -S tesseract"
    return "instalar el paquete 'tesseract' con el gestor del sistema"


def elegir_motor(directorio):
    """Devuelve (etiqueta, versión, función que OCRea un archivo).

    Prefiere el binario local; si no está, usa Docker. La versión efectivamente
    usada se registra junto a la salida, porque la tasa de error auditada
    (0,04 %) es de una versión concreta del motor, no del método en abstracto.
    """
    if shutil.which("tesseract"):
        version = subprocess.run(["tesseract", "--version"], capture_output=True,
                                 text=True).stdout.splitlines()[0].strip()

        def correr(img):
            return subprocess.run(["tesseract", str(img), "stdout", "--psm", "4", "-l", "eng"],
                                  capture_output=True, text=True).stdout

        return "local", version, correr

    if shutil.which("docker"):
        version = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "tesseract", IMAGEN_DOCKER, "--version"],
            capture_output=True, text=True).stdout.splitlines()[0].strip()

        def correr(img):
            return subprocess.run(
                ["docker", "run", "--rm", "--entrypoint", "tesseract",
                 "-v", f"{directorio}:/d:ro", IMAGEN_DOCKER,
                 f"/d/{Path(img).name}", "stdout", "--psm", "4", "-l", "eng"],
                capture_output=True, text=True).stdout

        return f"docker {IMAGEN_DOCKER}", version, correr

    sys.exit(f"Falta tesseract, que es lo único que este paso necesita.\n"
             f"  Instalarlo:  {instalacion_sugerida()}\n"
             f"  O tener Docker corriendo, que sirve igual.\n\n"
             f"Este paso es opcional: la transcripción ya viene en el paquete y la\n"
             f"cadena principal (scripts/reproducir.py) no lo necesita.")


def clave_natural(p):
    """p2.jpg antes que p10.jpg: ordena por los números que tenga el nombre."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directorio", type=Path, help="carpeta con las páginas .jpg")
    ap.add_argument("salida", type=Path, help="archivo de la lista transcripta")
    ap.add_argument("nomenclador", type=Path, nargs="?",
                    help="opcional: NCM oficial contra el que validar")
    args = ap.parse_args()

    if not args.directorio.is_dir():
        sys.exit(f"no existe el directorio {args.directorio}")
    paginas = sorted(args.directorio.glob("*.jpg"), key=clave_natural)
    if not paginas:
        sys.exit(f"no hay .jpg en {args.directorio}")

    motor, version, correr = elegir_motor(args.directorio.resolve())
    print(f"OCR sobre {len(paginas)} páginas de {args.directorio}", file=sys.stderr)
    print(f"motor: {motor} — {version}", file=sys.stderr)

    # Se acumulan TODAS las coincidencias de cada página, no una por línea: una
    # fila de la tabla puede nombrar más de una posición y las dos valen. La
    # deduplicación viene después, sobre el total.
    crudo = []
    for img in paginas:
        encontrados = RE_NCM.findall(correr(img))
        crudo.extend(encontrados)
        print(f"  {img.name:<12} {len(encontrados):>4} posiciones", file=sys.stderr)

    unicos = sorted(set(crudo))

    if args.nomenclador and args.nomenclador.is_file():
        validos = {c for c in RE_NCM.findall(args.nomenclador.read_text(encoding="utf-8"))}
        quedan = [c for c in unicos if c in validos]
        descartados = [c for c in unicos if c not in validos]
        args.salida.write_text("".join(f"{c}\n" for c in quedan), encoding="utf-8")
        print(f"\n  crudo:        {len(crudo)}", file=sys.stderr)
        print(f"  únicos:       {len(unicos)}", file=sys.stderr)
        print(f"  descartados:  {len(descartados)}  (no existen en el nomenclador)",
              file=sys.stderr)
        print(f"  VÁLIDOS:      {len(quedan)}  ->  {args.salida}\n", file=sys.stderr)
        print("  Los descartados NO son necesariamente errores de OCR: pueden ser códigos",
              file=sys.stderr)
        print("  de una enmienda posterior a la del nomenclador. Revisarlos:", file=sys.stderr)
        for c in descartados:
            print(f"    {c}", file=sys.stderr)
    else:
        quedan = unicos
        args.salida.write_text("".join(f"{c}\n" for c in quedan), encoding="utf-8")
        print(f"\n  crudo: {len(crudo)} | únicos: {len(quedan)}  ->  {args.salida}",
              file=sys.stderr)
        print("  (sin validar contra el nomenclador: pasá el tercer argumento)",
              file=sys.stderr)

    # Constancia del motor: la transcripción es auditable sólo si se sabe con qué
    # se hizo. Va al lado de la salida y no dentro, para no ensuciar la lista.
    args.salida.with_suffix(args.salida.suffix + ".motor").write_text(
        f"motor: {motor}\nversion: {version}\npaginas: {len(paginas)}\n"
        f"posiciones: {len(quedan)}\nfecha: {datetime.datetime.now().isoformat()}\n",
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
