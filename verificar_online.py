"""
verificar_online.py
-------------------
Lee las URLs limpias del archivo 'verificar_urls.xlsx',
verifica si cada una está online (HTTP < 400) y actualiza
la columna 'ESTADO ONLINE' en:
  - verificar_urls.xlsx  (archivo completo)
  - resumen_urls.xlsx    (resumen simple de 3 columnas)

Uso:
    python verificar_online.py

Requisitos:
    pip install requests openpyxl
"""

import os
import sys
import concurrent.futures
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: Falta 'requests'. Ejecutá: pip install requests")
    sys.exit(1)

try:
    import openpyxl
    from openpyxl.styles import PatternFill
except ImportError:
    print("ERROR: Falta 'openpyxl'. Ejecutá: pip install openpyxl")
    sys.exit(1)

# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
XLSX_COMPLETO = "verificar_urls.xlsx"
XLSX_RESUMEN  = "resumen_urls.xlsx"
MAX_WORKERS   = 15
TIMEOUT       = 12

COLOR_ONLINE   = "C6EFCE"
COLOR_OFFLINE  = "FFC7CE"
COLOR_INVALIDA = "D9D9D9"
COLOR_WARNING  = "FFEB9C"

HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}


# ──────────────────────────────────────────────
# Funciones
# ──────────────────────────────────────────────
def limpiar_url(url):
    """Elimina caracteres de puntuación trailing que no forman parte de la URL."""
    return url.rstrip(".,)*")


def es_invalida(url):
    """Devuelve mensaje si la URL tiene formato inválido DESPUÉS de limpiar."""
    if "..." in url:
        return "Contiene puntos suspensivos (...)"
    # * solo es inválido si queda en el medio (no al final, ya se limpió)
    if "*" in url:
        return "Contiene asterisco (*) en el medio de la URL"
    return None


def verificar_url(item):
    idx, url_orig, url_limp, estado_fmt = item

    # Si el estado de formato ya era INVÁLIDA por otra razón, respetar
    if estado_fmt and "INVÁLIDA" in str(estado_fmt):
        # Pero intentar re-limpiar por si el * era trailing
        url_candidata = url_limp.strip() if (url_limp and url_limp.strip() != "(sin cambios)") else (url_orig or "").strip()
        url_candidata = limpiar_url(url_candidata)
        if es_invalida(url_candidata):
            return idx, "INVÁLIDA — no se verifica", COLOR_INVALIDA
        # Si ya no es inválida tras limpiar mejor, continuar verificando
        url = url_candidata
    else:
        url = url_limp.strip() if (url_limp and url_limp.strip() != "(sin cambios)") else (url_orig or "").strip()
        url = limpiar_url(url)

    if not url:
        return idx, "SIN URL", COLOR_INVALIDA

    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return idx, "FORMATO INVÁLIDO", COLOR_INVALIDA
    except Exception:
        return idx, "FORMATO INVÁLIDO", COLOR_INVALIDA

    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True, headers=HEADERS_HTTP)
        code = resp.status_code
        if code == 405:
            resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True,
                                headers=HEADERS_HTTP, stream=True)
            code = resp.status_code

        if code < 400:
            return idx, f"✅ ONLINE (HTTP {code})", COLOR_ONLINE
        elif code == 404:
            return idx, "❌ NO ENCONTRADA (404)", COLOR_OFFLINE
        elif code == 403:
            return idx, "⚠️ ACCESO DENEGADO (403)", COLOR_WARNING
        else:
            return idx, f"❌ ERROR HTTP {code}", COLOR_OFFLINE

    except requests.exceptions.SSLError:
        return idx, "❌ ERROR SSL", COLOR_OFFLINE
    except requests.exceptions.ConnectionError:
        return idx, "❌ SIN CONEXIÓN", COLOR_OFFLINE
    except requests.exceptions.Timeout:
        return idx, "❌ TIMEOUT", COLOR_OFFLINE
    except Exception as e:
        return idx, f"❌ ERROR: {str(e)[:60]}", COLOR_OFFLINE


def leer_xlsx_completo(path):
    """Lee verificar_urls.xlsx y devuelve items + info de columnas."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active

    header_row, cols = None, {}
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row and row[0] == '#':
            header_row = row_idx
            for ci, val in enumerate(row, 1):
                if val: cols[str(val).strip()] = ci
            break

    if not header_row:
        print("ERROR: No se encontró fila de encabezados en verificar_urls.xlsx")
        sys.exit(1)

    col_num      = cols.get('#', 1)
    col_original = cols.get('URL ORIGINAL', 2)
    col_limpiada = cols.get('URL LIMPIADA', 3)
    col_formato  = cols.get('ESTADO FORMATO', 4)
    col_online   = cols.get('ESTADO ONLINE', 6)

    items, seen = [], set()
    for row_idx in range(header_row + 1, ws.max_row + 1):
        num_val = ws.cell(row=row_idx, column=col_num).value
        if num_val is None or not str(num_val).isdigit():
            continue
        num = int(num_val)
        if num in seen:
            continue
        seen.add(num)
        items.append((
            row_idx,
            ws.cell(row=row_idx, column=col_original).value,
            ws.cell(row=row_idx, column=col_limpiada).value,
            ws.cell(row=row_idx, column=col_formato).value,
        ))

    return wb, ws, items, col_num, col_online, header_row


def leer_xlsx_resumen(path):
    """Lee resumen_urls.xlsx y devuelve wb, ws."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    return wb, ws


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    for f in [XLSX_COMPLETO, XLSX_RESUMEN]:
        if not os.path.exists(f):
            print(f"ERROR: No se encontró '{f}'. Asegurate de correr desde la carpeta del proyecto.")
            sys.exit(1)

    print(f"\n{'='*65}")
    print(f"  Verificador Online de URLs — gob.ar")
    print(f"{'='*65}")

    wb_comp, ws_comp, items, col_num, col_online, header_row = leer_xlsx_completo(XLSX_COMPLETO)
    wb_res, ws_res = leer_xlsx_resumen(XLSX_RESUMEN)

    total = len(items)
    print(f"  URLs a verificar : {total}")
    print(f"  Simultáneas      : {MAX_WORKERS}")
    print(f"  Timeout          : {TIMEOUT}s")
    print(f"{'='*65}\n")

    # Verificar en paralelo
    resultados = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verificar_url, item): item for item in items}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            row_idx, estado, color = future.result()
            resultados[row_idx] = (estado, color)
            done += 1
            icon = "✅" if "ONLINE" in estado else ("⚠️" if "DENEGADO" in estado or "INVÁLIDA" in estado else "❌")
            item = next(i for i in items if i[0] == row_idx)
            url_display = (item[2] if item[2] and item[2] != "(sin cambios)" else item[1]) or ""
            print(f"  {icon} [{done:3d}/{total}] {estado:<35} {str(url_display)[:52]}")

    # ── Actualizar verificar_urls.xlsx ────────────────────────────────────
    print(f"\n  Actualizando '{XLSX_COMPLETO}'...")
    num_to_result = {}
    for item in items:
        num = int(ws_comp.cell(row=item[0], column=col_num).value)
        num_to_result[num] = resultados.get(item[0])

    for row_idx in range(header_row + 1, ws_comp.max_row + 1):
        num_val = ws_comp.cell(row=row_idx, column=col_num).value
        if num_val is None or not str(num_val).isdigit():
            continue
        num = int(num_val)
        if num not in num_to_result or not num_to_result[num]:
            continue
        estado, color = num_to_result[num]
        cell = ws_comp.cell(row=row_idx, column=col_online)
        cell.value = estado
        cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    wb_comp.save(XLSX_COMPLETO)
    print(f"  ✔ '{XLSX_COMPLETO}' actualizado.")

    # ── Actualizar resumen_urls.xlsx ──────────────────────────────────────
    print(f"  Actualizando '{XLSX_RESUMEN}'...")
    for row_idx_res in range(2, ws_res.max_row + 1):
        # El orden en resumen_urls es igual al orden del CSV (mismo índice)
        idx = row_idx_res - 1  # fila 2 = URL #1
        # Buscar resultado por posición (mismo orden que items)
        matching = [item for item in items if items.index(item) == idx - 1] if idx <= len(items) else []
        if not matching:
            continue
        item_row_idx = matching[0][0]
        if item_row_idx not in resultados:
            continue
        estado, color = resultados[item_row_idx]
        cell = ws_res.cell(row=row_idx_res, column=3)
        cell.value = estado
        cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    wb_res.save(XLSX_RESUMEN)
    print(f"  ✔ '{XLSX_RESUMEN}' actualizado.")

    # Resumen
    todos = list(resultados.values())
    online   = [r for r in todos if "ONLINE" in r[0]]
    no_enc   = [r for r in todos if "404" in r[0]]
    denegado = [r for r in todos if "403" in r[0]]
    invalida = [r for r in todos if "INVÁLIDA" in r[0] or "FORMATO" in r[0]]
    otros    = [r for r in todos if r not in online + no_enc + denegado + invalida]

    print(f"\n{'='*65}")
    print(f"  RESUMEN FINAL")
    print(f"{'='*65}")
    print(f"  ✅ ONLINE          : {len(online)}")
    print(f"  ❌ NO ENCONTRADAS  : {len(no_enc)}")
    print(f"  ⚠️  ACCESO DENEGADO: {len(denegado)}")
    print(f"  🚫 INVÁLIDAS       : {len(invalida)}")
    print(f"  ⚠️  OTROS ERRORES  : {len(otros)}")
    print(f"  {'─'*45}")
    print(f"  TOTAL              : {total}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
