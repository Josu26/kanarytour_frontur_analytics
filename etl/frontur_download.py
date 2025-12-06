# etl/frontur_download.py

import requests
from pathlib import Path


# Carpeta data/raw relativa a este archivo
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# URL de ejemplo FRONTUR (Euskadi, viajes mensuales 2021)
# Fuente: opendata.euskadi.eus / datos.gob.es
FRONTUR_EUSKADI_2021_URL = (
    "https://opendata.euskadi.eus/contenidos/estadistica/tur_estatis_frontur_2021t/"
    "es_def/adjuntos/13261403.xlsx"
)

OUTPUT_FILE = RAW_DIR / "frontur_euskadi_2021_viajes.xlsx"


def download_frontur_file(url: str = FRONTUR_EUSKADI_2021_URL, output_path: Path = OUTPUT_FILE) -> Path:
    """
    Descarga un fichero FRONTUR desde una URL y lo guarda en data/raw.
    Devuelve la ruta al archivo descargado.
    """
    print(f"Descargando FRONTUR desde:\n  {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    output_path.write_bytes(response.content)

    size_kb = len(response.content) / 1024
    print(f"Archivo guardado en: {output_path} ({size_kb:.1f} KB)")
    return output_path


if __name__ == "__main__":
    download_frontur_file()
