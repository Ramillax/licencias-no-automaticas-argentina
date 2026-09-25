#!/usr/bin/env python3
"""
Lectura del microdato de comercio exterior del INDEC, en un solo lugar.

El organismo publica un ZIP por año con una fila por operación de importación.
Leerlo tiene tres trampas que no se ven hasta que muerden, y estaban resueltas
por separado en cada programa que lo usaba. Acá están resueltas una vez.

    from indec import filas_importacion
    for ncm, mes, origen, fob, kg in filas_importacion():
        ...

No tiene efectos ni escribe nada: se puede importar desde cualquier lado. Sirve
para cualquier análisis sobre la base del INDEC, no sólo para este trabajo.

LAS TRES TRAMPAS

1. **Codificación latin-1 y punto y coma.** Es el formato en que el INDEC
   publica estos archivos. Leerlos como UTF-8 revienta en los acentos.

2. **Los decimales van con coma** y los miles con punto, así que `float()`
   directo falla o, peor, lee mal.

3. **El archivo del año en curso se reescribe** a medida que el organismo cierra
   meses. Sin una ventana temporal explícita, bajar los datos un mes después
   alarga el período en silencio y mueve todos los resultados. Por eso el tope
   es un parámetro con valor por omisión y no algo que cada programa decida.

Se lee directamente de adentro del ZIP, sin descomprimir: son cientos de miles
de filas por año y se recorren una sola vez.
"""

import csv
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDEC = RAIZ / "datos" / "indec"

# Ventana del trabajo. Ver la trampa 3: no es una preferencia, es lo que hace
# que el resultado no dependa del día en que se bajaron los datos.
VENTANA_HASTA = "2026-06"
ANIOS = range(2021, 2027)


def num(s):
    """Convierte un número del formato del INDEC. Vacío o ilegible da 0,0."""
    s = s.strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except ValueError:
        return 0.0


def filas_importacion(hasta=VENTANA_HASTA, anios=ANIOS, solo=None):
    """Genera (ncm, mes, origen, fob, kg) de cada operación de importación.

    `mes` viene normalizado como «AAAA-MM», que es lo que permite comparar con
    la ventana y agrupar sin volver a parsear. `solo`, si se pasa, es un conjunto
    de posiciones NCM (ocho dígitos sin puntos) y filtra a esas.

    No filtra por valor: quien necesite descartar las filas sin FOB lo hace del
    lado de afuera, porque no todos los usos quieren lo mismo.
    """
    for anio in anios:
        z = zipfile.ZipFile(INDEC / f"imports_{anio}_M.zip")
        nombre = next(n for n in z.namelist() if n.startswith("impom"))
        with z.open(nombre) as fh:
            lector = csv.reader((l.decode("latin-1") for l in fh), delimiter=";")
            next(lector)                                   # encabezado
            for fila in lector:
                if len(fila) < 6:
                    continue
                ncm = fila[2].strip()
                if solo is not None and ncm not in solo:
                    continue
                mes = f"{fila[0].strip()}-{int(fila[1]):02d}"
                if mes > hasta:
                    continue
                yield ncm, mes, fila[3].strip(), num(fila[5]), num(fila[4])
