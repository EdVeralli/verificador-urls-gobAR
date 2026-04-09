# Verificador de URLs — Buenos Aires GOB.AR

Herramienta para analizar y verificar si una lista de URLs están activas.

## Archivos

| Archivo | Descripción |
|---|---|
| `verificar_urls.py` | Script Python que verifica el estado HTTP de cada URL |
| `verificar_urls.xlsx` | Análisis de formato de las 173 URLs (coloreado por estado) |
| `urls_originales.csv` | CSV original con las 173 URLs |
| `resultado_urls.csv` | Resultado de la verificación online *(se genera al correr el script)* |

## Uso rápido

```bash
# 1. Instalar dependencias
pip install requests

# 2. Asegurarse que 'urls 1.csv' o 'urls_originales.csv' esté en la misma carpeta

# 3. Correr el verificador
python verificar_urls.py
```

El script genera `resultado_urls.csv` con el estado de cada URL:

| Estado | Significado |
|---|---|
| `VÁLIDA` | La URL responde correctamente (HTTP 2xx/3xx) |
| `NO ENCONTRADA` | HTTP 404 — la página no existe |
| `ACCESO DENEGADO` | HTTP 403 — el servidor bloquea el acceso |
| `SIN CONEXIÓN` | El servidor no responde |
| `TIMEOUT` | La URL tardó más de 12 segundos |
| `INVÁLIDA` | Formato de URL inválido (contiene `...` o `*`) |
| `ERROR SSL` | Problema con el certificado HTTPS |

## Hallazgos del análisis de formato

- **173 URLs** en el archivo original
- **164 URLs únicas** (9 duplicadas)
- **Varios URLs** tienen puntuación al final (`. , )`) copiada del texto — el script las limpia automáticamente
- **2 URLs** son claramente inválidas de formato:
  - `https://login.buenosaires.gob.ar/...` (puntos suspensivos)
  - `https://tramitesdigitales.buenosaires.gob.ar/authentication*,` (asterisco)

## Configuración del script

Podés ajustar estas variables al principio de `verificar_urls.py`:

```python
CSV_INPUT   = "urls 1.csv"    # Nombre del archivo CSV de entrada
CSV_OUTPUT  = "resultado_urls.csv"  # Nombre del archivo de salida
MAX_WORKERS = 15              # Cantidad de conexiones simultáneas
TIMEOUT     = 12              # Segundos de espera por URL
```
