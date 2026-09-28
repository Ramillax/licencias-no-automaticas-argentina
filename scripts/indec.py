#!/usr/bin/env python3
"""
Lectura del microdato de comercio exterior del INDEC, en un solo lugar.

El organismo publica un ZIP por año con una fila por operación de importación.
Leerlo tiene tres trampas que no se ven hasta que muerden. Acá están resueltas
una vez, y todos los programas del trabajo leen el dato a través de este módulo:
la ventana temporal y el formato numérico no se deciden en ningún otro lado.

    from indec import filas_importacion
    for ncm, mes, origen, fob, kg in filas_importacion():
        ...

No tiene efectos ni escribe nada: se puede importar desde cualquier lado. Sirve
para cualquier análisis sobre la base del INDEC, no sólo para este trabajo.

LAS TRES TRAMPAS

1. **Codificación latin-1 y punto y coma.** Es el formato en que el INDEC
   publica estos archivos. Leerlos como UTF-8 revienta en los acentos.

2. **Los decimales van con coma** («18508,06»), así que `float()` directo
   falla. Se relevaron las 1.975.302 filas y las seis tablas de control de
   2021-2026: todos los montos tienen exactamente la forma dígitos-coma-dígitos,
   sin separador de miles y sin campos vacíos. Por eso `num()` es estricto: un
   valor con otra forma no se «interpreta», se rechaza con error. Convertirlo en
   cero en silencio, como hace la lectura tolerante habitual, movería los
   totales sin que nada avisara.

3. **El archivo del año en curso se reescribe** a medida que el organismo cierra
   meses. Sin una ventana temporal explícita, bajar los datos un mes después
   alarga el período en silencio y mueve todos los resultados. Por eso el tope
   es la constante `VENTANA_HASTA`, definida acá y sólo acá. La ventana no
   alcanza sola: al republicar, el organismo también corrige meses que quedan
   dentro de ella (medido el 2026-09-28 sobre la edición de 2026). Por eso el
   repositorio guarda la edición exacta que usó el trabajo.

Se lee directamente de adentro del ZIP, sin descomprimir: son cientos de miles
de filas por año y se recorren una sola vez.
"""

import csv
import re
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDEC = RAIZ / "datos" / "indec"

# Ventana del trabajo. Ver la trampa 3: no es una preferencia, es lo que hace
# que el resultado no dependa del día en que se bajaron los datos.
VENTANA_HASTA = "2026-06"
ANIOS = range(2021, 2027)

# Columnas del microdato impomAA.csv:
# Año;mes;NCM;Porg;Pnet(kg);FOB(USD);Flete(USD);Seguro(USD);CIF(USD)
ANIO, MES, NCM, PORG, KG, FOB, FLETE, SEGURO, CIF = range(9)

_NUMERO = re.compile(r"-?\d+(,\d+)?")


def num(s):
    """Convierte un monto del INDEC («18508,06») a float.

    Acepta sólo la forma relevada en los archivos: dígitos, con parte decimal
    opcional separada por coma. Cualquier otra cosa levanta ValueError con el
    valor a la vista. Si el INDEC cambiara el formato, la cadena se detiene en
    vez de producir números distintos.
    """
    t = s.strip()
    if not _NUMERO.fullmatch(t):
        raise ValueError(f"monto con formato inesperado en el archivo del INDEC: {s!r}")
    return float(t.replace(",", "."))


def zip_anio(anio):
    """El ZIP de importaciones de un año, con un mensaje útil si falta."""
    ruta = INDEC / f"imports_{anio}_M.zip"
    if not ruta.exists():
        raise FileNotFoundError(
            f"falta {ruta.relative_to(RAIZ)}: corré primero scripts/descargar_fuentes.py")
    return zipfile.ZipFile(ruta)


def registros(anio):
    """Genera (mes, fila) de cada operación de un año, SIN aplicar la ventana.

    `mes` viene normalizado como «AAAA-MM»; `fila` es la lista de columnas tal
    como la publica el INDEC (ver las constantes ANIO…CIF). Es la lectura de más
    bajo nivel: la usan quienes necesitan contar también lo que queda fuera de la
    ventana, como el recuento contra la tabla de control.
    """
    z = zip_anio(anio)
    nombre = next(n for n in z.namelist() if n.startswith("impom") and n.endswith(".csv"))
    with z.open(nombre) as fh:
        lector = csv.reader((l.decode("latin-1") for l in fh), delimiter=";")
        next(lector)                                       # encabezado
        for fila in lector:
            if len(fila) < 6:
                continue
            yield f"{fila[ANIO].strip()}-{int(fila[MES]):02d}", fila


def tabla_control(anio):
    """Totales que el propio INDEC publica dentro del ZIP (itotmAA.csv).

    Devuelve (registros, kg, fob). Son la referencia externa contra la que
    `verificar.py` contrasta el recuento propio.
    """
    z = zip_anio(anio)
    nombre = next(n for n in z.namelist() if n.startswith("itotm") and n.endswith(".csv"))
    fila = list(csv.reader(z.read(nombre).decode("latin-1").splitlines(), delimiter=";"))[1]
    return int(fila[3]), num(fila[KG]), num(fila[FOB])


def filas_importacion(hasta=VENTANA_HASTA, anios=ANIOS, solo=None):
    """Genera (ncm, mes, origen, fob, kg) de cada operación dentro de la ventana.

    `solo`, si se pasa, es un conjunto de posiciones NCM (ocho dígitos sin
    puntos) y filtra a esas.

    No filtra por valor: quien necesite descartar las filas sin FOB lo hace del
    lado de afuera, porque no todos los usos quieren lo mismo.
    """
    for anio in anios:
        for mes, fila in registros(anio):
            if mes > hasta:
                continue
            ncm = fila[NCM].strip()
            if solo is not None and ncm not in solo:
                continue
            yield ncm, mes, fila[PORG].strip(), num(fila[FOB]), num(fila[KG])


if __name__ == "__main__":
    # Autoprueba mínima del formato numérico: corre sin datos descargados.
    assert num("18508,06") == 18508.06
    assert num(" 1200,000 ") == 1200.0
    assert num("0") == 0.0
    for malo in ("", "1.234", "1.234,5", "12,3,4", "abc"):
        try:
            num(malo)
        except ValueError:
            continue
        raise AssertionError(f"num() aceptó {malo!r}")
    print("indec.num: ok")
