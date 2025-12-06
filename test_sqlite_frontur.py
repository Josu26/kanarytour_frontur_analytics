import os
import pandas as pd
from sqlalchemy import create_engine, inspect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
TABLE_NAME = "frontur_euskadi_2021"

print(f"Usando BD: {DB_PATH}")

engine = create_engine(f"sqlite:///{DB_PATH}")
insp = inspect(engine)

print("\nTablas disponibles:")
for table in insp.get_table_names():
    print(f" - {table}")

print(f"\nLeyendo las primeras filas de la tabla '{TABLE_NAME}':")
df = pd.read_sql_table(TABLE_NAME, engine)
print(df.head())
print(f"\nFilas totales: {len(df)}")
