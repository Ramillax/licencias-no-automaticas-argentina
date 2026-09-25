#!/usr/bin/env python3
"""
Verifica, contra los archivos originales, cada número publicado en el trabajo.

Corre en tres bloques y termina con un veredicto:

  1. EL DATO ES REAL.  Recuenta los 1.975.302 registros de importación desde los
     CSV crudos del INDEC y los compara contra la tabla de control que el propio
     organismo publica dentro de cada ZIP (`itotmYY.csv`). El número de control
     no es del trabajo: es del INDEC.

  2. EL RÉGIMEN.  Reconstruye el universo de bienes de capital y las tres
     trayectorias regulatorias desde el Arancel Externo Común y las dos
     transcripciones de los anexos de licencias.

  3. LOS RESULTADOS.  Compara lo que quedó escrito en cada capítulo contra lo
     que producen los programas.

Uso   python3 verificar.py           todo (lee 1,9 M de registros; ~30 s)
      python3 verificar.py --rapido  saltea el bloque 1

Requiere que la cadena se haya corrido antes: construir_universo.py,
construir_panel.py, origenes.py y analisis_grupos.py.
"""

import argparse
import csv
import json
import re
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
INDEC = DATOS / "indec"
TRANS = DATOS / "lna-transcripcion"
ANIOS = range(2021, 2027)
VENTANA_HASTA = "2026-06"   # ver construir_panel.py

VERDE, ROJO, GRIS, FIN = "\033[32m", "\033[31m", "\033[90m", "\033[0m"
if not sys.stdout.isatty():
    VERDE = ROJO = GRIS = FIN = ""

fallas = []


def linea(concepto, tesis, calculado, ok, nota=""):
    """Imprime una comparación y la registra si falla.

    Cómo leer este programa: el argumento `tesis` es una CONSTANTE ESCRITA A MANO,
    copiada del texto publicado; `calculado` sale de recorrer los datos en esta
    misma corrida. O sea, lo que se contrasta es el texto de la tesis contra el
    dato, no el dato contra sí mismo. Si alguien edita una cifra del texto sin
    rehacer el análisis, o rehace el análisis y le da otra cosa, esta línea falla.

    Por eso los literales de abajo no deben «arreglarse» para que pase la prueba:
    si una línea da ✗, lo que hay que corregir es el capítulo o el programa.
    """
    marca = f"{VERDE}ok{FIN}" if ok else f"{ROJO}✗ {FIN}"
    print(f"  {marca}  {concepto:<44} {tesis:>16}  {calculado:>16}  {GRIS}{nota}{FIN}")
    if not ok:
        fallas.append(concepto)


def cabecera(titulo):
    print(f"\n{titulo}")
    print(f"      {'':<44} {'en la tesis':>16}  {'recalculado':>16}")


def num(s):
    s = s.strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except ValueError:
        return 0.0


def leer_lista(path):
    return {c for c in path.read_text().split() if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", c)}


# ---------------------------------------------------------------- bloque 1
def bloque_control():
    cabecera("1. EL DATO ES REAL — recuento propio contra la tabla de control del INDEC")
    tot_filas = tot_bk = 0
    universo = {c.replace(".", "") for c in
                leer_lista(TRANS / "bk_ruta_a_control.txt") |
                leer_lista(TRANS / "bk_ruta_a_tratadas.txt") |
                leer_lista(TRANS / "bk_ruta_a_nunca.txt")}

    for anio in ANIOS:
        # Cada ZIP del INDEC trae dos archivos: el microdato (impomYY.csv, una
        # fila por operación) y una tabla de totales del propio organismo
        # (itotmYY.csv). Se recorre el primero y se compara contra el segundo.
        # El patrón vale como control porque el número de referencia lo publica
        # el INDEC, no este trabajo: si la lectura del CSV estuviera mal, los
        # totales no cerrarían.
        z = zipfile.ZipFile(INDEC / f"imports_{anio}_M.zip")
        micro = next(n for n in z.namelist() if n.startswith("impom") and n.endswith(".csv"))
        ctrl = next(n for n in z.namelist() if n.startswith("itotm") and n.endswith(".csv"))

        fila_ctrl = list(csv.reader(
            z.read(ctrl).decode("latin-1").splitlines(), delimiter=";"))[1]
        reg_of, kg_of, fob_of = int(fila_ctrl[3]), num(fila_ctrl[4]), num(fila_ctrl[5])

        reg = kg = fob = 0
        with z.open(micro) as fh:
            lector = csv.reader((l.decode("latin-1") for l in fh), delimiter=";")
            next(lector)
            for f in lector:
                if len(f) < 6:
                    continue
                reg += 1
                kg += num(f[4])
                fob += num(f[5])
                if f"{f[0].strip()}-{int(f[1]):02d}" > VENTANA_HASTA:
                    continue
                if f[2].strip() in universo:
                    tot_bk += 1
        tot_filas += reg

        # Registros: igualdad exacta. Montos: tolerancia de un dólar y un kilo,
        # que es error de redondeo al sumar cientos de miles de decimales, no
        # holgura metodológica. Cualquier diferencia real es mucho mayor.
        ok = reg == reg_of and abs(fob - fob_of) < 1.0 and abs(kg - kg_of) < 1.0
        linea(f"{anio} · registros / FOB (M USD)",
              f"{reg_of:,} / {fob_of/1e6:,.1f}",
              f"{reg:,} / {fob/1e6:,.1f}",
              ok, "coincidencia exacta" if ok else f"dif FOB {fob-fob_of:+,.2f}")

    if tot_filas == 1_975_302:
        linea("total de registros leídos", "1,975,302", f"{tot_filas:,}", True)
    else:
        # El INDEC republica el archivo del año en curso con los meses que va cerrando.
        # No es un error: es una edición posterior de la misma fuente, y por eso el
        # trabajo fija su ventana explícitamente en vez de tomar lo que traiga el archivo.
        print(f"  {GRIS}··  {'total de registros leídos':<44} {'1,975,302':>16} "
              f"{tot_filas:>16,}  edición posterior del INDEC "
              f"({tot_filas - 1_975_302:+,} registros fuera de la ventana){FIN}")
    linea(f"registros de bienes de capital hasta {VENTANA_HASTA}", "329,309",
          f"{tot_bk:,}", tot_bk == 329_309)


# ---------------------------------------------------------------- bloque 2
def bloque_regimen():
    cabecera("2. EL RÉGIMEN — universo y trayectorias, desde el arancel y los anexos")
    todas = leer_lista(DATOS / "ncm_aec2017_todas.txt")
    bk = leer_lista(DATOS / "bk_posiciones_aec2017.txt")
    bk8490 = {c for c in bk if "84" <= c[:2] <= "90"}
    ago = leer_lista(DATOS / "lna_agosto2022_ocr.txt")
    oct_ = leer_lista(DATOS / "lna_octubre2022_ocr.txt")
    g1 = leer_lista(TRANS / "bk_ruta_a_control.txt")
    g2 = leer_lista(TRANS / "bk_ruta_a_tratadas.txt")
    g3 = leer_lista(TRANS / "bk_ruta_a_nunca.txt")

    linea("posiciones NCM de 8 dígitos en el AEC", "10,226", f"{len(todas):,}", len(todas) == 10226)
    linea("posiciones marcadas BK", "1,222", f"{len(bk):,}", len(bk) == 1222)
    linea("BK en los capítulos 84 a 90", "1,211", f"{len(bk8490):,}", len(bk8490) == 1211)
    linea("bajo LNA · agosto 2022 (Res. SC 1/2022)", "1,492", f"{len(ago):,}", len(ago) == 1492)
    linea("bajo LNA · octubre 2022 (Res. SC 26/2022)", "4,193", f"{len(oct_):,}", len(oct_) == 4193)

    bk_ago, bk_oct = len(bk8490 & ago), len(bk8490 & oct_)
    linea("BK bajo LNA en agosto 2022", "185 (15,3 %)",
          f"{bk_ago} ({100*bk_ago/len(bk8490):.1f} %)", bk_ago == 185)
    linea("BK bajo LNA en octubre 2022", "1,150 (95,0 %)",
          f"{bk_oct:,} ({100*bk_oct/len(bk8490):.1f} %)", bk_oct == 1150)
    # Validación de la transcripción por OCR, sin necesidad de rehacer el OCR.
    # Cada código transcripto tiene que existir literalmente en el nomenclador
    # oficial. Es la prueba de que el listado no se inventó: son posiciones
    # reales del arancel, no cadenas de dígitos plausibles. Los que no aparecen
    # se revisaron uno por uno y son desdoblamientos de la VII Enmienda (NCM
    # 2022), posterior al arancel de 2017 que se usa como padrón.
    oct8490 = {c for c in oct_ if "84" <= c[:2] <= "90"}
    existen = len(oct8490 & todas)
    linea("transcripción · códigos de octubre en cap. 84-90", "2,261",
          f"{len(oct8490):,}", len(oct8490) == 2261)
    linea("transcripción · existen literalmente en el AEC", "2,239",
          f"{existen:,}", existen == 2239)
    linea("transcripción · desdoblamientos de la VII Enmienda", "22",
          f"{len(oct8490 - todas)}", len(oct8490 - todas) == 22)

    # Concordancia del OCR con la segunda transcripción. Es la cifra que el
    # Anexo D.5 reporta como tasa de error; la calcula scripts/auditar_ocr.py y
    # acá se comprueba que el texto y los archivos sigan diciendo lo mismo.
    patron = leer_lista(TRANS / "lna_ch84_90.txt")
    linea("OCR · coincide con la 2ª transcripción", "2,260 / 2,261",
          f"{len(patron & oct8490):,} / {len(patron):,}",
          len(patron & oct8490) == 2260 and len(patron) == 2261)

    linea("G1 · bajo LNA desde agosto", "185", f"{len(g1)}", len(g1) == 185)
    linea("G2 · entra en octubre, sale en dic-2023", "965", f"{len(g2)}", len(g2) == 965)
    linea("G3 · nunca alcanzada", "61", f"{len(g3)}", len(g3) == 61)
    linea("las tres trayectorias suman el universo", "1,211",
          f"{len(g1|g2|g3):,}", (g1 | g2 | g3) == bk8490)


# ---------------------------------------------------------------- bloque 3
def bloque_resultados():
    ser = json.loads((DATOS / "series_agregadas.json").read_text())
    org = json.loads((DATOS / "origenes.json").read_text())
    rob = json.loads((DATOS / "robustez_grupos.json").read_text())

    cabecera("3. EL PANEL — capítulo 4 y anexo D")
    cob = ser["cobertura"]
    linea("celdas posición-mes del panel", "51,614", f"{cob['celdas_ncm_mes']:,}",
          cob["celdas_ncm_mes"] == 51614)
    linea("meses cubiertos", "66", f"{cob['meses']}", cob["meses"] == 66)
    linea("filas con FOB > 0 y peso nulo", "0", f"{cob['filas_fob_sin_kg']}",
          cob["filas_fob_sin_kg"] == 0)

    for frec, etiqueta, esperado in (("mes__ncm", "mensual", 21.8),
                                     ("trim__ncm", "trimestral", 5.8),
                                     ("anio__ncm", "anual", 0.6)):
        ix = ser["indices"][frec]
        ult = ix["periodos"][-1]
        deriva = round(ix["encadenado"][ult] - ix["base_primero"][ult], 1)
        linea(f"deriva de encadenamiento · {etiqueta}", f"{esperado:.1f}", f"{deriva:.1f}",
              abs(deriva - esperado) < 0.05)

    cabecera("4. LOS RESULTADOS — capítulos 5, 6 y 7")
    ch = org["bloques"]["China"]
    linea("China · % del peso importado en 2021", "48,4 %", f"{ch['2021']['share_kg']:.1f} %",
          abs(ch["2021"]["share_kg"] - 48.4) < 0.05)
    linea("China · % del peso importado en 2025", "61,3 %", f"{ch['2025']['share_kg']:.1f} %",
          abs(ch["2025"]["share_kg"] - 61.3) < 0.05)

    tramos = (("G1 bajo LNA, G2 no", "I", 105.5),
              ("ambos bajo LNA", "II", 92.2),
              ("ninguno bajo LNA", "III", 78.0))
    for clave, romano, esperado in tramos:
        v = rob["completo"]["ratio_por_tramo"][clave]["ratio"]
        linea(f"razón de cantidades G2/G1 · tramo {romano}", f"{esperado:.1f}", f"{v:.1f}",
              abs(v - esperado) < 0.05)

    for variante, etiqueta, n1, n2 in (("cap84", "solo capítulo 84", 146, 686),
                                       ("sin_top5", "sin las 5 mayores", 180, 960),
                                       ("sin_top20", "sin las 20 mayores", 165, 945)):
        r = rob[variante]
        ok = r["G1"]["posiciones"] == n1 and r["G2"]["posiciones"] == n2
        linea(f"robustez · {etiqueta} (G1/G2)", f"{n1}/{n2}",
              f"{r['G1']['posiciones']}/{r['G2']['posiciones']}", ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true", help="saltea el recuento del dato crudo")
    args = ap.parse_args()

    print("VERIFICACIÓN DEL TRABAJO CONTRA LAS FUENTES ORIGINALES")
    print(f"proyecto: {RAIZ}")
    if not args.rapido:
        bloque_control()
    else:
        print(f"\n{GRIS}1. EL DATO ES REAL — salteado (--rapido){FIN}")
    bloque_regimen()
    bloque_resultados()

    print()
    if fallas:
        print(f"{ROJO}{len(fallas)} verificación(es) no coinciden con el texto:{FIN}")
        for f in fallas:
            print(f"   · {f}")
        return 1
    print(f"{VERDE}Todo lo verificado coincide con lo publicado en el trabajo.{FIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
