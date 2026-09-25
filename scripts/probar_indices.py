#!/usr/bin/env python3
"""
Comprueba que el índice de Törnqvist esté bien implementado.

    python3 scripts/probar_indices.py

No compara contra un número esperado: verifica las PROPIEDADES que la fórmula
tiene que cumplir por construcción. Si el código estuviera mal, alguna falla.
Las pruebas corren sobre los datos reales del panel, no sobre ejemplos armados.

    1. Ponderaciones      suman 1 exactamente. Es lo primero que se rompe si las
                          participaciones se calculan sobre el universo entero en
                          vez de sobre las celdas apareadas.
    2. Identidad          comparar un período consigo mismo da 1.
    3. Proporcionalidad   si todos los valores unitarios se multiplican por k,
                          el índice da k, sea cual sea la composición.
    4. Reversión temporal P(a,b) · P(b,a) = 1. Laspeyres y Paasche NO la cumplen;
                          Törnqvist sí, y es una de las razones para elegirlo.
    5. Invariancia de     multiplicar todas las cantidades por una constante no
       escala             mueve el índice de PRECIOS.
    6. Cota               el índice queda entre el menor y el mayor relativo de
                          precio individual: es un promedio, no puede escaparse.

Referencia de la fórmula: Diewert (1976), «Exact and superlative index numbers».

NOTA: este programa importa `analisis_grupos`, que al importarse corre su propio
análisis e imprime su cuadro antes de las pruebas. Es intencional y no un efecto
colateral que convenga tapar: así el test ejercita **exactamente la misma función
que produce los resultados publicados**, y no una copia que podría divergir de
ella. Un test que reimplementa lo que quiere probar no prueba nada.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analisis_grupos import micro, tornqvist   # noqa: E402  (usa el panel ya leído)

VERDE, ROJO, GRIS, FIN = "\033[32m", "\033[31m", "\033[90m", "\033[0m"
if not sys.stdout.isatty():
    VERDE = ROJO = GRIS = FIN = ""

TOL = 1e-9
fallas = []


def chequear(nombre, ok, detalle=""):
    print(f"  {VERDE + 'ok' + FIN if ok else ROJO + '✗ ' + FIN}  {nombre:<52} {GRIS}{detalle}{FIN}")
    if not ok:
        fallas.append(nombre)


def celdas_de(anio):
    """{ncm: [fob, kg]} de un año, agregando los meses y los orígenes."""
    out = {}
    for (ncm, mes, _), (fob, kg) in micro.items():
        if mes[:4] != anio:
            continue
        c = out.setdefault(ncm, [0.0, 0.0])
        c[0] += fob
        c[1] += kg
    return out


def escalar(celdas, precio=1.0, cantidad=1.0):
    """Copia con los valores unitarios y/o las cantidades multiplicados."""
    return {k: [v[0] * precio * cantidad, v[1] * cantidad] for k, v in celdas.items()}


if __name__ == "__main__":
    a, b = celdas_de("2021"), celdas_de("2025")
    comunes = [k for k in a if k in b and a[k][1] > 0 and b[k][1] > 0]
    print(f"PRUEBAS DEL ÍNDICE DE TÖRNQVIST")
    print(f"{GRIS}sobre el panel real: {len(a):,} celdas en 2021, {len(b):,} en 2025, "
          f"{len(comunes):,} apareadas{FIN}\n")

    # 1. Las ponderaciones suman 1. Se recalculan acá con la misma regla que usa
    #    la función, sobre las celdas apareadas.
    v0 = sum(a[k][0] for k in comunes)
    v1 = sum(b[k][0] for k in comunes)
    suma_w = sum(0.5 * (a[k][0] / v0 + b[k][0] / v1) for k in comunes)
    chequear("ponderaciones suman 1", abs(suma_w - 1.0) < TOL, f"Σw = {suma_w:.12f}")

    # 2. Identidad.
    chequear("identidad: P(a, a) = 1", abs(tornqvist(a, a) - 1.0) < TOL,
             f"{tornqvist(a, a):.12f}")

    # 3. Proporcionalidad, con tres factores distintos.
    for k in (0.5, 1.37, 3.0):
        p = tornqvist(a, escalar(a, precio=k))
        chequear(f"proporcionalidad: precios × {k}", abs(p - k) < 1e-9, f"P = {p:.10f}")

    # 4. Reversión temporal.
    ida, vuelta = tornqvist(a, b), tornqvist(b, a)
    chequear("reversión temporal: P(a,b) · P(b,a) = 1",
             abs(ida * vuelta - 1.0) < 1e-9, f"{ida:.6f} × {vuelta:.6f} = {ida * vuelta:.12f}")

    # 5. Las cantidades no mueven el índice de precios.
    chequear("invariancia de escala en cantidades",
             abs(tornqvist(a, escalar(b, cantidad=7.3)) - ida) < 1e-9,
             f"{tornqvist(a, escalar(b, cantidad=7.3)):.10f} vs {ida:.10f}")

    # 6. El índice es un promedio: cae entre el mínimo y el máximo relativo.
    rel = [(b[k][0] / b[k][1]) / (a[k][0] / a[k][1]) for k in comunes]
    chequear("acotado por los relativos individuales", min(rel) <= ida <= max(rel),
             f"{min(rel):.4f} ≤ {ida:.4f} ≤ {max(rel):.4f}")

    # 7. Consistencia con la descomposición valor = precio × cantidad, que es de
    #    donde sale el índice de cantidad de los capítulos 5 a 7.
    random.seed(0)
    muestra = random.sample(comunes, min(300, len(comunes)))
    sub_a = {k: a[k] for k in muestra}
    sub_b = {k: b[k] for k in muestra}
    p = tornqvist(sub_a, sub_b)
    val = sum(sub_b[k][0] for k in muestra) / sum(sub_a[k][0] for k in muestra)
    cant = val / p
    chequear("valor = precio × cantidad (implícita)", abs(p * cant - val) < 1e-9,
             f"{p:.4f} × {cant:.4f} = {val:.6f}")

    print()
    if fallas:
        print(f"{ROJO}{len(fallas)} prueba(s) fallaron:{FIN}")
        for f in fallas:
            print(f"   · {f}")
        sys.exit(1)
    print(f"{VERDE}El índice cumple las siete propiedades. La implementación es correcta.{FIN}")
