import os
import datetime
import requests
import pandas as pd
from sqlalchemy import create_engine

# =========================
# CONFIGURACIÓN DEL PROYECTO
# =========================

# Ruta base del proyecto (carpeta raíz kanarytour_frontur_analytics)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carpetas de datos
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

# Nombre del fichero Excel que ya has descargado (si no existe, se descargará)
RAW_FILE_NAME = "frontur_euskadi_2021_viajes.xlsx"

# Nombre del fichero CSV limpio
CLEAN_FILE_NAME = "frontur_euskadi_2021_limpio.csv"

# Base de datos SQLite
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
TABLE_NAME = "frontur_euskadi_2021"

# URL de descarga del Excel (LA MISMA que ya usaste en tu script original)
FRONTUR_EUSKADI_2021_URL = "https://opendata.euskadi.eus/contenidos/estadistica/tur_estatis_frontur_2021t/es_def/adjuntos/13261403.xlsx"


def ensure_directories():
    """Crea las carpetas data/raw y data/processed si no existen."""
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print(f"[OK] Directorios asegurados:\n - {RAW_DIR}\n - {PROCESSED_DIR}")


def download_excel_if_needed():
    """
    Descarga el Excel solo si no existe ya.
    Devuelve la ruta final del fichero.
    """
    raw_path = os.path.join(RAW_DIR, RAW_FILE_NAME)

    if os.path.exists(raw_path):
        print(f"[INFO] El fichero ya existe, no se descarga de nuevo:\n  {raw_path}")
        return raw_path

    print(f"[DESCARGA] Descargando FRONTUR Euskadi 2021 desde:\n  {FRONTUR_EUSKADI_2021_URL}")
    response = requests.get(FRONTUR_EUSKADI_2021_URL)
    response.raise_for_status()

    with open(raw_path, "wb") as f:
        f.write(response.content)

    size_kb = os.path.getsize(raw_path) / 1024
    print(f"[OK] Fichero descargado: {raw_path} ({size_kb:.1f} KB)")
    return raw_path


def inspect_excel(raw_path: str):
    """
    Lee el Excel y muestra por pantalla:
    - Número de filas y columnas
    - Nombres de columnas
    - Primeras 5 filas
    """
    print(f"[LEER] Leyendo Excel:\n  {raw_path}")
    df = pd.read_excel(raw_path)

    print("\n[INFO] Dimensiones del DataFrame:")
    print(f"  Filas: {df.shape[0]}, Columnas: {df.shape[1]}")

    print("\n[INFO] Columnas:")
    for col in df.columns:
        print(f"  - {col}")

    print("\n[INFO] Primeras 5 filas:")
    print(df.head())

    return df


def clean_and_save_csv(df: pd.DataFrame):
    """
    Limpieza básica:
    - Normaliza nombres de columnas (minúsculas, sin espacios)
    - Elimina filas completamente vacías
    - Guarda CSV limpio en data/processed
    """
    print("\n[LIMPIEZA] Normalizando nombres de columnas...")
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("ó", "o").replace("á", "a")
                  .replace("é", "e").replace("í", "i").replace("ú", "u")
                  for c in df.columns]

    print("[LIMPIEZA] Eliminando filas completamente vacías...")
    df.dropna(how="all", inplace=True)

    clean_path = os.path.join(PROCESSED_DIR, CLEAN_FILE_NAME)
    df.to_csv(clean_path, index=False, encoding="utf-8-sig")
    print(f"[OK] CSV limpio guardado en:\n  {clean_path}")
    print(f"[INFO] Filas: {df.shape[0]}, Columnas: {df.shape[1]}")
    return clean_path, df


def load_to_sqlite(df: pd.DataFrame):
    """
    Carga el DataFrame en la base de datos SQLite usando SQLAlchemy.
    - Crea/reescribe la tabla TABLE_NAME
    """
    print("\n[SQLITE] Cargando datos en SQLite...")
    engine = create_engine(f"sqlite:///{DB_PATH}")

    with engine.begin() as conn:
        df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

    print(f"[OK] Datos cargados en SQLite:\n  BD: {DB_PATH}\n  Tabla: {TABLE_NAME}")


def run_etl():
    """Orquesta todo el proceso ETL."""
    print("===== ETL FRONTUR EUSKADI 2021 (Descarga → Limpieza → CSV → SQLite) =====")

    ensure_directories()
    raw_path = download_excel_if_needed()
    df_raw = inspect_excel(raw_path)
    clean_path, df_clean = clean_and_save_csv(df_raw)
    load_to_sqlite(df_clean)

    print("\n===== ETL COMPLETADO =====")
    print(f"- Excel original: {raw_path}")
    print(f"- CSV limpio:     {clean_path}")
    print(f"- SQLite:         {DB_PATH} (tabla '{TABLE_NAME}')")


if __name__ == "__main__":
    run_etl()
