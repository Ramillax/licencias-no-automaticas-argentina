#!/usr/bin/env python3
"""
Robusteces del capítulo 6: la comparación entre G1 y G2 bajo restricciones que
neutralizan las diferencias de composición entre los grupos.

Variantes calculadas:
  completo      las 185 posiciones de G1 contra las 965 de G2
  cap84         solo capítulo 84, donde ambos grupos concentran su valor
  sin_top5      excluyendo las cinco posiciones de mayor valor de cada grupo
  sin_top20     excluyendo las veinte posiciones de mayor valor de cada grupo

Las tres últimas existen porque el comercio de bienes de capital está muy
concentrado: si el contraste entre grupos dependiera de dos o tres posiciones
grandes, no diría nada sobre el régimen. El capítulo 6 reporta las cuatro y el
signo del resultado se mantiene en todas.

Qué mirar: la fila `ratio` (G2/G1) a lo largo de los tres tramos. Cae de forma
sostenida, y el tramo donde MÁS cae es aquel en el que los dos grupos enfrentan
exactamente el mismo régimen. Ese es el argumento central del capítulo 6 y la
razón por la que el trabajo no atribuye causalidad.

Salida: ~/tesis/datos/robustez_grupos.json y un cuadro por pantalla.

Uso:  python3 analisis_grupos.py
"""

import csv
import json
import math
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indices import tornqvist    # una sola implementación, ver indices.py
from indec import filas_importacion    # lector del microdato, ver indec.py

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"

# Ver construir_panel.py: el archivo del año en curso crece entre descargas.
VENTANA_HASTA = "2026-06"

GRUPO = {}
for g, f in (("G1", "bk_ruta_a_control"), ("G2", "bk_ruta_a_tratadas"),
             ("G3", "bk_ruta_a_nunca")):
    for linea in (DATOS / "lna-transcripcion" / f"{f}.txt").read_text().splitlines():
        c = linea.strip().replace(".", "")
        if len(c) == 8 and c.isdigit():
            GRUPO[c] = g


# (ncm, mes, porg) -> [fob, kg]. El lector vive en indec.py: ahí están la
# codificación latin-1, los decimales con coma y la ventana temporal.
micro = defaultdict(lambda: [0.0, 0.0])
for ncm, mes, porg, fob, kg in filas_importacion(solo=set(GRUPO)):
    if fob <= 0:
        continue
    c = micro[(ncm, mes, porg)]
    c[0] += fob
    c[1] += kg

valor_pos = defaultdict(float)
for (ncm, _, _), (fob, _) in micro.items():
    valor_pos[ncm] += fob

TRIM = lambda mes: f"{mes[:4]}-T{(int(mes[5:]) - 1) // 3 + 1}"


def universo(grupo, variante):
    pos = {c for c, g in GRUPO.items() if g == grupo}
    if variante == "cap84":
        pos = {c for c in pos if c.startswith("84")}
    elif variante.startswith("sin_top"):
        n = int(variante[7:])
        top = sorted(pos, key=lambda c: -valor_pos.get(c, 0.0))[:n]
        pos -= set(top)
    return pos


def series(pos):
    """Devuelve (trim -> {fob, kg}, trim -> {ncm -> [fob, kg]})."""
    agr = defaultdict(lambda: [0.0, 0.0])
    celdas = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    anual = defaultdict(lambda: [0.0, 0.0])
    for (ncm, mes, _), (fob, kg) in micro.items():
        if ncm not in pos:
            continue
        t = TRIM(mes)
        agr[t][0] += fob
        agr[t][1] += kg
        c = celdas[t][ncm]
        c[0] += fob
        c[1] += kg
        if mes[:4] == "2021":
            a = anual["2021"]
            a[0] += fob
            a[1] += kg
    base = defaultdict(lambda: [0.0, 0.0])
    for (ncm, mes, _), (fob, kg) in micro.items():
        if ncm in pos and mes[:4] == "2021":
            b = base[ncm]
            b[0] += fob
            b[1] += kg
    return agr, celdas, base



# Los tres tramos regulatorios. Los cortes NO son arbitrarios: salen de las
# fechas de las resoluciones, y cada tramo describe una relación distinta entre
# los dos grupos.
#   I   hasta 2022-T3  G1 está bajo licencia y G2 no: el régimen los diferencia.
#   II  2022-T4 a 2023-T4  la Res. SC 26/2022 suma a G2: ambos bajo el mismo régimen.
#   III desde 2024-T1  abrogado para todos desde el 27-12-2023: ambos sin régimen.
# Como en II y III el régimen es idéntico para los dos grupos, cualquier
# divergencia que aparezca ahí NO puede atribuirse al régimen. Que el salto
# mayor esté entre II y III es el hallazgo del capítulo 6.
TRAMOS = [("G1 bajo LNA, G2 no", lambda t: t <= "2022-T3"),
          ("ambos bajo LNA", lambda t: "2022-T4" <= t <= "2023-T4"),
          ("ninguno bajo LNA", lambda t: t >= "2024-T1")]

VARIANTES = ["completo", "cap84", "sin_top5", "sin_top20"]
resultado = {}

for var in VARIANTES:
    resultado[var] = {}
    for g in ("G1", "G2"):
        pos = universo(g, var)
        agr, celdas, base = series(pos)
        trims = sorted(agr)
        # Cada grupo se indiza contra SU PROPIO 2021 = 100, no contra el del otro.
        # Por eso los niveles de G1 y G2 no son comparables entre sí en valor
        # absoluto y lo que se compara es la RAZÓN entre sus índices: cada grupo
        # parte de 100 y lo que importa es cuánto se separan.
        base_fob = sum(v[0] for v in base.values()) / 12   # promedio mensual de 2021
        idx = {}
        for t in trims:
            rel = tornqvist(base, celdas[t])
            precio = 100.0 * rel if rel else None
            valor = agr[t][0] / 3 / base_fob * 100         # /3: trimestre a mensual
            # La cantidad no se mide: se deduce. Valor = precio x cantidad, así
            # que cantidad = valor / precio. Es lo que permite tener un índice de
            # volumen sin unidades físicas homogéneas, que la aduana no publica.
            idx[t] = {"precio": round(precio, 2) if precio else None,
                      "valor": round(valor, 2),
                      "cantidad": round(valor / precio * 100, 2) if precio else None}
        resultado[var][g] = {"posiciones": len(pos), "indices": idx}

    r = resultado[var]
    resultado[var]["ratio_por_tramo"] = {}
    for nombre, filtro in TRAMOS:
        ts = [t for t in sorted(r["G1"]["indices"]) if filtro(t)]
        q1 = sum(r["G1"]["indices"][t]["cantidad"] for t in ts) / len(ts)
        q2 = sum(r["G2"]["indices"][t]["cantidad"] for t in ts) / len(ts)
        resultado[var]["ratio_por_tramo"][nombre] = {
            "Q_G1": round(q1, 1), "Q_G2": round(q2, 1), "ratio": round(q2 / q1 * 100, 1)}

with open(DATOS / "robustez_grupos.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=1)

print("Índice de cantidad promedio por tramo regulatorio (base propia 2021 = 100)")
print(f"{'variante':>12} {'pos. G1':>8} {'pos. G2':>8} | " +
      " | ".join(f"{n:^26}" for n, _ in TRAMOS))
print(f"{'':>12} {'':>8} {'':>8} | " +
      " | ".join(f"{'G1':>7} {'G2':>7} {'G2/G1':>8}" for _ in TRAMOS))
for var in VARIANTES:
    r = resultado[var]
    fila = " | ".join(
        f"{r['ratio_por_tramo'][n]['Q_G1']:>7.1f} {r['ratio_por_tramo'][n]['Q_G2']:>7.1f} "
        f"{r['ratio_por_tramo'][n]['ratio']:>8.1f}" for n, _ in TRAMOS)
    print(f"{var:>12} {r['G1']['posiciones']:>8} {r['G2']['posiciones']:>8} | {fila}")
