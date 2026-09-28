#!/usr/bin/env python3
"""
Verifica, contra los archivos originales, cada número publicado en el trabajo.

Corre en cinco bloques y termina con un veredicto:

  1. EL DATO ES REAL.  Recuenta los 1.975.302 registros de importación desde los
     CSV crudos del INDEC y los compara contra la tabla de control que el propio
     organismo publica dentro de cada ZIP (`itotmYY.csv`). El número de control
     no es del trabajo: es del INDEC.

  2. EL RÉGIMEN.  Reconstruye el universo de bienes de capital y las tres
     trayectorias regulatorias desde el Arancel Externo Común y las dos
     transcripciones de los anexos de licencias.

  3. EL PANEL y 4. LOS RESULTADOS.  Compara lo que quedó escrito en cada
     capítulo, de la introducción a las conclusiones, contra lo que producen
     los programas.

  5. EL TEXTO.  Comprueba que cada una de esas cifras siga apareciendo, tal cual,
     en el capítulo que la publica. Sin este bloque, una cifra editada a mano en
     el texto pasaría la verificación mientras la constante de acá siguiera
     diciendo lo de antes. Sólo corre donde está el texto (`borradores/`): el
     paquete público no lo incluye y ahí el bloque se saltea con un aviso.

Uso   python3 verificar.py           todo (lee 1,9 M de registros; ~30 s)
      python3 verificar.py --rapido  saltea el bloque 1

Requiere que la cadena se haya corrido antes: construir_universo.py,
construir_panel.py, origenes.py, analisis_grupos.py y analisis_heterogeneidad.py.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# El lector, el formato numérico y la ventana son los de indec.py. Que el recuento
# use el mismo lector que el panel no le quita valor de control: la referencia
# contra la que se compara es la tabla del INDEC, no otra lectura propia.
from indec import ANIOS, VENTANA_HASTA, NCM, KG, FOB, num, registros, tabla_control

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
TRANS = DATOS / "lna-transcripcion"
BORRADORES = RAIZ / "borradores"

VERDE, ROJO, GRIS, FIN = "\033[32m", "\033[31m", "\033[90m", "\033[0m"
if not sys.stdout.isatty():
    VERDE = ROJO = GRIS = FIN = ""

fallas = []
citas = []      # (concepto, capítulo, literales) para el bloque 5


def linea(concepto, tesis, calculado, ok, nota="", en=None):
    """Imprime una comparación y la registra si falla.

    Cómo leer este programa: el argumento `tesis` es una CONSTANTE ESCRITA A MANO,
    copiada del texto publicado; `calculado` sale de recorrer los datos en esta
    misma corrida. O sea, lo que se contrasta es el texto de la tesis contra el
    dato, no el dato contra sí mismo. Si alguien edita una cifra del texto sin
    rehacer el análisis, o rehace el análisis y le da otra cosa, esta línea falla.

    `en` = (capítulo, literal o tupla de literales): dónde publica el texto esa
    cifra y cómo está escrita ahí, con coma decimal y punto de miles. Lo usa el
    bloque 5 para cerrar el círculo del otro lado, texto contra constante. Si la
    cifra aparece en varios capítulos, `en` es una lista de esos pares.

    Por eso los literales de abajo no deben «arreglarse» para que pase la prueba:
    si una línea da ✗, lo que hay que corregir es el capítulo o el programa.
    """
    marca = f"{VERDE}ok{FIN}" if ok else f"{ROJO}✗ {FIN}"
    print(f"  {marca}  {concepto:<48} {tesis:>16}  {calculado:>16}  {GRIS}{nota}{FIN}")
    if not ok:
        fallas.append(concepto)
    for cap, literales in (en if isinstance(en, list) else [en] if en else []):
        citas.append((concepto, cap, (literales,) if isinstance(literales, str) else literales))


def cabecera(titulo):
    print(f"\n{titulo}")
    print(f"      {'':<48} {'en la tesis':>16}  {'recalculado':>16}")


def leer_lista(path):
    return {c for c in path.read_text().split() if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", c)}


def cerca(a, b):
    """Igualdad a un decimal, que es la precisión con que el texto publica."""
    return abs(a - b) < 0.05


def coma(x, d=1):
    """Una cifra como la escribe el texto: coma decimal."""
    return f"{x:.{d}f}".replace(".", ",")


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
        reg_of, kg_of, fob_of = tabla_control(anio)
        reg = kg = fob = 0
        for mes, f in registros(anio):
            reg += 1
            kg += num(f[KG])
            fob += num(f[FOB])
            if mes <= VENTANA_HASTA and f[NCM].strip() in universo:
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
        linea("total de registros leídos", "1,975,302", f"{tot_filas:,}", True,
              en=("cap04", "1.975.302"))
    else:
        # El INDEC republica el archivo del año en curso con los meses que va cerrando.
        # No es un error: es una edición posterior de la misma fuente, y por eso el
        # trabajo fija su ventana explícitamente en vez de tomar lo que traiga el archivo.
        print(f"  {GRIS}··  {'total de registros leídos':<48} {'1,975,302':>16} "
              f"{tot_filas:>16,}  edición posterior del INDEC "
              f"({tot_filas - 1_975_302:+,} registros fuera de la ventana){FIN}")
    linea(f"registros de bienes de capital hasta {VENTANA_HASTA}", "329,309",
          f"{tot_bk:,}", tot_bk == 329_309, en=("cap04", "329.309"))


# ---------------------------------------------------------------- bloque 2
def bloque_regimen():
    cabecera("2. EL RÉGIMEN — capítulo 3: universo y trayectorias, desde el arancel y los anexos")
    todas = leer_lista(DATOS / "ncm_aec2017_todas.txt")
    bk = leer_lista(DATOS / "bk_posiciones_aec2017.txt")
    bk8490 = {c for c in bk if "84" <= c[:2] <= "90"}
    ago = leer_lista(DATOS / "lna_agosto2022_ocr.txt")
    oct_ = leer_lista(DATOS / "lna_octubre2022_ocr.txt")
    g1 = leer_lista(TRANS / "bk_ruta_a_control.txt")
    g2 = leer_lista(TRANS / "bk_ruta_a_tratadas.txt")
    g3 = leer_lista(TRANS / "bk_ruta_a_nunca.txt")

    linea("posiciones NCM de 8 dígitos en el AEC", "10,226", f"{len(todas):,}",
          len(todas) == 10226, en=("cap03", "10.226"))
    linea("posiciones marcadas BK", "1,222", f"{len(bk):,}", len(bk) == 1222,
          en=("cap03", "1.222"))
    linea("BK en los capítulos 84 a 90", "1,211", f"{len(bk8490):,}", len(bk8490) == 1211,
          en=("cap03", "1.211"))
    linea("bajo LNA · agosto 2022 (Res. SC 1/2022)", "1,492", f"{len(ago):,}",
          len(ago) == 1492, en=("cap03", "1.492"))
    linea("bajo LNA · octubre 2022 (Res. SC 26/2022)", "4,193", f"{len(oct_):,}",
          len(oct_) == 4193, en=("cap03", "4.193"))

    bk_ago, bk_oct = len(bk8490 & ago), len(bk8490 & oct_)
    linea("BK bajo LNA en agosto 2022", "185 (15,3 %)",
          f"{bk_ago} ({100*bk_ago/len(bk8490):.1f} %)", bk_ago == 185,
          en=("cap03", ("185 posiciones", "15,3")))
    linea("BK bajo LNA en octubre 2022", "1,150 (95,0 %)",
          f"{bk_oct:,} ({100*bk_oct/len(bk8490):.1f} %)", bk_oct == 1150,
          en=("cap03", ("1.150", "95,0")))
    # Validación de la transcripción por OCR, sin necesidad de rehacer el OCR.
    # Cada código transcripto tiene que existir literalmente en el nomenclador
    # oficial. Es la prueba de que el listado no se inventó: son posiciones
    # reales del arancel, no cadenas de dígitos plausibles. Los que no aparecen
    # se revisaron uno por uno y son desdoblamientos de la VII Enmienda (NCM
    # 2022), posterior al arancel de 2017 que se usa como padrón.
    oct8490 = {c for c in oct_ if "84" <= c[:2] <= "90"}
    existen = len(oct8490 & todas)
    linea("transcripción · códigos de octubre en cap. 84-90", "2,261",
          f"{len(oct8490):,}", len(oct8490) == 2261, en=("cap03", "2.261"))
    linea("transcripción · existen literalmente en el AEC", "2,239",
          f"{existen:,}", existen == 2239, en=("cap01", "2.239"))
    linea("transcripción · desdoblamientos de la VII Enmienda", "22",
          f"{len(oct8490 - todas)}", len(oct8490 - todas) == 22,
          en=("cap01", "los 22 restantes"))

    # Concordancia del OCR con la segunda transcripción. Es la cifra que el
    # Anexo D.5 reporta como tasa de error; la calcula scripts/auditar_ocr.py y
    # acá se comprueba que el texto y los archivos sigan diciendo lo mismo.
    patron = leer_lista(TRANS / "lna_ch84_90.txt")
    linea("OCR · coincide con la 2ª transcripción", "2,260 / 2,261",
          f"{len(patron & oct8490):,} / {len(patron):,}",
          len(patron & oct8490) == 2260 and len(patron) == 2261,
          en=("cap03", "2.260"))

    linea("G1 · bajo LNA desde agosto", "185", f"{len(g1)}", len(g1) == 185)
    linea("G2 · entra en octubre, sale en dic-2023", "965", f"{len(g2)}", len(g2) == 965,
          en=("cap03", "965"))
    linea("G3 · nunca alcanzada", "61", f"{len(g3)}", len(g3) == 61,
          en=("cap03", "61 posiciones"))
    linea("las tres trayectorias suman el universo", "1,211",
          f"{len(g1|g2|g3):,}", (g1 | g2 | g3) == bk8490)

    # 3.8: la discrepancia de nomenclatura no mueve el resultado. Agregando a seis
    # dígitos, nivel estable frente a los desdoblamientos de la VII Enmienda.
    oct6 = {c[:7] for c in oct_}                   # «8429.51» = seis dígitos con el punto
    seis = 100 * len({c for c in bk8490 if c[:7] in oct6}) / len(bk8490)
    linea("BK bajo LNA en oct-2022, a seis dígitos", "95,3 %", f"{seis:.1f} %",
          cerca(seis, 95.3), en=("cap03", "95,3 %"))

    # 3.5: cobertura sobre el valor importado, ponderada por valor en el período.
    cob = json.loads((DATOS / "cobertura_por_valor.json").read_text())["periodo"]
    for clave, etiqueta, esperado in (("cob_todos_ago", "total importado · listado ago-22", 32.4),
                                      ("cob_todos_oct", "total importado · listado oct-22", 51.9),
                                      ("cob_bk_ago", "bienes de capital · listado ago-22", 38.7),
                                      ("cob_bk_oct", "bienes de capital · listado oct-22", 95.9)):
        linea(f"cobertura por valor · {etiqueta}", f"{coma(esperado)} %", f"{cob[clave]:.1f} %",
              cerca(cob[clave], esperado), en=("cap03", f"{coma(esperado)} %"))


# ---------------------------------------------------------------- bloque 3 y 4
def bloque_resultados():
    ser = json.loads((DATOS / "series_agregadas.json").read_text())
    org = json.loads((DATOS / "origenes.json").read_text())
    rob = json.loads((DATOS / "robustez_grupos.json").read_text())
    het = json.loads((DATOS / "analisis_heterogeneidad.json").read_text())

    cabecera("3. EL PANEL — capítulo 4 y anexo D")
    cob = ser["cobertura"]
    linea("celdas posición-mes del panel", "51,614", f"{cob['celdas_ncm_mes']:,}",
          cob["celdas_ncm_mes"] == 51614, en=("cap04", "51.614"))
    linea("meses cubiertos", "66", f"{cob['meses']}", cob["meses"] == 66,
          en=("cap04", "66 meses"))
    linea("filas con FOB > 0 y peso nulo", "0", f"{cob['filas_fob_sin_kg']}",
          cob["filas_fob_sin_kg"] == 0)

    for frec, etiqueta, esperado, caps in (("mes__ncm", "mensual", 21.8, ("anexos", "cap04", "cap08")),
                                           ("trim__ncm", "trimestral", 5.8, ("cap05",)),
                                           ("anio__ncm", "anual", 0.6, ("anexos",))):
        ix = ser["indices"][frec]
        ult = ix["periodos"][-1]
        deriva = round(ix["encadenado"][ult] - ix["base_primero"][ult], 1)
        linea(f"deriva de encadenamiento · {etiqueta}", f"{esperado:.1f}", f"{deriva:.1f}",
              cerca(deriva, esperado), en=[(c, coma(esperado)) for c in caps])

    # 4.6: cuántas posiciones aparea el índice anual contra la base 2021.
    ap = [v["celdas_base_2021"] for a, v in ser["indices"]["anio__ncm"]["apareo"].items() if a != "2021"]
    cobmin = min(v["cobertura_base_2021"] for a, v in ser["indices"]["anio__ncm"]["apareo"].items() if a != "2021")
    linea("índice anual · posiciones apareadas (mín–máx)", "934–1,032", f"{min(ap)}–{max(ap):,}",
          (min(ap), max(ap)) == (934, 1032) and cobmin > 0.99, en=("cap04", ("934", "1.032")))

    # Valor y participación en el total importado, 2021 contra 2025 (1.8, 4.3, 5.7, 8.8.1).
    anual = {s["periodo"]: s for s in ser["series"]["anio"]}
    total = {}
    for r in json.loads((DATOS / "cobertura_por_valor.json").read_text())["mensual"]:
        total[r["periodo"][:4]] = total.get(r["periodo"][:4], 0.0) + r["fob_total"]
    crec = 100 * (anual["2025"]["fob_usd"] / anual["2021"]["fob_usd"] - 1)
    p21 = 100 * anual["2021"]["fob_usd"] / total["2021"]
    p25 = 100 * anual["2025"]["fob_usd"] / total["2025"]
    linea("valor BK · crecimiento 2021 → 2025", "54 %", f"{crec:.1f} %", round(crec) == 54,
          en=[("cap01", "54 %"), ("cap05", "54 %"), ("cap08", "54 %")])
    linea("participación BK en el total · 2021 → 2025", "10,4 → 13,2 %", f"{p21:.1f} → {p25:.1f} %",
          cerca(p21, 10.4) and cerca(p25, 13.2),
          en=[("cap01", ("10,4 %", "13,2 %")), ("cap08", ("10,4 %", "13,2 %"))])

    cabecera("4. LOS RESULTADOS — capítulos 5, 6 y 7")
    # 5.4: el contraste de P1, 2023 contra 2025.
    a23, a25, a21 = anual["2023"], anual["2025"], anual["2021"]
    var = {
        "índice de cantidad": 100 * (a25["idx_cantidad"] / a23["idx_cantidad"] - 1),
        "índice de peso": 100 * (a25["kg_mensual"] / a23["kg_mensual"] - 1),
        "valor unitario por posición": 100 * (a25["idx_precio"] / a23["idx_precio"] - 1),
        "valor unitario por posición y origen":
            100 * (a25["idx_precio_ctrl_origen"] / a23["idx_precio_ctrl_origen"] - 1),
    }
    for (etq, v), esperado in zip(var.items(), (16.7, 21.3, -5.3, 0.3)):
        txt = ("+" if esperado > 0 else "−") + coma(abs(esperado)) + " %"
        linea(f"P1 · 2023 → 2025 · {etq}", txt, f"{v:+.1f} %", cerca(v, esperado), en=("cap05", txt))
    linea("P1 · rango de cantidades en las conclusiones", "+17 a +21 %",
          f"{var['índice de cantidad']:+.0f} a {var['índice de peso']:+.0f} %",
          round(var["índice de cantidad"]) == 17 and round(var["índice de peso"]) == 21,
          en=("cap08", "+17 a +21 %"))
    ch = org["bloques"]["China"]
    for anio, esperado in (("2021", 48.4), ("2025", 61.3)):
        v = ch[anio]["share_kg"]
        linea(f"China · % del peso importado en {anio}", f"{esperado:.1f} %", f"{v:.1f} %",
              cerca(v, esperado), en=("cap05", f"{esperado:.1f}".replace(".", ",")))

    tramos = (("G1 bajo LNA, G2 no", "I", 105.5),
              ("ambos bajo LNA", "II", 92.2),
              ("ninguno bajo LNA", "III", 78.0))
    for clave, romano, esperado in tramos:
        v = rob["completo"]["ratio_por_tramo"][clave]["ratio"]
        linea(f"razón de cantidades G2/G1 · tramo {romano}", f"{esperado:.1f}", f"{v:.1f}",
              cerca(v, esperado), en=("cap06", f"{esperado:.1f}".replace(".", ",")))

    # 6.6: las caídas de la razón entre tramos, en cada variante.
    for variante, c1, c2 in (("cap84", 5.3, 17.3), ("sin_top5", 19.9, 12.8)):
        t = [v["ratio"] for v in rob[variante]["ratio_por_tramo"].values()]
        d1, d2 = round(t[0] - t[1], 1), round(t[1] - t[2], 1)
        linea(f"robustez · {variante}: caídas I→II y II→III", f"{coma(c1)} / {coma(c2)}",
              f"{d1} / {d2}", cerca(d1, c1) and cerca(d2, c2), en=("cap06", (coma(c1), coma(c2))))
    ultimo = {v: [x["ratio"] for x in rob[v]["ratio_por_tramo"].values()][-1] for v in rob if "ratio_por_tramo" in rob[v]}
    ninguna = all(t[2] <= t[1] for t in ([x["ratio"] for x in rob[v]["ratio_por_tramo"].values()] for v in ultimo))
    linea("robustez · ninguna variante se recupera tras la abrogación", "sí",
          "sí" if ninguna else "no", ninguna)

    for variante, etiqueta, n1, n2 in (("cap84", "solo capítulo 84", 146, 686),
                                       ("sin_top5", "sin las 5 mayores", 180, 960),
                                       ("sin_top20", "sin las 20 mayores", 165, 945)):
        r = rob[variante]
        ok = r["G1"]["posiciones"] == n1 and r["G2"]["posiciones"] == n2
        linea(f"robustez · {etiqueta} (G1/G2)", f"{n1}/{n2}",
              f"{r['G1']['posiciones']}/{r['G2']['posiciones']}", ok,
              en=("cap06", (str(n1), str(n2))))

    # Capítulo 7: los cuatro atributos, contrastados dentro de G2.
    g2c = het["cortes"]["posiciones_G2"]
    linea("cap. 7 · posiciones de G2 con comercio", "929", f"{g2c}", g2c == 929,
          en=("cap07", "929"))
    esperados = {"D1": (97.3, 122.7, 111.9), "D2": (103.6, 117.0, 122.8),
                 "D3": (123.0, 126.1, 115.6), "TB": (113.6, 150.4, 122.3)}
    picos = {}
    for dim, valores in esperados.items():
        clave = next(k for k in het if k.startswith(dim + " "))
        r = het[clave]["razon_Q_segunda_sobre_primera"]
        calc = tuple(r[t] for t in ("I", "II", "III"))
        picos[dim] = ("I", "II", "III")[calc.index(max(calc))]
        linea(f"cap. 7 · {dim} razón de cantidades I / II / III",
              " / ".join(f"{v:.1f}" for v in valores),
              " / ".join(f"{v:.1f}" for v in calc),
              all(cerca(a, b) for a, b in zip(calc, valores)),
              en=("cap07", tuple(f"{v:.1f}".replace(".", ",") for v in valores)))
    # El resultado del capítulo no es ninguna de esas cifras sino su forma: sólo
    # la diferenciación del producto alcanza el máximo en el tramo III. Se
    # comprueba aparte porque puede romperse sin que ninguna cifra cambie mucho.
    solo_d2 = [d for d, t in picos.items() if t == "III"] == ["D2"]
    linea("cap. 7 · sólo D2 alcanza su máximo en el tramo III", "sí",
          "sí" if solo_d2 else ", ".join(f"{d}→{t}" for d, t in picos.items()), solo_d2)


# ---------------------------------------------------------------- bloque 5
def bloque_texto():
    print("\n5. EL TEXTO — cada cifra de arriba, escrita tal cual en el capítulo que la publica")
    if not any(BORRADORES.glob("cap0*.md")):
        print(f"  {GRIS}··  salteado: el texto de la tesis no viaja en el paquete de replicación{FIN}")
        return
    textos = {}
    for p in BORRADORES.glob("*.md"):
        m = re.match(r"(cap\d\d|anexos)\b", p.stem)
        if m:
            textos[m.group(1)] = p.read_text(encoding="utf-8")
    faltan = 0
    for concepto, cap, literales in citas:
        texto = textos.get(cap)
        ausentes = [l for l in literales if texto is None or l not in texto]
        if ausentes:
            faltan += 1
            fallas.append(f"texto · {concepto}")
            print(f"  {ROJO}✗ {FIN}  {concepto:<48} {cap:>8}  no aparece: {', '.join(ausentes)}")
    if not faltan:
        print(f"  {VERDE}ok{FIN}  {len(citas)} cifras encontradas en su capítulo")


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
    bloque_texto()

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
