# Universo de bienes de capital

| Archivo | Contenido |
|---|---|
| `bk_posiciones_aec2017.txt` | **1.122 posiciones NCM marcadas `BK`** (bienes de capital) |
| `bit_posiciones_aec2017.txt` | 323 posiciones marcadas `BIT` (informática y telecomunicaciones) |
| `ncm_aec2017_todas.txt` | Las 10.226 posiciones de 8 dígitos, para validar transcripciones |
| `ncm_aec2017.pdf` | Fuente original, 415 páginas |

Extraído el 2026-08-07 del Arancel Externo Común (Anexo I, NCM 2017, VI Enmienda):
https://www.argentina.gob.ar/sites/default/files/nomenclatura_comun_del_mercosur_ncm.pdf

## Cómo se regenera

**Lo produce `scripts/construir_universo.py`**, que además deriva las tres trayectorias
regulatorias (`lna-transcripcion/bk_ruta_a_*.txt`) cruzando este universo con los dos anexos
de licencias transcriptos. Hasta el 2026-09-04 ningún programa producía estos seis archivos:
existían sueltos en `datos/` y toda la cadena los leía, de modo que el trabajo no se podía
rehacer desde la fuente. Correr `python3 scripts/construir_universo.py` sin argumentos
verifica que los archivos en disco sean exactamente los que salen del arancel.

## Dos reglas de lectura, y por qué importa

La marca `BK` vive en la cola de la fila del arancel, al lado del AEC y del derecho de
importación. El PDF parte las filas largas en varias líneas, y entonces la cola queda en una
línea que ya no lleva el código.

**Regla `tesis`** (la original, y la que produce los resultados publicados). Una sola línea,
código y marca juntos:

```bash
grep -E '^[0-9]{4}\.[0-9]{2}\.[0-9]{2}.*\sBK(\s|$)' ncm_aec2017_layout.txt
```

**→ 1.122 BK · 1.113 en los capítulos 84 a 90 · G1 175, G2 884, G3 54.**

**Regla `completo`** (`--modo completo`). Arma la fila entera antes de buscar la marca: pega
las líneas de continuación, salta el mobiliario de página (folio, encabezado y el sello
`IF-...-APN-MP`) y exige que el código esté en la columna cero, que es donde están las 10.226
filas reales —las únicas apariciones sangradas de un código son referencias cruzadas dentro
de la descripción de otra fila, como «envases de los ítem 4811.51.22 ó 4811.59.23»—.

**→ 1.222 BK · 1.211 en los capítulos 84 a 90 · G1 185, G2 965, G3 61.**

⚠ **La regla original omite 98 posiciones del tramo 84–90**, todas con descripción de más de
una línea. Es superconjunto estricto: ninguna posición del modo `tesis` falta en el modo
`completo`. Medido contra el dato del INDEC, lo omitido pesa **6,2 % del valor importado del
universo**, con una participación estable año a año (5,3 % a 6,9 %), y la cobertura del
listado de octubre sobre bienes de capital pasa de 95,1 % a 95,0 %. Las ocho de mayor valor
son `9031.80.99`, `8414.80.21`, `8483.90.00`, `8428.33.00`, `8408.90.10`, `9022.12.00`,
`8422.30.23` y `8477.10.11`.

**Cuál usar es una decisión del trabajo, no del programa.** El default es `tesis`, que es con
lo que están escritos los capítulos. Adoptar `completo` obliga a recorrer los capítulos 3, 5,
6 y 7, porque cambian los denominadores y el tamaño de los tres grupos.

Ambas reglas se validan contra el mismo invariante: las **10.226** posiciones de ocho dígitos,
que es el control que ya usaba el trabajo para auditar las transcripciones por OCR.

## Advertencias que siguen vigentes

⚠ Es la **VI Enmienda (2017)** y los anexos de LNA usan la **VII (2022)**: 21 códigos difieren por
desdoblamiento. Para el trabajo final conviene reconstruir el universo sobre la nomenclatura de 2022
con las tablas de correlación oficiales. Ver `identificacion.md` §Límites.

⚠ Capítulos 84 y 85 **no** equivalen a bienes de capital — incluyen electrodomésticos, teléfonos y
equipos de audio. Filtrar por la marca `BK`, nunca por capítulo.
