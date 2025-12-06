import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

# === RUTAS BASE ===
BASE_DIR = Path(__file__).resolve().parents[1]

RAW_OBS_FILE = BASE_DIR / "data" / "raw" / "dataset-ISTAC-E16028B_000001-~latest-observations.tsv"

PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_FILE = PROCESSED_DIR / "frontur_canarias_monthly.csv"

DB_PATH = BASE_DIR / "db.sqlite3"
DB_URL = f"sqlite:///{DB_PATH}"

TABLE_NAME = "frontur_canarias_monthly"


def main():
    print("=== ETL FRONTUR-CANARIAS (OBSERVATIONS TSV) ===")

    if not RAW_OBS_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el fichero de observaciones:\n{RAW_OBS_FILE}\n"
            "Mueve el TSV de ISTAC a data/raw con ese nombre."
        )

    os.makedirs(PROCESSED_DIR, exist_ok=True)

    print(f"[1] Cargando TSV de observaciones desde:\n    {RAW_OBS_FILE}")
    df_obs = pd.read_csv(RAW_OBS_FILE, sep="\t", dtype=str)

    print("\nColumnas encontradas en OBSERVATIONS:")
    print(list(df_obs.columns), "\n")

    # === 1. Filtrar solo Canarias y medida 'Turistas' ===
    mask_canarias = df_obs["TERRITORIO"] == "Canary Islands"
    mask_turistas = df_obs["MEDIDAS"] == "Turistas"

    df = df_obs[mask_canarias & mask_turistas].copy()

    if df.empty:
        raise ValueError("No hay filas para (TERRITORIO='Canary Islands', MEDIDAS='Turistas').")

    # === 2. Extraer año y mes del campo TIME_PERIOD (formato '10/2025') ===
    periodo = df["TIME_PERIOD"].astype(str)

    df["month"] = periodo.str.extract(r"(\d{2})/\d{4}").astype(int)
    df["year"] = periodo.str.extract(r"\d{2}/(\d{4})").astype(int)

    # === 3. Limpiar número de turistas (OBS_VALUE) ===
    # En este dataset son enteros sin separador de miles (ej. 1370188), pero lo hacemos robusto.
    tourists_str = (
        df["OBS_VALUE"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["tourists"] = pd.to_numeric(tourists_str, errors="coerce")

    df = df.dropna(subset=["tourists"])

    # === 4. Normalizar residencia (LUGAR_RESIDENCIA) ===
    df["residence"] = df["LUGAR_RESIDENCIA"].astype(str).str.strip()

    # === 5. Dataset final limpio ===
    df_clean = df[["year", "month", "residence", "tourists"]].copy()
    df_clean = df_clean.sort_values(["year", "month", "residence"])

    print("Primeras filas limpias:")
    print(df_clean.head(12))

    # === 6. Guardar CSV procesado ===
    df_clean.to_csv(PROCESSED_FILE, index=False, encoding="utf-8")
    print(f"\n[OK] CSV procesado guardado en:\n    {PROCESSED_FILE}")

    # === 7. Guardar en SQLite ===
    engine = create_engine(DB_URL)

    with engine.begin() as conn:
        df_clean.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

    print(f"[OK] Tabla '{TABLE_NAME}' creada / reemplazada en:\n    {DB_PATH}")
    print("=== ETL FRONTUR-CANARIAS COMPLETADO ===")


if __name__ == "__main__":
    main()
