# Licencias no automáticas de importación en la Argentina, a nivel de posición arancelaria

[![regimen](https://github.com/Ramillax/licencias-no-automaticas-argentina/actions/workflows/regimen.yml/badge.svg)](https://github.com/Ramillax/licencias-no-automaticas-argentina/actions/workflows/regimen.yml)
[![reproduccion](https://github.com/Ramillax/licencias-no-automaticas-argentina/actions/workflows/reproduccion.yml/badge.svg)](https://github.com/Ramillax/licencias-no-automaticas-argentina/actions/workflows/reproduccion.yml)

**Este repositorio reconstruye qué posiciones arancelarias de la Nomenclatura Común del
MERCOSUR estuvieron sujetas a licencias no automáticas de importación entre 2021 y 2026, con
fecha, y construye el panel de importaciones del INDEC que permite medir qué pasó con ellas.**

Ese listado no estaba disponible en ningún formato utilizable. Las resoluciones que definen el
régimen publican sus anexos como **imágenes escaneadas** en el Boletín Oficial: 147 páginas sin
texto seleccionable, inservibles para cualquier análisis cuantitativo. Acá están transcriptas,
validadas contra el nomenclador oficial y con la fecha en que cada posición entró y salió del
régimen.

## Qué hay acá

| | |
|---|---|
| **El régimen reconstruido** | 1.492 posiciones bajo licencia en agosto de 2022 y 4.193 desde octubre, hasta la abrogación del 27 de diciembre de 2023. Dentro de bienes de capital: de 185 a 1.150 posiciones en seis semanas |
| **Las trayectorias regulatorias** | Cada posición clasificada según cuándo entró al régimen y cuándo salió, que es lo que permite comparar grupos entre sí |
| **El panel de importaciones** | 1.975.302 registros del INDEC procesados; 51.614 celdas de posición-mes con comercio, 2021–2026, con valor, peso, valor unitario, orígenes y concentración |
| **Los índices** | Números índice de Törnqvist de precio y cantidad, en dos definiciones de celda: por posición y por posición × país de origen |
| **Los verificadores** | Programas que contrastan la transcripción contra el nomenclador, el recuento contra las tablas de control del INDEC y las propiedades matemáticas de los índices |

Los resultados no viajan como dato estático: **son programas que los reconstruyen desde las
fuentes oficiales**, que sí vienen incluidas en la edición que usó el trabajo. Así se puede
auditar cada paso y adaptar la cadena a otro universo de posiciones.

### Los datos, sin correr nada

Dos archivos en `datos/regimen/` se pueden abrir directamente:

| Archivo | Qué tiene |
|---|---|
| `regimen-lna-argentina.csv` | **4.201 posiciones** alcanzadas alguna vez por el régimen, con la fecha en que entraron y salieron, y la marca del arancel (BK/BIT) de cada una |
| `bienes-de-capital-trayectorias.csv` | Las **1.211 posiciones de bienes de capital** de los capítulos 84 a 90, etiquetadas según su trayectoria: bajo licencia desde agosto de 2022, incorporadas en octubre, o nunca alcanzadas |

Los dos son producto de los programas, no archivos sueltos: `construir_universo.py`
los regenera desde los anexos transcriptos e informa, archivo por archivo, si quedaron
idénticos a los publicados o cambiaron. En cada cambio al repositorio lo comprueba
además la integración continua (ver [Comprobación automática](#comprobación-automática)).

**Columnas de `regimen-lna-argentina.csv`**

| Columna | Contenido |
|---|---|
| `ncm` | Posición NCM de 8 dígitos, con puntos (`8429.51.99`) |
| `capitulo` | Los dos primeros dígitos |
| `marca_aec` | `BK` (bien de capital), `BIT` (informática y telecomunicaciones) o vacío, según el Arancel Externo Común |
| `res_1_2022_agosto` · `res_26_2022_octubre` | `si` si la posición figura en el Anexo II de cada resolución |
| `entrada` · `salida` | Fechas de entrada y salida del régimen, en ISO 8601. La salida es la abrogación (2023-12-27), salvo para las 8 posiciones de agosto que la resolución de octubre no repitió, que salen el 2022-10-04 |

**Columnas de `bienes-de-capital-trayectorias.csv`**

| Columna | Contenido |
|---|---|
| `ncm` · `capitulo` | Como arriba |
| `trayectoria` | `G1` bajo licencia desde agosto de 2022 · `G2` incorporada en octubre · `G3` nunca alcanzada |
| `entrada` · `salida` | Fechas del régimen para esa posición; vacías en `G3` |
| `descripcion_trayectoria` | La trayectoria en palabras |

Cuatro posiciones de `G3` (`8448.51.00`, `8480.79.00`, `8543.30.00` y `8708.50.11`) figuran como nunca alcanzadas porque sus códigos de 2017 no aparecen en el anexo, pero estuvieron alcanzadas bajo los códigos en que las desdobló la VII Enmienda (NCM 2022). Se las mantiene en `G3` porque el trabajo no usa ese grupo como término de comparación.

### Los módulos importables

| Módulo | Qué resuelve |
|---|---|
| `scripts/indec.py` | Lee el microdato de comercio exterior del INDEC: codificación latin-1, decimales con coma y la ventana temporal que evita que el resultado dependa del día de la descarga. Es el único lector de la cadena, y el formato numérico es estricto: un monto con una forma distinta de la relevada en los archivos detiene la cadena en vez de convertirse en cero. `filas_importacion()` genera cada operación |
| `scripts/indices.py` | El índice de Törnqvist, con y sin informe de cobertura. Sin dependencias ni efectos |

## Para qué sirve más allá de esta tesis

- **Medir el efecto de una política comercial argentina** que alcanzó a casi todo un universo
  de mercaderías y se eliminó por completo quince meses después.
- **Reutilizar el pipeline del INDEC**: descarga verificada por SHA-256, lectura del microdato
  de comercio exterior y construcción de panel, aplicable a cualquier posición arancelaria.
- **Partir de una implementación de índices superlativos** en Python puro, con pruebas de sus
  propiedades.

El material se produjo para el trabajo final de investigación en Economía **«Apertura
importadora y bienes de capital en la Argentina, 2021–2026: régimen regulatorio, precios,
cantidades y variedad de las importaciones»** (Universidad de Belgrano), y los programas
también verifican las cifras que ese trabajo publica.

## Requisitos

Para reproducir los resultados, **Python 3.8 o posterior y nada más**. Viene de fábrica en Linux
y macOS y se baja de python.org en Windows. Los programas usan solamente la biblioteca estándar:
no hay pandas, ni numpy, ni paquetes de terceros de ningún tipo.

**Rehacer el OCR de los anexos es lo único que pide software del sistema: `tesseract`**, o Docker,
que sirve igual. Queda fuera de la cadena y no hace falta para reproducir ninguna cifra, porque la
transcripción viaja hecha y verificada por SHA-256; se documenta en
[Rehacer el OCR](#rehacer-el-ocr).

## Correrlo

```
python3 scripts/reproducir.py
```

Eso hace todo: comprueba las fuentes, reconstruye el universo de bienes de capital,
arma el panel, corre los análisis y termina imprimiendo un veredicto.

Las fuentes ya vienen en el repositorio, así que no hace falta conexión: tarda
alrededor de un minuto en una máquina corriente. Si se interrumpe, se retoma:

```
python3 scripts/reproducir.py --desde 4     # sigue desde la etapa 4
python3 scripts/reproducir.py --listar      # muestra las nueve etapas
```

## Qué tiene que dar

La última etapa contrasta cincuenta y nueve cifras del trabajo contra lo que acaba de
calcular, de la introducción a las conclusiones, y termina así:

```
Todo lo verificado coincide con lo publicado en el trabajo.
```

Si alguna línea da `✗`, el programa lo dice con nombre y apellido: qué concepto,
qué dice la tesis y qué dio el recálculo.

**La columna «en la tesis» de ese cuadro son constantes escritas a mano en
`scripts/verificar.py`, copiadas del texto publicado.** Lo que se contrasta es el
texto contra el dato, no el dato contra sí mismo.

Además del valor, se comprueba la **forma** del resultado principal del capítulo 7
(sólo la diferenciación del producto alcanza su máximo en el último tramo), que
podría romperse sin que ninguna cifra se moviera mucho.

Un quinto bloque cierra el círculo del otro lado: busca cada una de esas cifras,
escrita tal cual, en el capítulo que la publica. Necesita el texto de la tesis, que
no forma parte de este repositorio, así que acá se saltea con un aviso.

## De dónde salen los datos

Son 154 archivos de dos organismos (58 MB), y **viajan en el repositorio en la edición
exacta que usó el trabajo**. `datos/FUENTES.json` registra de cada uno la URL de origen
y su SHA-256, que fija la **edición** y no solo el nombre. La primera etapa los
comprueba contra ese manifiesto y **baja de los organismos sólo lo que falte**, por
ejemplo si se borró un archivo:

| Fuente | Qué es |
|---|---|
| INDEC, base de comercio exterior | Seis archivos: importaciones 2021–2026, por posición, mes y país de origen |
| Arancel Externo Común (Anexo I) | El nomenclador, de donde sale la marca que define qué es un bien de capital |
| Res. SC 1/2022 y 26/2022, Anexo II | Las 147 páginas en imagen con las posiciones alcanzadas por licencias |

### Por qué las fuentes viajan en el repositorio

El INDEC **reescribe el archivo del año en curso** a medida que cierra meses, y al
hacerlo **corrige también meses anteriores**. Los programas fijan una ventana
temporal (`VENTANA_HASTA = "2026-06"`, en `scripts/indec.py`) que descarta lo
posterior, pero no esas correcciones. Medido el 2026-09-28: con la edición de 2026
que publica hoy el INDEC, dos cifras del trabajo se mueven en el último decimal (la
deriva de encadenamiento mensual, de 21,8 a 21,7, y la razón de cantidades de la
dimensión D2 en el último tramo, de 122,8 a 122,6).

La edición que usó el trabajo ya no está en el sitio del organismo: la copia de este
repositorio es la que permite reproducir exacto. Si alguien baja la edición nueva, la
etapa 1 lo avisa en ámbar y `verificar.py` dice qué cifra se movió; para volver a la
del trabajo alcanza con `git checkout -- datos/`.

## Lo que viaja dentro del paquete

Cinco archivos no se pueden volver a derivar con solo Python, así que se
incluyen, con su SHA-256 en `datos/CONGELADOS.sha256`. `reproducir.py` los
comprueba antes de arrancar.

| Archivo | Por qué está congelado |
|---|---|
| `datos/lna_agosto2022_ocr.txt` · `lna_octubre2022_ocr.txt` | Transcripción por OCR de los anexos. Se entrega hecha para que la cadena no dependa de tener tesseract instalado |
| `datos/lna-transcripcion/lna_ch84_90.txt` | Transcripción manual de 2.261 posiciones, leyendo las imágenes. Es el patrón contra el que `auditar_ocr.py` mide la precisión del OCR |
| `datos/ncm_aec2017_layout.txt` | Texto del arancel, extraído con `pdftotext -layout`. Evita depender de poppler |
| `datos/referencia/paises_indec.csv` | Tabla de códigos de país del INDEC |

### Rehacer el OCR

La transcripción se puede volver a hacer sobre las mismas imágenes:

```
python3 scripts/ocr_anexo.py datos/anexo2-lna-res1-2022-agosto  /tmp/agosto.txt
python3 scripts/ocr_anexo.py datos/anexo2-lna-res26-2022        /tmp/octubre.txt
```

**Comprobado: reproduce exactamente las listas congeladas.** La corrida sobre el
anexo de agosto de 2022 devolvió las mismas 1.492 posiciones, sin una sola
diferencia. Hay que correrlo **sin** el tercer argumento: los archivos congelados
son la transcripción cruda, y el filtrado contra el nomenclador lo hace después
`construir_universo.py`.

Lo único que hace falta es el programa `tesseract`, o Docker, que sirve igual. El
programa no lo instala por su cuenta, y es deliberado: instalar software en la
máquina de otro pide permisos de administrador y depende del sistema operativo.
Si falta, imprime el comando exacto para el sistema donde está corriendo.

**Sin OCR también se puede auditar la transcripción**, y eso corre en la cadena
principal: `verificar.py` contrasta cada código transcripto contra el nomenclador
oficial descargado y reporta que 2.239 de los 2.261 códigos de los capítulos 84 a
90 existen literalmente en el arancel. Los 22 restantes son desdoblamientos de la
VII Enmienda (NCM 2022), posterior al arancel de 2017 que sirve de padrón.

## Las nueve etapas

| | Programa | Qué hace |
|---|---|---|
| 1 | `descargar_fuentes.py` | Verifica las fuentes primarias por SHA-256 y baja de los organismos las que falten |
| 2 | `construir_universo.py` | Delimita los bienes de capital y sus tres trayectorias regulatorias |
| 3 | `descripciones_ncm.py` | Extrae del arancel la descripción y el arancel de cada posición |
| 4 | `cobertura_valor.py` | Mide qué fracción del valor importado alcanzaba cada listado |
| 5 | `construir_panel.py` | Arma el panel posición-mes y las series agregadas |
| 6 | `origenes.py` | Compone la participación por país de origen |
| 7 | `analisis_grupos.py` | Compara las trayectorias regulatorias y sus robusteces |
| 8 | `analisis_heterogeneidad.py` | Contrasta las cuatro dimensiones de heterogeneidad |
| 9 | `verificar.py` | Contrasta todo lo anterior contra las cifras publicadas |

Cada programa abre con una explicación de qué hace y por qué se decidió así, y
los comentarios del código anotan las decisiones metodológicas, no la sintaxis.

### Cuatro programas más, fuera de la cadena

No hacen falta para reproducir los resultados: existen para auditarlos o para componer el texto.

| Programa | Qué comprueba |
|---|---|
| `auditar_ocr.py` | La concordancia entre las dos transcripciones del anexo, hechas por procedimientos de lectura distintos. **De acá sale la cifra de discrepancia que reporta el trabajo**, no de un número anotado. Con `--rehacer` vuelve a pasar el OCR |
| `probar_indices.py` | Que el índice de Törnqvist esté bien implementado, verificando siete propiedades que la fórmula debe cumplir por construcción: identidad, proporcionalidad, reversión temporal y otras. Corre sobre los datos reales y usa la misma función que produce los resultados publicados |
| `ocr_anexo.py` | Rehace la transcripción desde las imágenes. Lo único que necesita instalado |
| `generar_anexos.py` | Los cuadros de los anexos del trabajo, en Markdown, desde los resultados de la cadena. En el repositorio los deja en `salida/anexos.md` |

## Comprobación automática

Dos flujos de GitHub Actions corren los mismos programas en una máquina limpia:

| Flujo | Cuándo | Qué comprueba |
|---|---|---|
| `regimen` | En cada cambio | Que todo compile con Python 3.8 y 3.12, que el lector del INDEC rechace formatos inesperados y que los dos CSV del régimen se regeneren **byte a byte** a partir de los insumos del repositorio |
| `reproduccion` | A mano y una vez por mes | La cadena entera, con las fuentes del repositorio, hasta el veredicto de `verificar.py`, más las propiedades del índice. Y aparte, que cada una de las 154 fuentes siga publicada en su URL oficial: si un organismo la retira, se ve acá |

## Dónde quedan los resultados

En `datos/`. Los principales son `cobertura_por_valor.json` (qué fracción del valor
importado alcanzaba cada listado, capítulo 3), `panel_bk_ncm_mes.csv` (el panel, una fila por
posición y mes), `series_agregadas.json` y `series_por_grupo.json` (las series y
los números índice) y `robustez_grupos.json` y `analisis_heterogeneidad.json`
(los contrastes de los capítulos 6 y 7).

## Cómo citar

Si usás la reconstrucción del régimen o el panel en un trabajo propio, se agradece la cita.
El repositorio trae `CITATION.cff`, así que el botón **Cite this repository** de GitHub la
da en APA y en BibTeX:

> Soler, R. (2026). *Licencias no automáticas de importación en la Argentina a nivel de posición
> arancelaria, 2021–2026: reconstrucción y panel de importaciones* [Software y datos].
> https://github.com/Ramillax/licencias-no-automaticas-argentina

## Contacto

Para preguntas sobre los datos o el procedimiento, lo más práctico es abrir una **issue** en
este repositorio, así la respuesta queda disponible para quien tenga la misma duda.

Para lo demás: **ramirosoler48@gmail.com**

## Licencia

MIT para el código (ver `LICENSE`). **No cubre las fuentes primarias** de `datos/`, que son
publicaciones oficiales de acceso público del INDEC y del Boletín Oficial de la República
Argentina. Se incluyen sin modificar, sólo para que el trabajo se pueda reproducir con la
edición exacta que usó; cada una conserva sus propias condiciones de uso y su procedencia
queda registrada en `datos/FUENTES.json`.
