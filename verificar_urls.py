"""
verificar_urls.py
-----------------
Lee las URLs del archivo 'urls 1.csv', las limpia y verifica
si cada una responde correctamente (HTTP < 400).

Uso:
    python verificar_urls.py

Resultado:
    - Imprime resumen en consola
    - Guarda 'resultado_urls.csv' con el estado de cada URL

Requisitos:
    pip install requests
"""

import re
import csv
import os
import concurrent.futures
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: Falta la librería 'requests'. Ejecutá: pip install requests")
    exit(1)

# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
CSV_INPUT   = "urls 1.csv"    # Archivo de entrada
CSV_OUTPUT  = "resultado_urls.csv"  # Archivo de salida
MAX_WORKERS = 15              # Conexiones simultáneas
TIMEOUT     = 12              # Segundos por URL


# ──────────────────────────────────────────────
# Funciones
# ──────────────────────────────────────────────
def leer_urls(filepath):
    urls = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            url = parts[1] if len(parts) == 2 else parts[0]
            url = url.strip().strip('"')
            if url:
                urls.append(url)
    return urls


def limpiar_url(url):
    """Elimina puntuación trailing que no forma parte de la URL."""
    return url.rstrip(".,)")


def verificar_url(item):
    idx, raw_url = item
    cleaned = limpiar_url(raw_url)

    # Validación de formato básica
    if "..." in cleaned:
        return idx, raw_url, cleaned, "INVÁLIDA", "Contiene puntos suspensivos (...)"
    if "*" in cleaned:
        return idx, raw_url, cleaned, "INVÁLIDA", "Contiene asterisco (*)"

    try:
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.netloc:
            return idx, raw_url, cleaned, "INVÁLIDA", "Sin esquema o dominio"
    except Exception:
        return idx, raw_url, cleaned, "INVÁLIDA", "Error al parsear la URL"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.head(
            cleaned, timeout=TIMEOUT, allow_redirects=True, headers=headers
        )
        code = resp.status_code
        if code == 405:  # HEAD no permitido → probar GET
            resp = requests.get(
                cleaned, timeout=TIMEOUT, allow_redirects=True,
                headers=headers, stream=True
            )
            code = resp.status_code

        if code < 400:
            return idx, raw_url, cleaned, "VÁLIDA", f"HTTP {code}"
        elif code == 404:
            return idx, raw_url, cleaned, "NO ENCONTRADA", "HTTP 404"
        elif code == 403:
            return idx, raw_url, cleaned, "ACCESO DENEGADO", "HTTP 403"
        else:
            return idx, raw_url, cleaned, "ERROR HTTP", f"HTTP {code}"

    except requests.exceptions.SSLError:
        return idx, raw_url, cleaned, "ERROR SSL", "Certificado SSL inválido"
    except requests.exceptions.ConnectionError:
        return idx, raw_url, cleaned, "SIN CONEXIÓN", "No se pudo conectar al servidor"
    except requests.exceptions.Timeout:
        return idx, raw_url, cleaned, "TIMEOUT", f"Sin respuesta en {TIMEOUT}s"
    except Exception as e:
        return idx, raw_url, cleaned, "ERROR", str(e)[:100]


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    if not os.path.exists(CSV_INPUT):
        print(f"ERROR: No se encontró el archivo '{CSV_INPUT}'")
        print(f"  Asegurate de que el archivo esté en la misma carpeta que este script.")
        exit(1)

    urls = leer_urls(CSV_INPUT)
    total = len(urls)
    print(f"\n{'='*60}")
    print(f"  Verificador de URLs")
    print(f"{'='*60}")
    print(f"  Archivo: {CSV_INPUT}")
    print(f"  Total URLs: {total}")
    print(f"  Conexiones simultáneas: {MAX_WORKERS}")
    print(f"  Timeout por URL: {TIMEOUT}s")
    print(f"{'='*60}\n")

    items = list(enumerate(urls, 1))
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verificar_url, item): item for item in items}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            idx, _, cleaned, estado, detalle = result
            icon = "✅" if estado == "VÁLIDA" else "❌"
            print(f"  {icon} [{idx:3d}/{total}] {estado:<18} {cleaned[:70]}")

    results.sort(key=lambda x: x[0])

    # Guardar CSV
    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["#", "URL Original", "URL Limpiada", "Estado", "Detalle"])
        for r in results:
            writer.writerow(list(r))

    # Resumen final
    validas       = [r for r in results if r[3] == "VÁLIDA"]
    no_encontradas = [r for r in results if r[3] == "NO ENCONTRADA"]
    invalidas     = [r for r in results if r[3] == "INVÁLIDA"]
    otros         = [r for r in results if r[3] not in ("VÁLIDA", "NO ENCONTRADA", "INVÁLIDA")]

    print(f"\n{'='*60}")
    print(f"  RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"  ✅ VÁLIDAS        : {len(validas)}")
    print(f"  ❌ NO ENCONTRADAS : {len(no_encontradas)}")
    print(f"  🚫 INVÁLIDAS      : {len(invalidas)}")
    print(f"  ⚠️  OTROS ERRORES : {len(otros)}")
    print(f"  {'─'*40}")
    print(f"  TOTAL             : {total}")
    print(f"{'='*60}")
    print(f"\n  Resultado guardado en: {CSV_OUTPUT}\n")

    if validas:
        print("✅ URLs VÁLIDAS:")
        for r in validas:
            print(f"   [{r[0]:3d}] {r[2]}")

    if no_encontradas:
        print("\n❌ NO ENCONTRADAS (404):")
        for r in no_encontradas:
            print(f"   [{r[0]:3d}] {r[2]}")

    if invalidas:
        print("\n🚫 FORMATO INVÁLIDO:")
        for r in invalidas:
            print(f"   [{r[0]:3d}] {r[2]}  →  {r[4]}")

    if otros:
        print("\n⚠️  OTROS ERRORES:")
        for r in otros:
            print(f"   [{r[0]:3d}] {r[3]}: {r[2]}")
            print(f"         {r[4]}")


if __name__ == "__main__":
    main()
