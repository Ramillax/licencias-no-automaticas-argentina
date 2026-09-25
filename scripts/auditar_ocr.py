#!/usr/bin/env python3
"""
Mide la discrepancia entre las dos transcripciones del anexo. La cifra que el
trabajo reporta se calcula acá: este programa es su fuente, no la copia de un
número anotado en otro lado.

    python3 scripts/auditar_ocr.py              compara las dos transcripciones
    python3 scripts/auditar_ocr.py --rehacer    además vuelve a pasar el OCR

Son dos preguntas distintas y el programa contesta las dos por separado.

CONCORDANCIA — ¿coinciden dos lecturas independientes de las mismas imágenes?
    Se compara la salida del OCR contra `lna-transcripcion/lna_ch84_90.txt`: las
    mismas 2.261 posiciones de los capítulos 84 a 90 del anexo de octubre,
    transcriptas por un procedimiento de lectura **distinto** del reconocimiento
    óptico de caracteres. Que dos procedimientos independientes lleguen al mismo
    listado es evidencia de que el listado es correcto; **no es una medición
    contra la verdad**, porque ninguna de las dos lecturas es infalible.

    Es la práctica que recomiendan Correia y Luck (2023) para digitalización de
    fuentes económicas escaneadas: contrastar la salida automática contra una
    referencia construida aparte, en vez de suponer que el motor acertó.

REPRODUCIBILIDAD — ¿otra corrida del OCR da lo mismo?
    Con `--rehacer`, vuelve a pasar el motor sobre las imágenes y compara contra
    la transcripción congelada. Necesita tesseract o Docker; sin eso, saltea esta
    parte y avisa.

Y una tercera cosa que el programa comprueba: que las discrepancias sean
DETECTABLES. Una lectura errónea que produce un código inexistente la caza la
validación contra el nomenclador; una que produce otro código válido, no. La
diferencia importa más que el porcentaje, porque define si el error sobrevive
al control.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
TRANS = DATOS / "lna-transcripcion"

REFERENCIA = TRANS / "lna_ch84_90.txt"          # segunda transcripción, otro procedimiento
OCR_OCTUBRE = DATOS / "lna_octubre2022_ocr.txt"  # salida del OCR, congelada
NOMENCLADOR = DATOS / "ncm_aec2017_todas.txt"
IMAGENES_AGOSTO = DATOS / "anexo2-lna-res1-2022-agosto"
OCR_AGOSTO = DATOS / "lna_agosto2022_ocr.txt"

RE_NCM = re.compile(r"\d{4}\.\d{2}\.\d{2}")
VERDE, ROJO, AMBAR, GRIS, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"
if not sys.stdout.isatty():
    VERDE = ROJO = AMBAR = GRIS = FIN = ""


def codigos(path):
    return set(RE_NCM.findall(path.read_text(encoding="utf-8")))


def precision():
    """Compara las dos transcripciones y devuelve el porcentaje de discrepancia."""
    print("CONCORDANCIA — OCR contra la segunda transcripción de referencia")
    for p in (REFERENCIA, OCR_OCTUBRE):
        if not p.exists():
            sys.exit(f"falta {p}, que tiene que venir dentro del paquete")
    if not NOMENCLADOR.exists():
        sys.exit(f"falta {NOMENCLADOR.name}, que lo produce la cadena.\n"
                 f"  Correr antes:  python3 scripts/reproducir.py\n"
                 f"  o al menos:    python3 scripts/construir_universo.py --escribir")

    patron = codigos(REFERENCIA)
    # El patrón cubre sólo los capítulos 84 a 90, así que el OCR se recorta al
    # mismo tramo: comparar contra el anexo entero mediría otra cosa.
    salida = {c for c in codigos(OCR_OCTUBRE) if "84" <= c[:2] <= "90"}
    valido = codigos(NOMENCLADOR)

    faltan = patron - salida       # el OCR no leyó una posición que estaba
    sobran = salida - patron       # el OCR leyó algo que el patrón no tiene
    aciertos = len(patron & salida)
    errores = len(faltan) + len(sobran)

    print(f"  posiciones en la 2ª transcripción   : {len(patron):>6,}")
    print(f"  posiciones leídas por el OCR        : {len(salida):>6,}")
    print(f"  coincidencias exactas               : {aciertos:>6,}")
    print(f"  no leídas por el OCR                : {len(faltan):>6,}")
    print(f"  leídas de más                       : {len(sobran):>6,}")

    tasa = errores / (2 * len(patron)) * 100 if patron else 0.0
    print(f"\n  {'DISCREPANCIA':<36}{tasa:>6.2f} %"
          f"  {GRIS}({errores} desvíos sobre {2 * len(patron):,} comparaciones){FIN}")

    if not errores:
        print(f"  {VERDE}las dos transcripciones coinciden en todo{FIN}")
        return tasa

    # Lo que decide si un error sobrevive al control: si el código mal leído NO
    # existe en el nomenclador, la validación lo descarta sola.
    print(f"\n  Discrepancias, y si el control contra el nomenclador las detecta:")
    detectables = 0
    for c in sorted(sobran):
        existe = c in valido
        detectables += not existe
        estado = (f"{ROJO}NO detectable{FIN} (es un código válido del arancel)" if existe
                  else f"{VERDE}detectable{FIN} (no existe en el nomenclador)")
        print(f"    leído de más  {c}   {estado}")
    for c in sorted(faltan):
        print(f"    no leído      {c}   {GRIS}(está en la 2ª transcripción){FIN}")

    print(f"\n  {detectables} de {len(sobran)} lecturas espurias las caza la validación "
          f"contra el nomenclador.")
    return tasa


def reproducibilidad():
    """Vuelve a correr el OCR y lo compara contra la transcripción congelada."""
    print("\nREPRODUCIBILIDAD — nueva corrida del OCR contra la lista congelada")
    if not IMAGENES_AGOSTO.is_dir():
        print(f"  {AMBAR}faltan las imágenes: correr antes descargar_fuentes.py{FIN}")
        return
    salida = RAIZ / "salida" / "ocr-rehecho-agosto.txt"
    salida.parent.mkdir(exist_ok=True)
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "ocr_anexo.py"),
                        str(IMAGENES_AGOSTO), str(salida)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {AMBAR}no se pudo correr el OCR:{FIN}")
        print(GRIS + "\n".join("    " + l for l in r.stdout.splitlines()[:6]) + FIN)
        return
    nuevo, viejo = codigos(salida), codigos(OCR_AGOSTO)
    print(f"  posiciones en la lista congelada : {len(viejo):>6,}")
    print(f"  posiciones en la corrida nueva   : {len(nuevo):>6,}")
    if nuevo == viejo:
        print(f"  {VERDE}idénticas: la transcripción se reproduce exactamente{FIN}")
    else:
        print(f"  {ROJO}difieren en {len(nuevo ^ viejo)} códigos{FIN}")
        for c in sorted(nuevo ^ viejo)[:20]:
            print(f"    {c}  {'sólo en la nueva' if c in nuevo else 'sólo en la congelada'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rehacer", action="store_true",
                    help="además vuelve a pasar el OCR (necesita tesseract o Docker)")
    args = ap.parse_args()
    precision()
    if args.rehacer:
        reproducibilidad()
