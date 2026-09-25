#!/usr/bin/env python3
"""
Extrae del Arancel Externo Común la descripción completa de cada posición NCM de
ocho dígitos, reconstruyendo la jerarquía de la nomenclatura: partida, agrupamientos
del Sistema Armonizado, subpartidas regionales y texto propio del ítem.

POR QUÉ HACE FALTA. Una posición NCM no se explica sola: su texto es un fragmento
que cuelga de los niveles superiores. «Los demás» no significa nada sin la partida
que lo encabeza. Reconstruir la jerarquía es lo que convierte el código en algo
legible, y de esa lectura dependen dos piezas del capítulo 7:

  · el arancel (AEC) de cada posición, que es la dimensión D1;
  · la descripción, que permite separar partes de máquinas completas (TB).

Un error acá no rompe nada de forma visible: sesga en silencio una dimensión del
capítulo 7. Ya pasó una vez, y está explicado en la segunda pasada, más abajo.

Entrada:  ~/tesis/datos/ncm_aec2017.pdf   (o el .txt ya extraído, si está)
Salida :  ~/tesis/datos/ncm_descripciones.tsv   (código, AEC%, marca, descripción)

Uso:  python3 descripciones_ncm.py [codigo ...]

      Con un código como argumento imprime esa posición, que es la forma rápida
      de comprobar a mano que la jerarquía se armó bien:
          python3 descripciones_ncm.py 8471.30.12
"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_universo as universo

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
PDF = DATOS / "ncm_aec2017.pdf"
TXT = DATOS / "ncm_aec2017_layout.txt"
SALIDA = DATOS / "ncm_descripciones.tsv"

if not TXT.exists():
    subprocess.run(["pdftotext", "-layout", str(PDF), str(TXT)], check=True)

RE_PARTIDA = re.compile(r"^(\d{2}\.\d{2})\s{2,}(\S.*)$")
RE_CODIGO = re.compile(r"^\s*(\d{4}\.\d{2}(?:\.\d{1,2})?)\s{2,}(\S.*)$")
# cola de la fila: AEC, marca BK/BIT y derecho de importación
RE_COLA = re.compile(r"\s{2,}(\d{1,2}(?:,\d+)?)\s+(BK|BIT)?\s*([\d,]+)?\s*$")


def separar_cola(texto):
    m = RE_COLA.search(texto)
    if m:
        return texto[:m.start()].strip(), m.group(1), m.group(2) or ""
    return re.sub(r"\s{2,}[\d,\s]+$", "", texto).strip(), "", ""


def sin_guiones(texto):
    n = 0
    while texto.startswith("- "):
        n += 1
        texto = texto[2:].lstrip()
    return n, texto


registros = {}
partida = ""
guiones = {}        # nivel -> encabezado del SA sin código
prefijos = {}       # código de 6 o 7 dígitos -> su texto
ultimo = None       # ("partida" | "guiones", clave) para pegar continuaciones

for linea in TXT.read_text(encoding="utf-8", errors="replace").splitlines():
    if not linea.strip():
        ultimo = None
        continue

    m = RE_PARTIDA.match(linea)
    if m:
        partida = separar_cola(m.group(2))[0].rstrip(".")
        guiones, prefijos = {}, {}
        ultimo = ("partida", None)
        continue

    m = RE_CODIGO.match(linea)
    if m:
        codigo, resto = m.group(1), m.group(2)
        desc, aec, marca = separar_cola(resto)
        nivel, texto = sin_guiones(desc)
        if len(codigo) == 10:  # posición de ocho dígitos
            cadena = [partida]
            cadena += [guiones[k] for k in sorted(guiones)]
            cadena += [prefijos[p] for p in (codigo[:7], codigo[:9]) if p in prefijos]
            cadena.append(texto)
            vistos, limpia = set(), []
            for x in cadena:
                if x and x not in vistos:
                    vistos.add(x)
                    limpia.append(x)
            registros[codigo] = {"aec": aec, "marca": marca,
                                 "desc": " › ".join(limpia), "propia": texto}
            ultimo = None
        else:                   # subpartida intermedia (8429.51 o 8429.51.9)
            prefijos[codigo] = texto.rstrip(":")
            prefijos = {k: v for k, v in prefijos.items() if len(k) <= len(codigo)}
            guiones = {k: v for k, v in guiones.items() if k <= nivel} if nivel else guiones
            ultimo = ("prefijo", codigo)
        continue

    desc = linea.strip()
    if desc.startswith("- "):
        nivel, texto = sin_guiones(desc)
        guiones = {k: v for k, v in guiones.items() if k < nivel}
        guiones[nivel] = texto.rstrip(":")
        prefijos = {}
        ultimo = ("guiones", nivel)
        continue

    # continuación de un encabezado partido en dos líneas
    if ultimo:
        tipo, clave = ultimo
        cont = separar_cola(desc)[0].rstrip(".").rstrip(":")
        if not cont:
            continue
        if tipo == "partida":
            partida = f"{partida} {cont}"
        elif tipo == "guiones":
            guiones[clave] = f"{guiones[clave]} {cont}"
        else:
            prefijos[clave] = f"{prefijos[clave]} {cont}"

# --------------------------------------------------------------------------
# Segunda pasada: el AEC y la marca están en la cola de la fila, y el PDF parte las
# filas largas en varias líneas. El barrido de arriba mira solo la línea del código,
# así que pierde la cola de toda fila con descripción de más de un renglón. Es el
# mismo defecto que corrigió construir_universo.py sobre la marca BK, y acá sesgaba
# la dimensión D1 del capítulo 7, que se construye con el AEC. Se completa releyendo
# la fila entera; es estrictamente aditivo: nunca pisa un valor ya obtenido.
# --------------------------------------------------------------------------

RE_COLA_CON_MARCA = re.compile(r"(\d{1,2}(?:,\d+)?)\s+(BK|BIT)(?![A-Za-z0-9])")
RE_COLA_SIN_MARCA = re.compile(r"(?<![\d,])(\d{1,2})\s+[\d]{1,2},\d{2}\s*$")


def cola_de_fila(texto):
    """(AEC, marca) leídos de la fila completa. La marca manda: el AEC es lo que va antes."""
    ultima = None
    for ultima in RE_COLA_CON_MARCA.finditer(texto):
        pass
    if ultima:
        return ultima.group(1), ultima.group(2)
    m = RE_COLA_SIN_MARCA.search(texto)
    return (m.group(1), "") if m else ("", "")


filas_enteras = universo.filas_completas(TXT.read_text(encoding="utf-8", errors="replace").splitlines())
completados = agregados = 0
for codigo, texto in filas_enteras.items():
    aec, marca = cola_de_fila(texto)
    if codigo not in registros:
        if aec or marca:
            registros[codigo] = {"aec": aec, "marca": marca, "desc": "", "propia": ""}
            agregados += 1
        continue
    r = registros[codigo]
    if not r["aec"] and aec:
        r["aec"] = aec
        completados += 1
    if not r["marca"] and marca:
        r["marca"] = marca

if completados or agregados:
    print(f"segunda pasada          : {completados:,} colas completadas, "
          f"{agregados} posiciones agregadas")

with open(SALIDA, "w", encoding="utf-8") as f:
    f.write("codigo\taec\tmarca\tdescripcion\n")
    for c in sorted(registros):
        r = registros[c]
        f.write(f"{c}\t{r['aec']}\t{r['marca']}\t{r['desc']}\n")

print(f"posiciones con descripción: {len(registros):,}  ->  {SALIDA}")

for arg in sys.argv[1:]:
    k = arg if "." in arg else f"{arg[:4]}.{arg[4:6]}.{arg[6:]}"
    r = registros.get(k)
    print(f"\n{k}  [AEC {r['aec']}%, {r['marca']}]\n  {r['desc']}" if r else f"\n{k}  NO ENCONTRADO")
