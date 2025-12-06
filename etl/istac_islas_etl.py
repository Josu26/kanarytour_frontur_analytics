import pandas as pd
import sqlite3
from pathlib import Path

# ==== Rutas básicas ====
# BASE_DIR = carpeta raíz del proyecto (kanarytour_frontur_analytics)
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "db.sqlite3"

# Archivos descargados del ISTAC (tabla 6)
OBS_FILE = RAW_DIR / "dataset-ISTAC-E16028B_000011-~latest-observations.tsv"
ATTR_FILE = RAW_DIR / "dataset-ISTAC-E16028B_000011-~latest-attributes.tsv"  # ahora no lo usamos, pero lo dejamos referenciado

# Nombre de la tabla nueva en SQLite
TABLE_NAME = "frontur_canarias_islands_monthly"

# CSV procesado que dejaremos en data/processed
PROCESSED_CSV = PROCESSED_DIR / "frontur_canarias_islands_monthly.csv"


def main():
    print("==== ETL ISTAC · Tabla 6 (Islas por residencia) ====")
    print("BASE_DIR:", BASE_DIR)
    print("Leyendo observaciones de:", OBS_FILE)

    # === 1. Leer observaciones ===
    df = pd.read_csv(OBS_FILE, sep="\t")

    # Solo nos quedamos con viajeros tipo "Tourist" y medida "Turistas"
    df = df[
        (df["TIPO_VIAJERO"] == "Tourist")
        & (df["MEDIDAS"] == "Turistas")
    ].copy()

    print("Filas tras filtrar Tourist/Turistas:", len(df))

    # === 2. Parsear año/mes desde TIME_PERIOD ("10/2025" → year=2025, month=10) ===
    def parse_period(s: str):
        m_str, y_str = str(s).split("/")
        return int(y_str), int(m_str)

    df["year"], df["month"] = zip(*df["TIME_PERIOD"].map(parse_period))

    # Fecha normalizada YYYY-MM-01 (como texto, amigable para SQLite y Django)
    df["date"] = pd.to_datetime(df[["year", "month"]].assign(day=1))

    # === 3. Nos quedamos con las columnas relevantes y renombramos ===
    clean = df[
        ["year", "month", "date", "LUGAR_RESIDENCIA", "TERRITORIO", "OBS_VALUE"]
    ].rename(
        columns={
            "LUGAR_RESIDENCIA": "residence",
            "TERRITORIO": "island",
            "OBS_VALUE": "tourists",
        }
    )

    # Quitamos filas sin dato numérico
    before = len(clean)
    clean = clean.dropna(subset=["tourists"])
    after = len(clean)
    print(f"Filas totales: {before}  →  después de limpiar NaN: {after}")

    # Aseguramos tipos básicos
    clean["year"] = clean["year"].astype(int)
    clean["month"] = clean["month"].astype(int)
    clean["date"] = clean["date"].dt.strftime("%Y-%m-%d")
    clean["residence"] = clean["residence"].astype(str)
    clean["island"] = clean["island"].astype(str)
    clean["tourists"] = clean["tourists"].astype(float)

    # === 4. Guardar CSV procesado ===
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(PROCESSED_CSV, index=False, encoding="utf-8")
    print("✔ CSV limpio guardado en:", PROCESSED_CSV)

    # === 5. Volcar a SQLite (db.sqlite3 de Django) ===
    print("Conectando a SQLite:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        date TEXT NOT NULL,
        residence TEXT NOT NULL,
        island TEXT NOT NULL,
        tourists REAL
    );
    """

    print("Creando tabla (si no existe):", TABLE_NAME)
    cur.execute(create_sql)

    # Opcional: borramos todo para recargar limpio
    print("Borrando datos previos (si los hay)...")
    cur.execute(f"DELETE FROM {TABLE_NAME};")

    insert_sql = f"""
    INSERT INTO {TABLE_NAME} (year, month, date, residence, island, tourists)
    VALUES (?, ?, ?, ?, ?, ?);
    """

    records = [
        (
            int(row["year"]),
            int(row["month"]),
            row["date"],
            row["residence"],
            row["island"],
            float(row["tourists"]),
        )
        for _, row in clean.iterrows()
    ]

    print(f"Insertando {len(records)} filas en {TABLE_NAME}...")
    cur.executemany(insert_sql, records)
    conn.commit()
    conn.close()

    print("✔ ETL completado para", TABLE_NAME)


if __name__ == "__main__":
    main()
