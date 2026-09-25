#!/usr/bin/env python3
"""
Composición por país de origen de las importaciones de bienes de capital,
2021-2026: participación en el valor, participación en el peso y valor unitario.

Salida: ~/tesis/datos/origenes.json  y un cuadro por pantalla.

Uso:  python3 origenes.py
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from indec import filas_importacion    # lector del microdato, ver indec.py

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
PAISES = DATOS / "referencia" / "paises_indec.csv"

NOMBRE = {r["porg"]: r["nombre_es"]
          for r in csv.DictReader(open(PAISES, encoding="utf-8"))}

UNIVERSO = set()
for f in ("bk_ruta_a_control", "bk_ruta_a_tratadas", "bk_ruta_a_nunca"):
    for linea in (DATOS / "lna-transcripcion" / f"{f}.txt").read_text().splitlines():
        c = linea.strip().replace(".", "")
        if len(c) == 8 and c.isdigit():
            UNIVERSO.add(c)

# Códigos verificados contra paises_indec.csv del INDEC
CHINA, EEUU = "310", "212"
BRASIL = {"203", "291"}                    # Brasil y Zona Franca de Manaos
ASIA_ALTO_COSTO = {"320", "309", "318", "333"}  # Japón, Corea del Sur, Israel, Singapur


def bloque(porg):
    if porg == CHINA:
        return "China"
    if porg in ASIA_ALTO_COSTO:
        return "Asia de costo alto"
    if porg.startswith("3"):
        return "Resto de Asia"
    if porg.startswith("4"):
        return "Europa"
    if porg == EEUU:
        return "Estados Unidos"
    if porg in BRASIL:
        return "Brasil"
    if porg.startswith("2"):
        return "Resto de América"
    return "Otros"


por_bloque = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
por_pais = defaultdict(lambda: [0.0, 0.0])

# El lector vive en indec.py, con la codificación, los decimales y la ventana.
for ncm, mes, porg, fob, kg in filas_importacion(solo=UNIVERSO):
    b = por_bloque[mes[:4]][bloque(porg)]
    b[0] += fob
    b[1] += kg
    p = por_pais[porg]
    p[0] += fob
    p[1] += kg

ANIOS = [str(a) for a in range(2021, 2027)]
BLOQUES = ["China", "Resto de Asia", "Asia de costo alto", "Europa",
           "Estados Unidos", "Brasil", "Resto de América", "Otros"]

salida = {"bloques": {}, "paises": {}}
for b in BLOQUES:
    salida["bloques"][b] = {}
    for a in ANIOS:
        fob, kg = por_bloque[a].get(b, [0.0, 0.0])
        tf = sum(v[0] for v in por_bloque[a].values())
        tk = sum(v[1] for v in por_bloque[a].values())
        salida["bloques"][b][a] = {
            "share_valor": round(fob / tf * 100, 2),
            "share_kg": round(kg / tk * 100, 2),
            "usd_por_kg": round(fob / kg, 2) if kg else None,
        }

total_fob = sum(v[0] for v in por_pais.values())
for p, (fob, kg) in sorted(por_pais.items(), key=lambda x: -x[1][0])[:25]:
    salida["paises"][p] = {"nombre": NOMBRE.get(p, "?"), "fob_usd": round(fob, 2),
                           "share_valor": round(fob / total_fob * 100, 2),
                           "usd_por_kg": round(fob / kg, 2) if kg else None}

with open(DATOS / "origenes.json", "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False, indent=1)

for etiqueta, campo in (("participación en el valor (%)", "share_valor"),
                        ("participación en el peso (%)", "share_kg"),
                        ("valor unitario (USD/kg)", "usd_por_kg")):
    print(f"=== {etiqueta} ===")
    print(f"{'':>20} " + " ".join(f"{a:>8}" for a in ANIOS))
    for b in BLOQUES:
        print(f"{b:>20} " + " ".join(f"{salida['bloques'][b][a][campo]:>8}" for a in ANIOS))
    print()

print("=== principales orígenes, FOB acumulado 2021-2026 ===")
for p, r in list(salida["paises"].items())[:12]:
    print(f"  {r['nombre']:<40} {r['fob_usd']/1e6:8.0f} M USD  {r['share_valor']:5.1f}%  "
          f"{r['usd_por_kg']:6.1f} USD/kg")
