#!/usr/bin/env python3
"""
Capítulo 3, sección 3.5: qué fracción del valor importado alcanzaba cada listado.

    python3 scripts/cobertura_valor.py

Para cada mes de la ventana calcula la participación en el valor FOB importado
de las posiciones incluidas en el listado de agosto de 2022 (Res. SC 1/2022) y en
el de octubre de 2022 (Res. SC 26/2022), sobre el total de bienes importados y
sobre el universo de bienes de capital.

Los listados se aplican FIJOS a los 66 meses. Por eso la variación entre meses es
de composición del comercio y no del régimen, y para los meses anteriores a agosto
de 2022 el resultado es la aplicación retrospectiva de un listado posterior (ver
3.8), útil para comparar composición pero no como descripción del régimen vigente.

El promedio del período se pondera por valor: es la participación del valor
alcanzado en el valor total de los 66 meses. Un promedio simple de los meses
daría el mismo peso a un mes chico que a uno grande.

Salida: datos/cobertura_por_valor.json. La lee generar_anexos.py (Anexo A) y la
controla verificar.py.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indec import filas_importacion    # lector del microdato y ventana, ver indec.py

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
TRANS = DATOS / "lna-transcripcion"
SALIDA = DATOS / "cobertura_por_valor.json"


def lista(path):
    """Códigos NCM de un listado, normalizados a ocho dígitos sin puntos."""
    return {c.replace(".", "") for c in path.read_text().split()
            if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", c)}


def pct(parte, total):
    return round(100 * parte / total, 2) if total else 0.0


def main():
    bk = (lista(TRANS / "bk_ruta_a_control.txt") | lista(TRANS / "bk_ruta_a_tratadas.txt")
          | lista(TRANS / "bk_ruta_a_nunca.txt"))
    ago = lista(DATOS / "lna_agosto2022_ocr.txt")
    oct_ = lista(DATOS / "lna_octubre2022_ocr.txt")

    # mes -> [total, total en ago, total en oct, bk, bk en ago, bk en oct]
    m = defaultdict(lambda: [0.0] * 6)
    for ncm, mes, _origen, fob, _kg in filas_importacion():
        r = m[mes]
        r[0] += fob
        r[1] += fob if ncm in ago else 0.0
        r[2] += fob if ncm in oct_ else 0.0
        if ncm in bk:
            r[3] += fob
            r[4] += fob if ncm in ago else 0.0
            r[5] += fob if ncm in oct_ else 0.0

    mensual = [{"periodo": mes,
                "cob_todos_ago": pct(r[1], r[0]), "cob_todos_oct": pct(r[2], r[0]),
                "cob_bk_ago": pct(r[4], r[3]), "cob_bk_oct": pct(r[5], r[3]),
                "fob_total": round(r[0], 2), "fob_bk": round(r[3], 2)}
               for mes, r in sorted(m.items())]

    s = [sum(r[i] for r in m.values()) for i in range(6)]
    periodo = {"meses": len(m),
               "cob_todos_ago": pct(s[1], s[0]), "cob_todos_oct": pct(s[2], s[0]),
               "cob_bk_ago": pct(s[4], s[3]), "cob_bk_oct": pct(s[5], s[3]),
               "fob_total": round(s[0], 2), "fob_bk": round(s[3], 2)}

    SALIDA.write_text(json.dumps({"periodo": periodo, "mensual": mensual},
                                 ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{'':<34}{'listado ago-22':>16}{'listado oct-22':>16}")
    print(f"{'sobre el total importado':<34}{periodo['cob_todos_ago']:>15.1f}%"
          f"{periodo['cob_todos_oct']:>15.1f}%")
    print(f"{'sobre bienes de capital':<34}{periodo['cob_bk_ago']:>15.1f}%"
          f"{periodo['cob_bk_oct']:>15.1f}%")
    print(f"\n{periodo['meses']} meses, ponderado por valor. Escrito {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
