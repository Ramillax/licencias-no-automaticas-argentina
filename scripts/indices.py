#!/usr/bin/env python3
"""
El número índice del trabajo, en un solo lugar.

Hasta el 2026-09-25 esta función estaba copiada en tres programas. Idénticas,
pero copiadas: quien auditara tenía que leer las tres para confirmar que decían
lo mismo, y cualquier corrección había que aplicarla por triplicado. Acá está una
sola vez, y es la que `probar_indices.py` verifica.

No tiene dependencias ni efectos: se puede importar desde cualquier lado.

    from indices import tornqvist, tornqvist_con_cobertura
    tornqvist({"8429.51.99": [fob0, kg0]}, {"8429.51.99": [fob1, kg1]})
"""

import math


def tornqvist(a, b):
    """Índice de precios de Törnqvist entre dos períodos, base fija.

    `a` y `b` son diccionarios {clave de celda: [valor, cantidad física]} del
    período base y del período comparado. La clave define qué se considera «el
    mismo producto»: en este trabajo, la posición arancelaria, o la posición y
    el país de origen. Devuelve el relativo de precio (1,0 = sin cambio), o None
    si no hay ninguna celda comparable.

    Es un índice superlativo en el sentido de Diewert (1976): la media geométrica
    ponderada de las variaciones de precio de cada celda, con peso igual al
    PROMEDIO de su participación en el valor de los dos períodos. Se elige frente
    a Laspeyres o Paasche porque no fija la canasta en ninguno de los dos
    extremos, lo que importa en un período de recomposición pronunciada.

    El precio de una celda es su valor unitario, valor dividido cantidad. Sólo
    entran las celdas presentes en AMBOS períodos con cantidad positiva: una
    posición que no se importó en el período base no tiene variación de precio
    que medir. Eso deja la aparición y desaparición de posiciones fuera del
    índice de precios, y es justamente lo que el trabajo mide aparte, como margen
    extensivo.

    Las participaciones se calculan sobre las celdas apareadas y no sobre el
    universo entero, que es lo que hace que los pesos sumen 1. Si se calcularan
    sobre el total, el índice quedaría subponderado en proporción a lo que no
    aparea, sin que nada avisara.
    """
    comunes = [k for k in a if k in b and a[k][1] > 0 and b[k][1] > 0]
    if not comunes:
        return None
    v0 = sum(a[k][0] for k in comunes)
    v1 = sum(b[k][0] for k in comunes)
    log = sum(0.5 * (a[k][0] / v0 + b[k][0] / v1)
              * math.log((b[k][0] / b[k][1]) / (a[k][0] / a[k][1])) for k in comunes)
    return math.exp(log)


def tornqvist_con_cobertura(a, b):
    """Como `tornqvist`, pero informando además cuánto del período b quedó apareado.

    Devuelve (relativo, celdas apareadas, participación del valor apareado sobre
    el valor total de b). La cobertura importa para juzgar el índice: un relativo
    calculado sobre el 60 % del comercio dice menos que uno calculado sobre el
    98 %, y el panel la publica junto a cada número para que se pueda ver.
    """
    comunes = [k for k in a if k in b and a[k][1] > 0 and b[k][1] > 0]
    if not comunes:
        return None, 0, 0.0
    rel = tornqvist(a, b)
    v1 = sum(b[k][0] for k in comunes)
    total_b = sum(v[0] for v in b.values())
    return rel, len(comunes), (v1 / total_b if total_b else 0.0)
