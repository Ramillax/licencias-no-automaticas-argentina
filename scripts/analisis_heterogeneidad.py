#!/usr/bin/env python3
"""
Capítulo 7 — heterogeneidad de la evolución según atributos de la posición.

Repite la maquinaria de los capítulos 5 y 6 —índice de valor unitario Törnqvist
de base fija contra el año 2021 completo del propio subgrupo, índice de cantidad
implícito, promedios por tramo regulatorio— pero partiendo el panel por cuatro
atributos de la posición en lugar de por trayectoria regulatoria.

Los cuatro atributos tienen la misma naturaleza y es deliberado: o los declara el
nomenclador oficial o se calculan sobre el propio panel. Ninguno infiere nada
sobre el mundo que los datos no muestren.

Todos los contrastes se toman DENTRO DE G2, las posiciones que entran al
régimen de licencias en octubre de 2022 y salen en diciembre de 2023. Con eso la
trayectoria regulatoria queda constante en las dos celdas de cada comparación y
lo único que varía es el atributo. Es la razón por la que el capítulo 7 no
reproduce el problema del capítulo 6: acá no hay contraste regulatorio que
confundir con el atributo.

  D1  protección arancelaria previa      AEC de la posición, 14 % frente a 0 %
  D2  diferenciación del producto        dispersión de valores unitarios entre
                                         orígenes dentro de la posición, 2021-22
  D3  tamaño del mercado                 valor importado medio anual, 2021-22
  TB  tipo de bien                       máquina completa frente a partes

D2 no usa el criterio de Rauch. Rauch clasifica a nivel SITC y dentro de bienes
de capital manda a casi todo al grupo «diferenciado»: aplicado a este universo no
discrimina nada. Se lo reemplaza por una medida construida sobre el propio panel
que captura la misma idea económica —qué tan comparables entre sí son las
mercaderías de distinto origen dentro de una posición— y que además se mide en el
período previo, antes del cambio de régimen.

Salidas: ~/tesis/datos/analisis_heterogeneidad.json y cuadros por pantalla.
"""

import csv
import json
import math
import statistics
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
PRE = ("2021", "2022")

# El arancel y la descripción salen del nomenclador; la trayectoria regulatoria,
# de los listados de licencias reconstruidos en el capítulo 3.
AEC, DESC = {}, {}
for r in csv.DictReader(open(DATOS / "ncm_descripciones.tsv"), delimiter="\t"):
    c = r["codigo"].replace(".", "")
    AEC[c] = r["aec"]
    DESC[c] = r["descripcion"]

GRUPO = {}
for arch, g in (("bk_ruta_a_control", "G1"), ("bk_ruta_a_tratadas", "G2"),
                ("bk_ruta_a_nunca", "G3")):
    for linea in (DATOS / "lna-transcripcion" / f"{arch}.txt").read_text().splitlines():
        c = linea.strip().replace(".", "")
        if len(c) == 8 and c.isdigit():
            GRUPO[c] = g


def es_parte(ncm):
    """La posición cubre partes y accesorios, no la máquina completa."""
    return any(x.strip().lower().startswith("partes")
               for x in DESC.get(ncm, "").split("›"))


# --- microdato -----------------------------------------------------------
micro = defaultdict(lambda: [0.0, 0.0])          # (ncm, mes, porg) -> [fob, kg]. El lector vive en indec.py: ahí están la
# codificación latin-1, los decimales con coma y la ventana temporal.
micro = defaultdict(lambda: [0.0, 0.0])
for ncm, mes, porg, fob, kg in filas_importacion(solo=set(GRUPO)):
    if fob <= 0:
        continue
    c = micro[(ncm, mes, porg)]
    c[0] += fob
    c[1] += kg

TRIM = lambda mes: f"{mes[:4]}-T{(int(mes[5:]) - 1) // 3 + 1}"



def indices(pos):
    """Serie trimestral de precio, valor y cantidad para un subconjunto.

    Cada celda de la comparación se indiza contra SU PROPIO 2021 = 100, no contra
    el del universo ni el de la celda vecina. Por eso los niveles de dos celdas no
    son comparables entre sí en valor absoluto: las dos arrancan en 100 y lo que
    el capítulo 7 lee es la RAZÓN entre ellas, es decir cuánto se separan.
    """
    agr = defaultdict(lambda: [0.0, 0.0])
    celdas = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    base = defaultdict(lambda: [0.0, 0.0])
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
            b = base[ncm]
            b[0] += fob
            b[1] += kg
    base_fob = sum(v[0] for v in base.values()) / 12   # promedio mensual de 2021
    if base_fob <= 0:
        return None
    out = {}
    for t in sorted(agr):
        rel = tornqvist(base, celdas[t])
        precio = 100.0 * rel if rel else None
        valor = agr[t][0] / 3 / base_fob * 100         # /3: trimestre a mensual
        # La cantidad no se observa: se deduce de valor = precio x cantidad. Es
        # lo que permite un índice de volumen sin unidades físicas homogéneas,
        # que la aduana no publica (sólo hay peso, y un kilo de torno no es
        # comparable con un kilo de tomógrafo).
        out[t] = {"precio": round(precio, 2) if precio else None,
                  "valor": round(valor, 2),
                  "cantidad": round(valor / precio * 100, 2) if precio else None}
    return out


# Los mismos tres tramos del capítulo 6, por comparabilidad. Acá cumplen otro
# papel: como todas las posiciones son de G2, las DOS celdas de cada contraste
# enfrentan el mismo régimen en todo momento. Los tramos no separan regímenes
# distintos, sólo dan una cronología común para leer cuándo se abre la brecha.
# Que una dimensión alcance su máximo en el tramo III (con el régimen ya
# abrogado) o en el II (con el régimen puesto para las dos celdas) es lo que
# distingue a D2 de las otras tres.
TRAMOS = [("I", lambda t: t <= "2022-T3"),
          ("II", lambda t: "2022-T4" <= t <= "2023-T4"),
          ("III", lambda t: t >= "2024-T1")]


def promedios(idx):
    out = {}
    for nombre, filtro in TRAMOS:
        ts = [t for t in sorted(idx) if filtro(t) and idx[t]["cantidad"]]
        out[nombre] = {
            "cantidad": round(sum(idx[t]["cantidad"] for t in ts) / len(ts), 1),
            "precio": round(sum(idx[t]["precio"] for t in ts) / len(ts), 1)}
    return out


# --- D2: dispersión de valores unitarios entre orígenes -------------------
# Para cada posición se toma el valor unitario de cada origen en la ventana
# previa, se calcula el desvío estándar del logaritmo ponderado por la
# participación del origen en el valor, y se exige al menos tres orígenes. Un
# bien homogéneo llega de todas partes a un precio por kilo parecido; uno
# diferenciado no. La medida se construye ANTES del cambio de régimen, así que no
# puede estar contaminada por lo que se quiere describir.
def dispersion_origenes():
    por_pos = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    for (ncm, mes, porg), (fob, kg) in micro.items():
        if mes[:4] in PRE and kg > 0:
            c = por_pos[ncm][porg]
            c[0] += fob
            c[1] += kg
    out = {}
    for ncm, orgs in por_pos.items():
        vu = {o: v[0] / v[1] for o, v in orgs.items() if v[1] > 0 and v[0] > 0}
        if len(vu) < 3:
            continue
        tot = sum(orgs[o][0] for o in vu)
        media = sum(orgs[o][0] / tot * math.log(vu[o]) for o in vu)
        var = sum(orgs[o][0] / tot * (math.log(vu[o]) - media) ** 2 for o in vu)
        out[ncm] = math.sqrt(var)
    return out


DISP = dispersion_origenes()

# --- D3: tamaño del mercado ----------------------------------------------
IMPO_PRE = defaultdict(float)
for (ncm, mes, _), (fob, _) in micro.items():
    if mes[:4] in PRE:
        IMPO_PRE[ncm] += fob

# G2 restringido a las posiciones que registran alguna importación: las que no
# comercian no aportan nada a los índices y contarlas infla los tamaños de celda
# sin cambiar ningún resultado.
CON_COMERCIO = {k[0] for k in micro}
G2POS = {c for c in GRUPO if GRUPO[c] == "G2" and c in CON_COMERCIO}
disp_g2 = sorted(DISP[c] for c in G2POS if c in DISP)
CORTE_D2 = statistics.median(disp_g2)
impo_g2 = sorted(IMPO_PRE[c] for c in G2POS if IMPO_PRE[c] > 0)
CORTE_D3 = statistics.median(impo_g2)

# --- dimensiones ----------------------------------------------------------
DIMENSIONES = {
    "D1 — protección arancelaria previa (dentro de G2)": (
        ("AEC 0 %", lambda c: AEC[c] == "0"),
        ("AEC 14 %", lambda c: AEC[c] == "14"),
    ),
    "D2 — diferenciación del producto (dentro de G2)": (
        ("homogéneo (dispersión baja)", lambda c: c in DISP and DISP[c] <= CORTE_D2),
        ("diferenciado (dispersión alta)", lambda c: c in DISP and DISP[c] > CORTE_D2),
    ),
    "D3 — tamaño del mercado (dentro de G2)": (
        ("mercado chico", lambda c: 0 < IMPO_PRE[c] <= CORTE_D3),
        ("mercado grande", lambda c: IMPO_PRE[c] > CORTE_D3),
    ),
    "TB — tipo de bien (dentro de G2)": (
        ("máquina completa", lambda c: not es_parte(c)),
        ("partes y accesorios", lambda c: es_parte(c)),
    ),
}

resultado = {"cortes": {"D2_desvio_log_vu": round(CORTE_D2, 4),
                        "D3_impo_pre_usd": round(CORTE_D3, 0),
                        "posiciones_G2": len(G2POS),
                        "G2_con_D2_medible": sum(1 for c in G2POS if c in DISP)}}

for dim, celdas in DIMENSIONES.items():
    resultado[dim] = {}
    for etiqueta, filtro in celdas:
        pos = {c for c in G2POS if filtro(c)}
        idx = indices(pos)
        if not idx:
            continue
        resultado[dim][etiqueta] = {
            "posiciones": len(pos),
            "fob_total_musd": round(
                sum(v[0] for (n, _, _), v in micro.items() if n in pos) / 1e6, 1),
            "por_tramo": promedios(idx),
            "indices_trimestrales": idx,
        }
    vals = list(resultado[dim].values())
    if len(vals) == 2:
        resultado[dim]["razon_Q_segunda_sobre_primera"] = {
            n: round(vals[1]["por_tramo"][n]["cantidad"]
                     / vals[0]["por_tramo"][n]["cantidad"] * 100, 1)
            for n, _ in TRAMOS}

with open(DATOS / "analisis_heterogeneidad.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=1)

# --- salida ---------------------------------------------------------------
print(f"G2: {len(G2POS)} posiciones. Corte D2 (desvío del log del valor unitario "
      f"entre orígenes): {CORTE_D2:.3f}; {resultado['cortes']['G2_con_D2_medible']} "
      f"posiciones con tres orígenes o más en 2021-22.")
print(f"Corte D3 (valor importado 2021-22): {CORTE_D3/1e6:.2f} M USD.\n")

for dim, celdas in DIMENSIONES.items():
    print(f"=== {dim} ===")
    print(f"{'':<32}{'pos.':>6}{'M USD':>10}   " +
          "  ".join(f"{n:^17}" for n, _ in TRAMOS))
    print(f"{'':<32}{'':>6}{'':>10}   " + "  ".join(f"{'Q':>8}{'P':>9}" for _ in TRAMOS))
    for etiqueta, r in resultado[dim].items():
        if etiqueta.startswith("razon"):
            continue
        fila = "  ".join(f"{r['por_tramo'][n]['cantidad']:>8.1f}"
                         f"{r['por_tramo'][n]['precio']:>9.1f}" for n, _ in TRAMOS)
        print(f"{etiqueta:<32}{r['posiciones']:>6}{r['fob_total_musd']:>10,.0f}   {fila}")
    razon = resultado[dim].get("razon_Q_segunda_sobre_primera")
    if razon:
        fila = "  ".join(f"{razon[n]:>8.1f}{'':>9}" for n, _ in TRAMOS)
        print(f"{'razón de cantidades (2ª/1ª)':<32}{'':>6}{'':>10}   {fila}")
    print()


print(f"\n-> {DATOS / 'analisis_heterogeneidad.json'}")
