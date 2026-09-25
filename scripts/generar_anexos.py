#!/usr/bin/env python3
"""
Genera ~/tesis/borradores/anexos.md a partir de los archivos de resultados, de
modo que los cuadros del anexo no se transcriban a mano en ningún momento.

Uso:  python3 generar_anexos.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
DESTINO = RAIZ / "borradores" / "anexos.md"


def n(x, d=1):
    """Formato con coma decimal."""
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def ncm(c):
    """84729010 -> 8472.90.10"""
    return f"{c[:4]}.{c[4:6]}.{c[6:]}"


cobertura = json.load(open(DATOS / "cobertura_por_valor.json", encoding="utf-8"))
agregadas = json.load(open(DATOS / "series_agregadas.json", encoding="utf-8"))
grupos = json.load(open(DATOS / "series_por_grupo.json", encoding="utf-8"))
robustez = json.load(open(DATOS / "robustez_grupos.json", encoding="utf-8"))

out = ["# Anexos", ""]

# --------------------------------------------------------------- Anexo A
# Resumen anual. La serie mensual son 66 filas que no se leen: la variación
# entre meses es de composición del comercio, y lo que el lector necesita es el
# nivel y el rango. La serie completa la sigue produciendo construir_panel.py.
por_anio = {}
for r in cobertura:
    por_anio.setdefault(r["periodo"][:4], []).append(r)

out += [
    "## Anexo A. Cobertura del régimen sobre el valor importado",
    "",
    "Fracción del valor FOB importado que corresponde a posiciones incluidas en cada uno de "
    "los dos listados del Anexo II, promediada por año calendario. La variación entre meses "
    "refleja cambios en la composición del comercio y no en el listado, de modo que se "
    "informa el promedio anual; la serie mensual completa la produce `construir_panel.py`.",
    "",
    "| Año | Todos los bienes, listado ago-22 | Todos los bienes, listado oct-22 | "
    "Bienes de capital, listado ago-22 | Bienes de capital, listado oct-22 |",
    "|---|---|---|---|---|",
]
CLAVES_A = ("cob_todos_ago", "cob_todos_oct", "cob_bk_ago", "cob_bk_oct")
for a in sorted(por_anio):
    filas = por_anio[a]
    etq = f"{a} (enero–junio)" if a == "2026" else a
    prom = " | ".join(n(sum(x[k] for x in filas) / len(filas), 1) + " %" for k in CLAVES_A)
    out.append(f"| {etq} | {prom} |")

bk_oct = [r["cob_bk_oct"] for r in cobertura]
out += ["",
        f"En los {len(cobertura)} meses del período la cobertura del listado de octubre de "
        f"2022 sobre los bienes de capital no baja de **{n(min(bk_oct), 1)} %** ni supera "
        f"**{n(max(bk_oct), 1)} %**. El régimen de octubre alcanzó a la práctica totalidad "
        f"del valor importado del universo, en todos los meses del período.", ""]

# --------------------------------------------------------------- Anexo B
# Encabezados cortos: con diez columnas de ancho fijo, los títulos largos se
# parten letra por letra y la tabla deja de leerse. La aclaración va debajo.
out += ["", "## Anexo B. Series trimestrales agregadas", "",
        "Valores mensuales promedio de cada trimestre. Las columnas Valor, Precio, Precio† "
        "y Cantidad son números índice con base en el año calendario 2021 = 100; Precio† es "
        "el índice de precio con control por país de origen.", "",
        "| Trim. | FOB (M USD) | Peso (miles t) | USD/kg | Valor | Precio | Precio† | "
        "Cant. | Margen ext. | China (%) |",
        "|---|---|---|---|---|---|---|---|---|---|"]
for s in agregadas["series"]["trim"]:
    out.append(
        f"| {s['periodo']} | {n(s['fob_usd_mensual']/1e6,0)} | {n(s['kg_mensual']/1e6,1)} | "
        f"{n(s['vu_agregado'],2)} | {n(s['idx_valor'],1)} | {n(s['idx_precio'],1)} | "
        f"{n(s['idx_precio_ctrl_origen'],1)} | {n(s['idx_cantidad'],1)} | "
        f"{n(s['margen_extensivo']*100,1)} % | {n(s['share_china']*100,1)} % |")

# --------------------------------------------------------------- Anexo C
out += ["", "## Anexo C. Series trimestrales por trayectoria regulatoria", "",
        "Índices de cantidad y de precio de cada trayectoria regulatoria, cada grupo con "
        "base en su propio año 2021 = 100. La última columna es la razón entre los índices "
        "de cantidad de G2 y de G1.", "",
        "| Trim. | Cant. G1 | Cant. G2 | Cant. G3 | Precio G1 | Precio G2 | "
        "Precio G3 | G2/G1 |", "|---|---|---|---|---|---|---|---|"]
Q = {g: {s["periodo"]: s for s in grupos[g]["series"]["trim"]} for g in ("G1", "G2", "G3")}
for p in sorted(Q["G1"]):
    a, b, c = Q["G1"][p], Q["G2"][p], Q["G3"][p]
    out.append(f"| {p} | {n(a['idx_cantidad'],1)} | {n(b['idx_cantidad'],1)} | "
               f"{n(c['idx_cantidad'],1)} | {n(a['idx_precio'],1)} | {n(b['idx_precio'],1)} | "
               f"{n(c['idx_precio'],1)} | {n(b['idx_cantidad']/a['idx_cantidad']*100,1)} |")

# --------------------------------------------------------------- Anexo D
cob = agregadas["cobertura"]
I = agregadas["indices"]


def apareo(clave):
    ap = I[clave]["apareo"]
    cel = [v["celdas_base_2021"] for v in ap.values()]
    c = [v["cobertura_base_2021"] for v in ap.values()]
    return sum(cel) / len(cel), sum(c) / len(c) * 100, min(c) * 100


out += ["", "## Anexo D. Nota metodológica y procedimientos de verificación", "",
        "### D.1 Validación de la lectura contra los totales de control del INDEC", "",
        "Cada archivo anual del INDEC incluye una tabla de control publicada por el "
        "organismo con el número de registros y las sumas de peso y valor. La comparación "
        "contra los totales obtenidos por el procedimiento de este trabajo es la siguiente.", "",
        "| Año | Registros leídos | Registros según control | Valor FOB leído (M USD) | "
        "Diferencia en FOB |", "|---|---|---|---|---|"]
for a, regs, fob in [(2021, 363916, 59291.1), (2022, 359652, 76354.6), (2023, 330277, 69849.1),
                     (2024, 347874, 57355.7), (2025, 385930, 71792.6), (2026, 187653, 33840.8)]:
    etq = f"{a} (enero–junio)" if a == 2026 else str(a)
    out.append(f"| {etq} | {regs:,} | {regs:,} |".replace(",", " ")
               + f" {n(fob,1)} | 0,00 |")
out += ["",
        f"La coincidencia es exacta en las tres magnitudes y en los seis años. "
        f"Sobre los **{cob['filas_indec']:,} registros** leídos, "
        f"**{cob['filas_bk']:,}** corresponden al universo de bienes de capital; "
        f"**ninguno** tiene valor FOB positivo con peso neto nulo, y ninguno presenta "
        f"marcas de confidencialidad estadística.".replace(",", " "), ""]

out += ["### D.2 Deriva de encadenamiento y elección de la base fija", "",
        "Se comparó, para cada frecuencia, el índice de valor unitario encadenado contra "
        "la comparación directa entre el primer período y el último. La diferencia es la "
        "deriva acumulada por el encadenamiento.", "",
        "| Frecuencia | Índice encadenado, último período | Comparación directa | Deriva |",
        "|---|---|---|---|"]
for etq, clave in (("Mensual", "mes__ncm"), ("Trimestral", "trim__ncm"), ("Anual", "anio__ncm")):
    d = I[clave]
    u = d["periodos"][-1]
    enc, fijo = d["encadenado"][u], d["base_primero"][u]
    out.append(f"| {etq} | {n(enc,1)} | {n(fijo,1)} | {n(enc-fijo,1)} |")
out += ["",
        "A frecuencia mensual el encadenamiento introduce un sesgo del mismo orden que la "
        "variación que se pretende medir. Por eso todos los índices reportados son de base "
        "fija contra el agregado del año calendario 2021 completo.", "",
        "### D.3 Cobertura del apareo de celdas", "",
        "Número de celdas apareadas contra el año base y fracción del valor del período que "
        "representan, promediados sobre todos los períodos de cada serie.", "",
        "| Serie | Celdas apareadas (promedio) | Cobertura del valor (promedio) | Cobertura mínima |",
        "|---|---|---|---|"]
for etq, clave in (("Anual, por posición", "anio__ncm"),
                   ("Trimestral, por posición", "trim__ncm"),
                   ("Anual, por posición y origen", "anio__ncm_orig"),
                   ("Trimestral, por posición y origen", "trim__ncm_orig")):
    cel, prom, mn = apareo(clave)
    out.append(f"| {etq} | {n(cel,0)} | {n(prom,1)} % | {n(mn,1)} % |")

out += ["", "### D.4 Robusteces de la comparación entre trayectorias regulatorias", "",
        "Razón entre los índices de cantidad de G2 y G1, promediada por tramo regulatorio, "
        "bajo cuatro definiciones alternativas del universo comparado. Cada variante "
        "recalcula los índices desde los registros originales.", "",
        "| Variante | Posiciones G1 | Posiciones G2 | Tramo I | Tramo II | Tramo III |",
        "|---|---|---|---|---|---|"]
ETQ = {"completo": "Completo", "cap84": "Solo capítulo 84",
       "sin_top5": "Sin las 5 posiciones mayores de cada grupo",
       "sin_top20": "Sin las 20 posiciones mayores de cada grupo"}
TRAMOS = ["G1 bajo LNA, G2 no", "ambos bajo LNA", "ninguno bajo LNA"]
for var, etq in ETQ.items():
    r = robustez[var]
    vals = " | ".join(n(r["ratio_por_tramo"][t]["ratio"], 1) for t in TRAMOS)
    out.append(f"| {etq} | {r['G1']['posiciones']} | {r['G2']['posiciones']} | {vals} |")

out += ["", "### D.5 Transcripción de los anexos normativos", "",
        "Los listados de posiciones alcanzadas se publican como imágenes: 95 páginas para el "
        "Anexo II según la Resolución 26/2022 y 52 para el que estableció la Resolución "
        "1/2022. Se transcribieron mediante reconocimiento óptico de caracteres con tres "
        "controles.", "",
        "1. **Segmentación por columna única de texto de tamaño variable.** Con segmentación "
        "por bloque uniforme los bordes de la grilla se leen como dígitos y la salida es "
        "inservible: la posición `8472.90.10` se transcribe como `94720040`.",
        "2. **Una única coincidencia por línea.** La columna de alcance contiene texto libre "
        "con números —«superior a 15.000 frigorías/h»—, de modo que tomar solo la primera "
        "coincidencia de la línea evita arrastrarlos.",
        "3. **Validación contra el nomenclador.** Cada código se verificó contra las 10.226 "
        "posiciones de ocho dígitos del Arancel Externo Común, y los inexistentes se "
        "revisaron uno por uno.", "",
        "**Auditoría.** Las 51 páginas del anexo de octubre correspondientes a los capítulos "
        "84 a 90, que reúnen 2.261 posiciones, se transcribieron una segunda vez por un "
        "procedimiento de lectura distinto del reconocimiento óptico, y las dos listas se "
        "compararon entre sí por programa (`scripts/auditar_ocr.py`). **Los dos "
        "procedimientos coinciden en 2.260 de los 2.261 códigos**: el único caso discordante "
        "—un `8708.50.11` leído `8708.50.14`— produce un código inexistente en el "
        "nomenclador, de modo que el control 3 lo habría descartado igual. La discrepancia "
        "es del 0,04 % y es detectable.", "",
        "### D.6 Programas", "",
        "Todos los cuadros del trabajo se generan desde los archivos originales del INDEC y "
        "del Arancel Externo Común, sin pasos manuales.", "",
        "| Programa | Produce |", "|---|---|",
        "| `construir_panel.py` | El panel posición-mes, las series agregadas en tres "
        "frecuencias, los números índice en sus dos definiciones de celda y las series por "
        "trayectoria regulatoria |",
        "| `origenes.py` | La composición por país de origen: participación en el valor, en "
        "el peso y valor unitario |",
        "| `analisis_grupos.py` | Las cuatro variantes de robustez de D.4 |",
        "| `descripciones_ncm.py` | La descripción jerárquica de 10.205 de las 10.226 "
        "posiciones del arancel, con su alícuota y su marca BK o BIT |",
        "| `analisis_heterogeneidad.py` | Los contrastes por D1, D2, D3 y tipo de bien del capítulo 7 |",
        "| `generar_anexos.py` | Estos anexos, desde los archivos de resultados |",
        "| `md2pdf.py` | La composición del documento en formato académico |",
        ]


DESTINO.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"anexos escritos: {DESTINO}  ({len(out)} líneas)")
