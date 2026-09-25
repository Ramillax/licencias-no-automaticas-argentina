#!/usr/bin/env python3
"""
Construye el panel de bienes de capital importados, 2021-2026, a partir de los
archivos masivos del INDEC (Comercio Exterior, importaciones mensuales).

Salidas, en ~/tesis/datos/:
  panel_bk_ncm_mes.csv    NCM(8) x mes: fob, kg, orígenes, HHI, Asia, China, grupo
  series_agregadas.json   series mensuales agregadas y números índice
  series_por_grupo.json   lo mismo, desagregado por trayectoria regulatoria

Universo: las 1.113 posiciones de bienes de capital de los capítulos 84 a 90,
clasificadas por trayectoria regulatoria G1 / G2 / G3 (ver identificacion.md).

Uso:  python3 construir_panel.py
"""

import csv
import json
import math
import zipfile
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indices import tornqvist_con_cobertura as tornqvist   # ver indices.py

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
INDEC = DATOS / "indec"
TRANS = DATOS / "lna-transcripcion"
PAISES = DATOS / "referencia" / "paises_indec.csv"

ANIOS = range(2021, 2027)
# El INDEC republica el archivo del año en curso a medida que cierra meses nuevos:
# el de 2026 pasó de 6 a más meses después de la descarga original. La ventana del
# trabajo es explícita para que el panel no dependa de la fecha en que se bajó el dato.
VENTANA_HASTA = "2026-06"


# --------------------------------------------------------------------------
# 1. Universo y trayectorias regulatorias
# --------------------------------------------------------------------------

def leer_posiciones(path):
    """Lee un listado de NCM y lo devuelve normalizado a 8 dígitos sin puntos."""
    out = set()
    for linea in Path(path).read_text().splitlines():
        cod = linea.strip().replace(".", "")
        if len(cod) == 8 and cod.isdigit():
            out.add(cod)
    return out


G1 = leer_posiciones(TRANS / "bk_ruta_a_control.txt")    # LNA desde antes de ago-2022
G2 = leer_posiciones(TRANS / "bk_ruta_a_tratadas.txt")   # entra oct-2022, sale dic-2023
G3 = leer_posiciones(TRANS / "bk_ruta_a_nunca.txt")      # nunca bajo LNA

GRUPO = {}
for cod in G1:
    GRUPO[cod] = "G1"
for cod in G2:
    GRUPO[cod] = "G2"
for cod in G3:
    GRUPO[cod] = "G3"

UNIVERSO = set(GRUPO)
assert len(UNIVERSO) == len(G1) + len(G2) + len(G3), "hay posiciones en más de un grupo"


# --------------------------------------------------------------------------
# 2. Países: continente por prefijo del código INDEC (1 África, 2 América,
#    3 Asia, 4 Europa, 5 Oceanía, 9 indeterminado)
# --------------------------------------------------------------------------

NOMBRE_PAIS = {}
with open(PAISES, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        NOMBRE_PAIS[r["porg"]] = r["nombre_es"]

CHINA = "310"
# Orígenes asiáticos de costo alto: no cuentan como penetración de bajo costo.
ASIA_ALTO_COSTO = {"320", "309", "318", "333"}  # Japón, Corea del Sur, Israel, Singapur


def es_asia(porg):
    return porg.startswith("3")


# --------------------------------------------------------------------------
# 3. Lectura de los archivos del INDEC
# --------------------------------------------------------------------------

def num(s):
    """Convierte '4500,000' a float. Devuelve None si no es numérico."""
    s = s.strip()
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except ValueError:
        return None


# (ncm, periodo, porg) -> [fob, kg, flete, seguro]
micro = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])

filas_total = 0
filas_bk = 0
filas_fob_sin_kg = 0
filas_descartadas = 0
filas_fuera_ventana = 0

for anio in ANIOS:
    z = zipfile.ZipFile(INDEC / f"imports_{anio}_M.zip")
    nombre = next(n for n in z.namelist() if n.startswith("impom") and n.endswith(".csv"))
    with z.open(nombre) as fh:
        lector = csv.reader((l.decode("latin-1") for l in fh), delimiter=";")
        next(lector)  # encabezado
        for fila in lector:
            if len(fila) < 6:
                continue
            filas_total += 1
            periodo = f"{fila[0].strip()}-{int(fila[1]):02d}"
            if periodo > VENTANA_HASTA:
                filas_fuera_ventana += 1
                continue
            ncm = fila[2].strip()
            if ncm not in UNIVERSO:
                continue
            filas_bk += 1
            porg = fila[3].strip()
            kg = num(fila[4])
            fob = num(fila[5])
            if fob is None or fob <= 0:
                filas_descartadas += 1
                continue
            if kg is None or kg <= 0:
                filas_fob_sin_kg += 1
                kg = 0.0
            c = micro[(ncm, periodo, porg)]
            c[0] += fob
            c[1] += kg
            c[2] += num(fila[6]) or 0.0
            c[3] += num(fila[7]) or 0.0

print(f"filas leídas           : {filas_total:,}")
if filas_fuera_ventana:
    print(f"filas posteriores a {VENTANA_HASTA}: {filas_fuera_ventana:,}  (descartadas: quedan fuera de la ventana del trabajo)")
print(f"filas de bienes de cap.: {filas_bk:,}")
print(f"filas sin FOB positivo : {filas_descartadas:,}")
print(f"filas con FOB>0 y kg=0 : {filas_fob_sin_kg:,}")


# --------------------------------------------------------------------------
# 4. Panel NCM x mes
# --------------------------------------------------------------------------

celdas = defaultdict(lambda: {"fob": 0.0, "kg": 0.0, "orig": defaultdict(float),
                              "asia": 0.0, "asia_bajo": 0.0, "china": 0.0})

for (ncm, periodo, porg), (fob, kg, _fl, _sg) in micro.items():
    c = celdas[(ncm, periodo)]
    c["fob"] += fob
    c["kg"] += kg
    c["orig"][porg] += fob
    if es_asia(porg):
        c["asia"] += fob
        if porg not in ASIA_ALTO_COSTO:
            c["asia_bajo"] += fob
    if porg == CHINA:
        c["china"] += fob


def hhi(shares):
    return sum(s * s for s in shares)


panel = []
for (ncm, periodo), c in celdas.items():
    partes = [v / c["fob"] for v in c["orig"].values()]
    panel.append({
        "ncm": ncm,
        "periodo": periodo,
        "grupo": GRUPO[ncm],
        "fob": round(c["fob"], 2),
        "kg": round(c["kg"], 3),
        "vu": round(c["fob"] / c["kg"], 6) if c["kg"] > 0 else "",
        "n_orig": len(c["orig"]),
        "hhi": round(hhi(partes), 6),
        "fob_asia": round(c["asia"], 2),
        "fob_asia_bajo": round(c["asia_bajo"], 2),
        "fob_china": round(c["china"], 2),
    })
panel.sort(key=lambda r: (r["periodo"], r["ncm"]))

with open(DATOS / "panel_bk_ncm_mes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(panel[0].keys()))
    w.writeheader()
    w.writerows(panel)
print(f"panel NCM x mes        : {len(panel):,} filas")


# --------------------------------------------------------------------------
# 5. Números índice de valor unitario
# --------------------------------------------------------------------------
# Se construyen sobre celdas apareadas entre dos períodos. Dos definiciones de
# celda:
#   "ncm"       posición arancelaria — mide el valor unitario de la posición
#   "ncm_orig"  posición x país de origen — además neutraliza el efecto de los
#               cambios en la composición de orígenes sobre el valor unitario
#
# Y tres frecuencias. La mensual sirve de control: al aparear canastas chicas y
# ruidosas acumula deriva de encadenamiento. La trimestral y la anual son las
# que se reportan.

MESES = sorted({p for (_, p, _) in micro})


def clave_periodo(mes, frec):
    a, m = mes.split("-")
    if frec == "mes":
        return mes
    if frec == "trim":
        return f"{a}-T{(int(m) - 1) // 3 + 1}"
    return a


def agregar(frec, celda, filtro_grupo=None):
    """(periodo -> clave de celda -> [fob, kg]) para una frecuencia y definición."""
    out = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    for (ncm, mes, porg), (fob, kg, _fl, _sg) in micro.items():
        if filtro_grupo and GRUPO[ncm] != filtro_grupo:
            continue
        k = ncm if celda == "ncm" else (ncm, porg)
        d = out[clave_periodo(mes, frec)][k]
        d[0] += fob
        d[1] += kg
    return out



def serie_indice(frec, celda, filtro_grupo=None):
    """Tres versiones del índice de valor unitario, para contrastarlas:

    encadenado   producto de relativos entre períodos consecutivos
    base_primero comparación directa contra el primer período
    base_2021    comparación directa contra el agregado del año 2021 completo,
                 que es la que se reporta: no acumula deriva de encadenamiento
                 y su período base no arrastra estacionalidad
    """
    datos = agregar(frec, celda, filtro_grupo)
    base_2021 = agregar("anio", celda, filtro_grupo)["2021"]
    periodos = sorted(datos)
    primero = periodos[0]
    encadenado = {primero: 100.0}
    fijo = {primero: 100.0}
    b21, apareo = {}, {}
    for i, p in enumerate(periodos):
        if i:
            rel, n, cob = tornqvist(datos[periodos[i - 1]], datos[p])
            encadenado[p] = encadenado[periodos[i - 1]] * (rel if rel else 1.0)
            rel_f, _, _ = tornqvist(datos[primero], datos[p])
            fijo[p] = 100.0 * (rel_f if rel_f else 1.0)
        else:
            n, cob = 0, 0.0
        rel_b, n_b, cob_b = tornqvist(base_2021, datos[p])
        b21[p] = 100.0 * (rel_b if rel_b else 1.0)
        apareo[p] = {"celdas": n, "cobertura_valor": round(cob, 4),
                     "celdas_base_2021": n_b, "cobertura_base_2021": round(cob_b, 4)}
    return periodos, encadenado, fijo, b21, apareo


INDICES = {}
for frec in ("mes", "trim", "anio"):
    for celda in ("ncm", "ncm_orig"):
        periodos, enc, fijo, b21, apareo = serie_indice(frec, celda)
        INDICES[f"{frec}__{celda}"] = {
            "periodos": periodos,
            "encadenado": {p: round(v, 3) for p, v in enc.items()},
            "base_primero": {p: round(v, 3) for p, v in fijo.items()},
            "base_2021": {p: round(v, 3) for p, v in b21.items()},
            "apareo": apareo,
        }
print("índices calculados     : " + ", ".join(INDICES))


# --------------------------------------------------------------------------
# 6. Series descriptivas
# --------------------------------------------------------------------------

def descriptivas(frec, filtro_grupo=None):
    """Series de valor, cantidad, variedad y concentración por período."""
    agr = defaultdict(lambda: {"fob": 0.0, "kg": 0.0, "flete": 0.0, "seguro": 0.0,
                               "orig": defaultdict(float),
                               "asia": 0.0, "asia_bajo": 0.0, "china": 0.0,
                               "pos": defaultdict(lambda: {"fob": 0.0, "orig": defaultdict(float)})})
    for (ncm, mes, porg), (fob, kg, flete, seguro) in micro.items():
        if filtro_grupo and GRUPO[ncm] != filtro_grupo:
            continue
        d = agr[clave_periodo(mes, frec)]
        d["fob"] += fob
        d["kg"] += kg
        d["flete"] += flete
        d["seguro"] += seguro
        d["orig"][porg] += fob
        if es_asia(porg):
            d["asia"] += fob
            if porg not in ASIA_ALTO_COSTO:
                d["asia_bajo"] += fob
        if porg == CHINA:
            d["china"] += fob
        p = d["pos"][ncm]
        p["fob"] += fob
        p["orig"][porg] += fob

    n_universo = sum(1 for c in UNIVERSO if not filtro_grupo or GRUPO[c] == filtro_grupo)
    meses_por_periodo = defaultdict(set)
    for (_, mes, _) in micro:
        meses_por_periodo[clave_periodo(mes, frec)].add(mes)

    out = []
    for p in sorted(agr):
        d = agr[p]
        fob = d["fob"]
        n_meses = len(meses_por_periodo[p])
        posiciones = d["pos"]
        n_orig_pos = sorted(len(v["orig"]) for v in posiciones.values())
        hhi_pos_pond = sum(
            hhi([x / v["fob"] for x in v["orig"].values()]) * v["fob"]
            for v in posiciones.values()) / fob if fob else None
        out.append({
            "periodo": p,
            "meses": n_meses,
            "fob_usd": round(fob, 2),
            "fob_usd_mensual": round(fob / n_meses, 2),
            "kg": round(d["kg"], 1),
            "kg_mensual": round(d["kg"] / n_meses, 1),
            "vu_agregado": round(fob / d["kg"], 4) if d["kg"] else None,
            "flete_seguro_pct_fob": round((d["flete"] + d["seguro"]) / fob * 100, 3) if fob else None,
            "posiciones_activas": len(posiciones),
            "margen_extensivo": round(len(posiciones) / n_universo, 4),
            "orig_distintos": len(d["orig"]),
            "orig_por_pos_mediana": n_orig_pos[len(n_orig_pos) // 2] if n_orig_pos else 0,
            "orig_por_pos_promedio": round(sum(n_orig_pos) / len(n_orig_pos), 3) if n_orig_pos else 0,
            "orig_por_pos_pond": round(
                sum(len(v["orig"]) * v["fob"] for v in posiciones.values()) / fob, 3) if fob else 0,
            "hhi_por_pos_pond": round(hhi_pos_pond, 5) if hhi_pos_pond is not None else None,
            "hhi_agregado": round(hhi([v / fob for v in d["orig"].values()]), 5) if fob else None,
            "share_asia": round(d["asia"] / fob, 5) if fob else None,
            "share_asia_bajo": round(d["asia_bajo"] / fob, 5) if fob else None,
            "share_china": round(d["china"] / fob, 5) if fob else None,
        })
    return out


series = {frec: descriptivas(frec) for frec in ("mes", "trim", "anio")}

# Índices de valor, precio y cantidad, todos con base en el año 2021 = 100.
# El de cantidad es implícito: valor deflactado por el de valor unitario.
base_valor = next(s for s in series["anio"] if s["periodo"] == "2021")["fob_usd_mensual"]
for frec in ("mes", "trim", "anio"):
    idx_p = INDICES[f"{frec}__ncm"]["base_2021"]
    idx_po = INDICES[f"{frec}__ncm_orig"]["base_2021"]
    for s in series[frec]:
        s["idx_valor"] = round(s["fob_usd_mensual"] / base_valor * 100, 3)
        s["idx_precio"] = idx_p.get(s["periodo"])
        s["idx_precio_ctrl_origen"] = idx_po.get(s["periodo"])
        s["idx_cantidad"] = (round(s["idx_valor"] / s["idx_precio"] * 100, 3)
                             if s["idx_precio"] else None)

salida = {
    "universo": {
        "posiciones": len(UNIVERSO), "G1": len(G1), "G2": len(G2), "G3": len(G3),
        "fuente": "marca BK del Arancel Externo Común, capítulos 84 a 90; "
                  "trayectorias regulatorias según identificacion.md",
    },
    "cobertura": {
        "filas_indec": filas_total, "filas_bk": filas_bk,
        "filas_sin_fob": filas_descartadas, "filas_fob_sin_kg": filas_fob_sin_kg,
        "celdas_ncm_mes": len(celdas), "celdas_ncm_orig_mes": len(micro),
        "meses": len(MESES), "desde": MESES[0], "hasta": MESES[-1],
    },
    "nota_indices": (
        "Törnqvist encadenado sobre celdas con comercio positivo en ambos períodos. "
        "'ncm' aparea por posición arancelaria; 'ncm_orig' por posición y país de "
        "origen, lo que neutraliza los cambios de composición de orígenes. "
        "'base_fija' compara cada período directamente contra el primero y sirve "
        "para medir la deriva de encadenamiento."
    ),
    "indices": INDICES,
    "series": series,
}

with open(DATOS / "series_agregadas.json", "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False, indent=1)
print(f"series agregadas       : {len(series['mes'])} meses, "
      f"{len(series['trim'])} trimestres, {len(series['anio'])} años")

# --------------------------------------------------------------------------
# 7. Lo mismo, desagregado por trayectoria regulatoria
# --------------------------------------------------------------------------
# Cada grupo se indexa contra su propio año 2021, de modo que los índices son
# comparables entre sí como variaciones respecto de la propia base del grupo.

por_grupo = {}
for g in ("G1", "G2", "G3"):
    ser = {frec: descriptivas(frec, g) for frec in ("mes", "trim", "anio")}
    idx = {}
    for frec in ("mes", "trim", "anio"):
        for celda in ("ncm", "ncm_orig"):
            periodos, enc, fijo, b21, apareo = serie_indice(frec, celda, g)
            idx[f"{frec}__{celda}"] = {
                "periodos": periodos,
                "base_2021": {p: round(v, 3) for p, v in b21.items()},
                "encadenado": {p: round(v, 3) for p, v in enc.items()},
                "apareo": apareo,
            }
    base_valor_g = next(s for s in ser["anio"] if s["periodo"] == "2021")["fob_usd_mensual"]
    for frec in ("mes", "trim", "anio"):
        idx_p = idx[f"{frec}__ncm"]["base_2021"]
        idx_po = idx[f"{frec}__ncm_orig"]["base_2021"]
        for s in ser[frec]:
            s["idx_valor"] = round(s["fob_usd_mensual"] / base_valor_g * 100, 3)
            s["idx_precio"] = idx_p.get(s["periodo"])
            s["idx_precio_ctrl_origen"] = idx_po.get(s["periodo"])
            s["idx_cantidad"] = (round(s["idx_valor"] / s["idx_precio"] * 100, 3)
                                 if s["idx_precio"] else None)
    por_grupo[g] = {"posiciones": sum(1 for c in UNIVERSO if GRUPO[c] == g),
                    "series": ser, "indices": idx}

with open(DATOS / "series_por_grupo.json", "w", encoding="utf-8") as f:
    json.dump(por_grupo, f, ensure_ascii=False, indent=1)
print("series por grupo       : G1, G2, G3 con índices propios")
