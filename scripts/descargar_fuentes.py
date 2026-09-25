#!/usr/bin/env python3
"""
Descarga las fuentes primarias del trabajo desde los organismos de origen y las
verifica una por una contra `datos/FUENTES.json`.

Son 154 archivos y 59 MB: las seis bases de importación del INDEC, el PDF
del Arancel Externo Común y las 147 páginas en imagen de los dos anexos de
licencias no automáticas. Con eso, y solamente con eso, la cadena entera se
reconstruye desde cero: nada de lo que produce el trabajo hace falta bajarlo.

El manifiesto lleva el SHA-256 de cada archivo tal como se usó en el trabajo, así
que quien reciba esto puede comprobar que descargó exactamente lo mismo y no una
versión posterior del mismo enlace.

Uso   python3 descargar_fuentes.py              baja lo que falte y verifica todo
      python3 descargar_fuentes.py --verificar  no toca la red, solo comprueba
      python3 descargar_fuentes.py --forzar     vuelve a bajar aunque ya estén

Después de bajar:  python3 scripts/verificar.py

Las series macroeconómicas del capítulo 8 son un bloque aparte, con sus propias
APIs:  python3 scripts/descargar_macro.py
"""

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MANIFIESTO = RAIZ / "datos" / "FUENTES.json"
INDEC = RAIZ / "datos" / "indec"
INTENTOS = 3
UA = "Mozilla/5.0 (X11; Linux x86_64) tesis-bienes-de-capital/1.0"

VERDE, ROJO, AMBAR, GRIS, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"
TERMINAL = sys.stdout.isatty()
if not TERMINAL:
    VERDE = ROJO = AMBAR = GRIS = FIN = ""


def sha256(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            d.update(bloque)
    return d.hexdigest()


def bajar(url, destino):
    """Descarga a un temporal y recién entonces renombra, para no dejar archivos a medias.

    Importa porque el programa es reanudable: decide qué bajar mirando qué hay en
    disco. Si una descarga cortada dejara el archivo truncado en su lugar
    definitivo, la corrida siguiente lo daría por presente y la cadena seguiría
    con datos incompletos. Escribir en `.parcial` y renombrar al final hace que un
    archivo sólo exista cuando está entero: el renombrado es atómico.

    Tres intentos, porque el servidor del INDEC corta conexiones con cierta
    frecuencia y un reintento resuelve casi siempre.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".parcial")
    ultimo = None
    for intento in range(1, INTENTOS + 1):
        try:
            pedido = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(pedido, timeout=300) as r, open(tmp, "wb") as f:
                while True:
                    bloque = r.read(1 << 20)
                    if not bloque:
                        break
                    f.write(bloque)
            tmp.replace(destino)
            return None
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            ultimo = e
            if intento == INTENTOS:
                break
    tmp.unlink(missing_ok=True)
    return ultimo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verificar", action="store_true", help="no descarga, solo comprueba lo que hay")
    ap.add_argument("--forzar", action="store_true", help="vuelve a descargar aunque el archivo esté")
    args = ap.parse_args()

    if not MANIFIESTO.exists():
        sys.exit(f"falta el manifiesto {MANIFIESTO}")
    manifiesto = json.loads(MANIFIESTO.read_text())["archivos"]

    # Se agrupa por organismo para que la salida se lea como un inventario de
    # procedencia y no como una lista de 154 archivos: quien audita quiere ver de
    # qué fuente oficial viene cada bloque, no los nombres uno por uno.
    porfuente = {}
    for rel, meta in manifiesto.items():
        porfuente.setdefault(meta["fuente"], []).append((rel, meta))

    print("FUENTES PRIMARIAS DEL TRABAJO")
    print(f"proyecto: {RAIZ}")
    if args.verificar:
        print(f"{GRIS}modo verificación: no se toca la red{FIN}")

    ok = bajados = faltan = corruptos = republicados = 0
    bytes_bajados = 0

    for fuente, archivos in porfuente.items():
        print(f"\n{fuente}  {GRIS}({len(archivos)} archivo(s)){FIN}")
        # Con muchos archivos sólo se listan los que dan problema, pero hay que
        # mostrar SIEMPRE que el programa avanza: las 147 imágenes de los anexos
        # tardan varios minutos y sin señal de vida parece colgado.
        muchos = len(archivos) > 13
        for i, (rel, meta) in enumerate(sorted(archivos), 1):
            if muchos:
                # En una terminal, una sola línea que se pisa a sí misma. Cuando
                # la salida va a un archivo el retorno de carro no sirve, así que
                # se marca el avance cada 25 archivos y no se inunda el registro.
                if TERMINAL:
                    print(f"  {GRIS}··  {i}/{len(archivos)}  {Path(rel).name:<28}{FIN}",
                          end="\r", flush=True)
                elif i % 25 == 0 or i == len(archivos):
                    print(f"  ··  {i}/{len(archivos)}", flush=True)
            destino = RAIZ / rel
            etiqueta = Path(rel).name
            presente = destino.exists() and destino.stat().st_size > 0

            if presente and not args.forzar:
                if sha256(destino) == meta["sha256"]:
                    ok += 1
                    if len(archivos) <= 13:
                        print(f"  {VERDE}ok{FIN}  {etiqueta:<28} {meta['bytes']/1e6:>7,.1f} MB  {GRIS}ya estaba{FIN}")
                    continue
                print(f"  {AMBAR}~ {FIN} {etiqueta:<28} {GRIS}en disco, pero es otra edición "
                      f"que la del manifiesto{FIN}")
                republicados += 1
                continue
            elif args.verificar:
                print(f"  {AMBAR}—{FIN}  {etiqueta:<28} {GRIS}falta{FIN}")
                faltan += 1
                continue

            print(f"  {GRIS}··{FIN}  {etiqueta:<28} {meta['bytes']/1e6:>7,.1f} MB  bajando…", end="\r")
            error = bajar(meta["url"], destino)
            if error:
                print(f"  {ROJO}✗ {FIN} {etiqueta:<28} {GRIS}{error}{FIN}")
                faltan += 1
                continue
            real = sha256(destino)
            if real != meta["sha256"]:
                # No es un error: el INDEC republica el archivo del año en curso a
                # medida que cierra meses. La ventana temporal de construir_panel.py
                # neutraliza el agregado; verificar.py dice qué cifra se mueve.
                print(f"  {AMBAR}~ {FIN} {etiqueta:<28} {meta['bytes']/1e6:>7,.1f} MB  "
                      f"{GRIS}bajó: el organismo republicó este archivo{FIN}")
                republicados += 1
                continue
            bajados += 1
            bytes_bajados += destino.stat().st_size
            print(f"  {VERDE}ok{FIN}  {etiqueta:<28} {meta['bytes']/1e6:>7,.1f} MB  {GRIS}descargado y verificado{FIN}")

        if muchos:
            print(f"  {GRIS}{len(archivos)} archivos verificados"
                  f"{'' if args.verificar else ' o descargados'}: "
                  f"se listan sólo los que dieron problema{' ' * 20}{FIN}")

    print()
    total = len(manifiesto)
    print(f"  verificados contra el manifiesto : {ok + bajados} de {total}")
    if bajados:
        print(f"  descargados en esta corrida      : {bajados}  ({bytes_bajados/1e6:,.1f} MB)")
    if republicados:
        print(f"  {AMBAR}republicados por el organismo    : {republicados}{FIN}")
    if faltan:
        print(f"  {ROJO}faltan                           : {faltan}{FIN}")
    if corruptos:
        print(f"  {ROJO}no coinciden con el manifiesto   : {corruptos}{FIN}")

    print()
    if faltan or corruptos:
        print(f"{ROJO}Faltan fuentes: la cadena no se puede reconstruir completa.{FIN}")
        return 1
    if republicados:
        print(f"{AMBAR}Están las {total} fuentes. {republicados} ya no son la edición que usó el "
              f"trabajo:{FIN}")
        print(f"{GRIS}  el INDEC reescribe el archivo del año en curso a medida que cierra meses.")
        print("  La ventana temporal del panel (VENTANA_HASTA) descarta lo posterior a junio de")
        print(f"  2026, así que la cadena reproduce igual. verificar.py dice qué cifra se mueve.{FIN}")
        return 0
    print(f"{VERDE}Están las {total} fuentes primarias y todas coinciden con el manifiesto.{FIN}")
    print(f"{GRIS}Siguiente paso:  python3 {Path('scripts/verificar.py')}{FIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
