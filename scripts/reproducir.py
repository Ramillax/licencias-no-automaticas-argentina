#!/usr/bin/env python3
"""
Reproduce el trabajo entero, de las fuentes originales al veredicto.

    python3 scripts/reproducir.py

Baja las fuentes primarias de los organismos que las publican, reconstruye el
universo de bienes de capital y el panel, corre los análisis y termina
contrastando los resultados contra las cifras publicadas en la tesis.

El único requisito es Python 3.8 o posterior. No hace falta instalar nada: los
programas usan solamente la biblioteca estándar.

Opciones
    --desde N     empieza en la etapa N (las anteriores ya corrieron)
    --solo N      corre únicamente la etapa N
    --rapido      saltea el recuento de los 1,9 millones de registros al verificar
    --listar      muestra las etapas y no hace nada

Qué tarda: la descarga depende de la conexión (59 MB) y el resto alrededor de
un minuto en una máquina corriente.
"""

import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
DATOS = RAIZ / "datos"

VERDE, ROJO, AMBAR, GRIS, NEGRITA, FIN = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")
if not sys.stdout.isatty():
    VERDE = ROJO = AMBAR = GRIS = NEGRITA = FIN = ""

# (programa, argumentos, qué hace)
ETAPAS = [
    ("descargar_fuentes.py", [],
     "Descarga las fuentes primarias y las verifica por SHA-256"),
    # --escribir, no el modo verificación: en un paquete recién descomprimido
    # estos seis archivos no existen todavía. Son producto derivado, no insumo.
    ("construir_universo.py", ["--escribir"],
     "Delimita los bienes de capital y sus tres trayectorias regulatorias"),
    ("descripciones_ncm.py", [],
     "Extrae del arancel la descripción y el AEC de cada posición"),
    ("construir_panel.py", [],
     "Arma el panel posición-mes y las series agregadas"),
    ("origenes.py", [],
     "Compone la participación por país de origen"),
    ("analisis_grupos.py", [],
     "Compara las trayectorias regulatorias y sus robusteces"),
    ("analisis_heterogeneidad.py", [],
     "Contrasta las cuatro dimensiones de heterogeneidad"),
    ("verificar.py", [],
     "Contrasta todo lo anterior contra las cifras publicadas"),
]

# Insumos que NO se pueden volver a derivar con solo Python y que por eso viajan
# dentro del paquete. Cada uno se comprueba antes de arrancar.
CONGELADOS = {
    "datos/lna_agosto2022_ocr.txt":
        "transcripción del anexo de agosto de 2022 (OCR, tesseract 5.5)",
    "datos/lna_octubre2022_ocr.txt":
        "transcripción del anexo de octubre de 2022 (OCR, tesseract 5.5)",
    "datos/ncm_aec2017_layout.txt":
        "texto del Arancel Externo Común (pdftotext -layout)",
    "datos/referencia/paises_indec.csv":
        "tabla de países del INDEC",
    "datos/lna-transcripcion/lna_ch84_90.txt":
        "segunda transcripción de referencia, contra la que se mide la concordancia del OCR",
}


def sha256(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            d.update(b)
    return d.hexdigest()


def comprobar_entorno():
    print(f"{NEGRITA}Entorno{FIN}")
    v = sys.version_info
    if v < (3, 8):
        sys.exit(f"{ROJO}hace falta Python 3.8 o posterior; este es {v.major}.{v.minor}{FIN}")
    print(f"  {VERDE}ok{FIN}  Python {v.major}.{v.minor}.{v.micro}")

    faltan = [r for r in CONGELADOS if not (RAIZ / r).exists()]
    if faltan:
        print(f"  {ROJO}✗{FIN}  faltan insumos que tienen que venir en el paquete:")
        for r in faltan:
            print(f"      {r}  {GRIS}({CONGELADOS[r]}){FIN}")
        sys.exit(1)
    print(f"  {VERDE}ok{FIN}  {len(CONGELADOS)} insumos incluidos en el paquete")

    hashes = DATOS / "CONGELADOS.sha256"
    if hashes.exists():
        malos = []
        for linea in hashes.read_text(encoding="utf-8").splitlines():
            if not linea.strip() or linea.startswith("#"):
                continue
            esperado, rel = linea.split(None, 1)
            rel = rel.strip()
            if (RAIZ / rel).exists() and sha256(RAIZ / rel) != esperado:
                malos.append(rel)
        if malos:
            print(f"  {ROJO}✗{FIN}  insumos alterados respecto del paquete original:")
            for r in malos:
                print(f"      {r}")
            sys.exit(1)
        print(f"  {VERDE}ok{FIN}  los insumos coinciden con el paquete original")
    print()


def correr(n, total, programa, argumentos, descripcion):
    print(f"{NEGRITA}[{n}/{total}] {programa}{FIN}  {GRIS}{descripcion}{FIN}")
    t0 = time.time()
    r = subprocess.run([sys.executable, str(SCRIPTS / programa), *argumentos], cwd=RAIZ)
    seg = time.time() - t0
    if r.returncode != 0:
        print(f"\n{ROJO}La etapa {n} falló (código {r.returncode}). La cadena se detiene acá.{FIN}")
        print(f"{GRIS}Para retomar desde este punto:  python3 scripts/reproducir.py --desde {n}{FIN}")
        sys.exit(r.returncode)
    print(f"  {GRIS}{seg:.1f} s{FIN}\n")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--desde", type=int, default=1, metavar="N")
    ap.add_argument("--solo", type=int, metavar="N")
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--listar", action="store_true")
    args = ap.parse_args()

    total = len(ETAPAS)
    if args.listar:
        print("Etapas:")
        for i, (p, _, d) in enumerate(ETAPAS, 1):
            print(f"  {i:>2}. {p:<28} {d}")
        return 0

    print(f"{NEGRITA}REPRODUCCIÓN DEL TRABAJO{FIN}")
    print(f"proyecto: {RAIZ}\n")
    comprobar_entorno()

    etapas = list(enumerate(ETAPAS, 1))
    if args.solo:
        etapas = [e for e in etapas if e[0] == args.solo]
    else:
        etapas = [e for e in etapas if e[0] >= args.desde]

    t0 = time.time()
    for n, (programa, argumentos, descripcion) in etapas:
        if programa == "verificar.py" and args.rapido:
            argumentos = [*argumentos, "--rapido"]
        correr(n, total, programa, argumentos, descripcion)

    print(f"{VERDE}{NEGRITA}Listo.{FIN} {GRIS}{time.time() - t0:.0f} s en total.{FIN}")
    print(f"{GRIS}Los resultados quedaron en datos/ (panel, series y análisis en CSV y JSON).{FIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
