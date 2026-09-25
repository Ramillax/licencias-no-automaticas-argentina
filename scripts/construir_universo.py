#!/usr/bin/env python3
"""
Reconstruye, desde el Arancel Externo Común y los dos anexos de Licencias No
Automáticas ya transcriptos, el universo de bienes de capital y las tres
trayectorias regulatorias que consume el panel.

Es el eslabón que faltaba: hasta ahora estos seis archivos existían en `datos/`
pero ningún programa los producía, de modo que la cadena de la tesis no se podía
correr desde la fuente original. Todos los demás programas los leen.

Entradas   datos/ncm_aec2017_layout.txt        (pdftotext -layout del AEC; se genera si falta)
           datos/lna_agosto2022_ocr.txt        (salida de ocr_anexo.py, Res. SC 1/2022)
           datos/lna_octubre2022_ocr.txt       (salida de ocr_anexo.py, Res. SC 26/2022)

Salidas    datos/ncm_aec2017_todas.txt         las 10.226 posiciones de 8 dígitos
           datos/bk_posiciones_aec2017.txt     posiciones marcadas BK
           datos/bit_posiciones_aec2017.txt    posiciones marcadas BIT
           datos/lna-transcripcion/bk_ruta_a_control.txt    G1
           datos/lna-transcripcion/bk_ruta_a_tratadas.txt   G2
           datos/lna-transcripcion/bk_ruta_a_nunca.txt      G3

Uso   python3 construir_universo.py                 verifica contra lo que ya está, no escribe
      python3 construir_universo.py --escribir      regenera los archivos
      python3 construir_universo.py --modo completo verifica con la regla corregida

MODOS. La marca BK/BIT vive en la cola de la fila del arancel, junto al AEC y al
derecho de importación. El problema es que el PDF parte filas largas en varias
líneas, y entonces la cola cae en una línea que ya no lleva el código.

  tesis     Regla original, documentada en datos/FUENTE-universo-bk.md: una sola
            línea, código y marca juntos. Reproduce exactamente los archivos con
            los que están hechos los resultados del trabajo. 1.122 BK.

  completo  Arma la fila entera antes de buscar la marca: pega las líneas de
            continuación, salta el mobiliario de página (folio, encabezado y el
            sello IF-...-APN-MP) y exige que el código esté en la columna cero,
            que es donde están las 10.226 filas reales del arancel. 1.222 BK.

La diferencia son 100 posiciones cuya descripción ocupa más de una línea. Ninguna
posición del modo `tesis` falta en el modo `completo`: es superconjunto estricto.
**El trabajo adoptó `completo` el 2026-09-04** y es el default. El modo `tesis` queda
disponible para reproducir los resultados anteriores a esa fecha.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
TRANS = DATOS / "lna-transcripcion"
PDF = DATOS / "ncm_aec2017.pdf"
LAYOUT = DATOS / "ncm_aec2017_layout.txt"

# Fila real del arancel: el código arranca en la columna cero. Las únicas
# apariciones sangradas de un código son referencias cruzadas dentro de la
# descripción de otra fila ("... envases de los ítem 4811.51.22 ó 4811.59.23"),
# que no son filas y no deben contarse.
RE_CODIGO = re.compile(r"^(\d{4}\.\d{2}\.\d{2})(?=\s)")
RE_OTRA_FILA = re.compile(r"^(?:\d{2}\.\d{2}|\d{4}\.\d{2}(?:\.\d)?)(?=\s)")
RE_MARCA = re.compile(r"(?<![A-Za-z0-9])(BK|BIT)(?![A-Za-z0-9])")
RE_UNA_LINEA = re.compile(r"^(\d{4}\.\d{2}\.\d{2}).*\s(BK|BIT)(?:\s|$)")

# Lo que el PDF intercala en medio de una fila sin cortarla.
RE_MOBILIARIO = re.compile(
    r"^\s*(página \d+ de \d+"
    r"|Arancel Externo Común.*"
    r"|ANEXO I"
    r"|NCM\s+DESCRIPCIÓN\s+AEC.*"
    r"|IF-\d{4}-\d+-APN-MP\s*)\s*$",
    re.IGNORECASE,
)
MAX_SALTO = 6          # líneas de mobiliario toleradas dentro de una fila
CAPITULOS_BK = ("84", "90")   # tramo de nomenclatura analizado, inclusive

# Fechas del régimen, tomadas del Boletín Oficial. La entrada es la publicación
# de la resolución que incorpora la posición; la salida, la de la que la retira.
ALTA_AGOSTO = "2022-08-25"     # Res. SC 1/2022
ALTA_OCTUBRE = "2022-10-04"    # Res. SC 26/2022
BAJA_GENERAL = "2023-12-27"    # Res. SC 1/2023, abrogación del régimen completo
REGIMEN = DATOS / "regimen"


def leer_layout():
    if not LAYOUT.exists():
        if not PDF.exists():
            sys.exit(f"falta {LAYOUT.name} y no está {PDF.name} para generarlo")
        subprocess.run(["pdftotext", "-layout", str(PDF), str(LAYOUT)], check=True)
    return LAYOUT.read_text(encoding="utf-8", errors="replace").splitlines()


def filas_completas(lineas):
    """Código -> texto de la fila entera, uniendo las líneas de continuación.

    El arancel es un PDF de 415 páginas maquetado como tabla. `pdftotext -layout`
    conserva las columnas, pero una fila cuya descripción no entra en el ancho se
    reparte en varios renglones y sólo el primero lleva el código. La marca BK
    viaja en la cola de la fila, a la derecha, así que en esas filas largas la
    marca aparece en un renglón sin código. Leer línea por línea las pierde: ese
    fue el defecto que en septiembre de 2026 dejó el universo en 1.113 posiciones
    en vez de 1.211.
    """
    filas, i = {}, 0
    while i < len(lineas):
        m = RE_CODIGO.match(lineas[i])
        if not m:
            i += 1
            continue

        # Acumula renglones hasta que empieza otra fila. El corte por «otra fila»
        # incluye los códigos de 4 y 6 dígitos (partidas y subpartidas), porque
        # son encabezados de grupo y marcan el final de la fila anterior.
        cuerpo, j, saltadas = [lineas[i]], i + 1, 0
        while j < len(lineas):
            linea = lineas[j]
            if RE_CODIGO.match(linea) or RE_OTRA_FILA.match(linea):
                break

            # Un salto de página puede caer en medio de una fila sin cortarla:
            # se descarta el mobiliario (folio, encabezado, sello IF-...-APN-MP)
            # y se sigue leyendo la misma fila del otro lado. El tope de 6 evita
            # que, si algo no se reconoce, la fila se coma media página.
            if not linea.strip() or RE_MOBILIARIO.match(linea):
                saltadas += 1
                if saltadas > MAX_SALTO:
                    break
                j += 1
                continue

            cuerpo.append(linea)
            j += 1

        # setdefault y no asignación: si un código apareciera dos veces, vale la
        # primera aparición, que es la fila del nomenclador. Comprobado: no pasa.
        filas.setdefault(m.group(1), " ".join(cuerpo))
        i = j
    return filas


def universo(lineas, modo):
    """Devuelve (todas, bk, bit) según el modo de lectura de la marca.

    `todas` se cuenta siempre por fila entera, en los dos modos: es el invariante
    de control del arancel (10.226 posiciones de ocho dígitos) contra el que se
    validan las transcripciones por OCR. Lo que cambia entre modos es solamente
    cómo se busca la marca BK/BIT.
    """
    todas = set(filas_completas(lineas))
    if modo == "tesis":
        bk, bit = set(), set()
        for linea in lineas:
            m = RE_UNA_LINEA.match(linea)
            if m:
                (bk if m.group(2) == "BK" else bit).add(m.group(1))
        return todas, bk, bit
    bk, bit = set(), set()
    for cod, texto in filas_completas(lineas).items():
        m = RE_MARCA.search(texto)
        if m:
            (bk if m.group(1) == "BK" else bit).add(cod)
    return todas, bk, bit


def leer_lista(path):
    return {c for c in path.read_text().split() if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", c)}


def trayectorias(bk, agosto, octubre):
    """G1 bajo LNA desde agosto · G2 entra en octubre · G3 nunca alcanzada.

    Los tres grupos son los que compara el capítulo 6. Se definen por la fecha de
    ENTRADA al régimen y no por la de salida, porque todas las posiciones salieron
    el mismo día: la Res. SC 1/2023 abrogó el régimen completo el 27-12-2023. Esa
    salida común es justamente la razón por la que el trabajo no estima un efecto
    causal, y está argumentada en el apartado de hipótesis.

    Dentro de los bienes de capital, el listado de octubre (Res. SC 26/2022)
    contiene al de agosto (Res. SC 1/2022): ninguna posición BK sale del régimen
    en octubre, y el `assert` de abajo lo comprueba. Por eso G3 se define contra
    octubre, que es el alcance máximo, y G2 tiene que restar agosto.

    ⚠️ En el universo completo eso NO vale: ocho posiciones del listado de agosto
    no figuran en el de octubre, o sea que salieron del régimen en esa fecha.
    Ninguna está marcada BK, así que no afectan a este trabajo, pero el archivo
    `datos/regimen/regimen-lna-argentina.csv` sí las refleja con su fecha de
    salida propia.
    """
    # El universo se acota a los capítulos 84 a 90. Capítulo 84 y 85 NO equivalen
    # a bienes de capital (traen electrodomésticos, teléfonos y audio): el recorte
    # lo hace la marca BK del arancel, y el rango de capítulos sólo excluye los
    # BK de otros capítulos, ajenos a la maquinaria que estudia el trabajo.
    bk8490 = {c for c in bk if CAPITULOS_BK[0] <= c[:2] <= CAPITULOS_BK[1]}

    g1 = bk8490 & agosto              # alcanzadas desde el primer listado
    g2 = (bk8490 & octubre) - agosto  # incorporadas por la ampliación de octubre
    g3 = bk8490 - octubre             # nunca alcanzadas (equipamiento médico)

    # Los tres grupos tienen que ser una partición exacta del universo: sin
    # solapamiento y sin sobrantes. Si esto falla, cambió alguna transcripción.
    assert g1 | g2 | g3 == bk8490 and not (g1 & g2) and not (g1 & g3) and not (g2 & g3)
    return bk8490, g1, g2, g3


def volcar(posiciones):
    return "".join(f"{c}\n" for c in sorted(posiciones))


def csv_regimen(agosto, octubre, bk, bit):
    """El régimen completo, una fila por posición alcanzada alguna vez.

    Es el archivo que un tercero querría sin correr nada: qué posición estuvo
    bajo licencia no automática, desde cuándo y hasta cuándo. Incluye TODO el
    universo alcanzado, no sólo los bienes de capital, porque el listado vale
    para cualquier estudio del régimen.

    ⚠️ Ocho posiciones del listado de agosto no figuran en el de octubre: para
    ésas la salida es el 4-10-2022 y no la abrogación general. Ninguna está
    marcada BK.
    """
    filas = ["ncm,capitulo,marca_aec,res_1_2022_agosto,res_26_2022_octubre,entrada,salida"]
    for c in sorted(agosto | octubre):
        en_a, en_o = c in agosto, c in octubre
        marca = "BK" if c in bk else ("BIT" if c in bit else "")
        entrada = ALTA_AGOSTO if en_a else ALTA_OCTUBRE
        salida = BAJA_GENERAL if en_o else ALTA_OCTUBRE
        filas.append(f"{c},{c[:2]},{marca},{'si' if en_a else 'no'},"
                     f"{'si' if en_o else 'no'},{entrada},{salida}")
    return "\n".join(filas) + "\n"


def csv_trayectorias(bk8490, g1, g2, g3):
    """Las 1.211 posiciones de bienes de capital con su trayectoria regulatoria.

    Es el corte que usa el trabajo: el universo de bienes de capital de los
    capítulos 84 a 90, cada posición etiquetada según cuándo entró al régimen.
    """
    filas = ["ncm,capitulo,trayectoria,entrada,salida,descripcion_trayectoria"]
    glosa = {"G1": "bajo licencia desde agosto de 2022",
             "G2": "incorporada en octubre de 2022",
             "G3": "nunca alcanzada por el régimen"}
    for c in sorted(bk8490):
        g = "G1" if c in g1 else ("G2" if c in g2 else "G3")
        entrada = "" if g == "G3" else (ALTA_AGOSTO if g == "G1" else ALTA_OCTUBRE)
        salida = "" if g == "G3" else BAJA_GENERAL
        filas.append(f"{c},{c[:2]},{g},{entrada},{salida},{glosa[g]}")
    return "\n".join(filas) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modo", choices=("completo", "tesis"), default="completo")
    ap.add_argument("--escribir", action="store_true", help="regenera los archivos en vez de solo verificar")
    args = ap.parse_args()

    lineas = leer_layout()
    todas, bk, bit = universo(lineas, args.modo)
    agosto = leer_lista(DATOS / "lna_agosto2022_ocr.txt")
    octubre = leer_lista(DATOS / "lna_octubre2022_ocr.txt")
    bk8490, g1, g2, g3 = trayectorias(bk, agosto, octubre)

    print(f"modo {args.modo}")
    print(f"  posiciones de 8 dígitos en el AEC : {len(todas):>6}")
    print(f"  marcadas BK                       : {len(bk):>6}")
    print(f"  marcadas BIT                      : {len(bit):>6}")
    print(f"  BK en los capítulos 84 a 90       : {len(bk8490):>6}")
    print(f"  LNA agosto 2022 / octubre 2022    : {len(agosto):>6} / {len(octubre)}")
    print(f"  G1 bajo LNA desde agosto          : {len(g1):>6}")
    print(f"  G2 entra en octubre               : {len(g2):>6}")
    print(f"  G3 nunca alcanzada                : {len(g3):>6}")

    salidas = [
        (DATOS / "ncm_aec2017_todas.txt", todas),
        (DATOS / "bk_posiciones_aec2017.txt", bk),
        (DATOS / "bit_posiciones_aec2017.txt", bit),
        (TRANS / "bk_ruta_a_control.txt", g1),
        (TRANS / "bk_ruta_a_tratadas.txt", g2),
        (TRANS / "bk_ruta_a_nunca.txt", g3),
    ]

    # Los dos CSV publicables: el régimen completo y el corte de bienes de
    # capital. Son lo que alguien ajeno al trabajo puede querer sin correr nada.
    REGIMEN.mkdir(exist_ok=True)
    csvs = [
        (REGIMEN / "regimen-lna-argentina.csv", csv_regimen(agosto, octubre, bk, bit)),
        (REGIMEN / "bienes-de-capital-trayectorias.csv",
         csv_trayectorias(bk8490, g1, g2, g3)),
    ]

    print()
    distintos = ausentes = 0
    for path, contenido in salidas:
        nuevo = volcar(contenido)
        if args.escribir:
            path.write_text(nuevo)
            print(f"  escrito    {path.name}  ({len(contenido)})")
            continue
        if not path.exists():
            print(f"  NO EXISTE  {path.name}")
            ausentes += 1
        elif path.read_text() == nuevo:
            print(f"  idéntico   {path.name}  ({len(contenido)})")
        else:
            viejo = leer_lista(path)
            print(f"  DIFIERE    {path.name}  (+{len(contenido - viejo)} / -{len(viejo - contenido)})")
            distintos += 1

    for path, contenido in csvs:
        if args.escribir:
            path.write_text(contenido, encoding="utf-8")
            print(f"  escrito    {path.name}  ({contenido.count(chr(10)) - 1} filas)")
        elif not path.exists():
            print(f"  NO EXISTE  {path.name}")
            ausentes += 1
        elif path.read_text(encoding="utf-8") != contenido:
            print(f"  DIFIERE    {path.name}")
            distintos += 1

    if not args.escribir:
        print()
        if ausentes:
            print(f"  {ausentes} archivo(s) NO EXISTEN todavía: correr con --escribir "
                  f"para generarlos.")
        elif distintos:
            print(f"  {distintos} archivo(s) no coinciden — correr con --escribir "
                  f"para regenerarlos")
        else:
            print("  todos los archivos coinciden con los del trabajo")

    # Un archivo AUSENTE es siempre un error: son la entrada de construir_panel.py
    # y sin ellos la cadena revienta tres etapas más adelante, lejos de la causa.
    # Una DIFERENCIA, en cambio, sólo es error en modo `tesis`, que es el que debe
    # reproducir bit a bit los archivos anteriores al 2026-09-04; en modo
    # `completo` la diferencia es esperable (las 98 posiciones que la regla vieja
    # perdía) y no tiene que cortar la cadena.
    if args.escribir:
        return 0
    if ausentes:
        return 1
    return 1 if (distintos and args.modo == "tesis") else 0


if __name__ == "__main__":
    sys.exit(main())
