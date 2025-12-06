import sqlite3

conn = sqlite3.connect("db.sqlite3")
cur = conn.cursor()

# Tabla dummy totalmente inocua, solo para cambiar el fichero
cur.execute("CREATE TABLE IF NOT EXISTS _deploy_marker (id INTEGER)")

conn.commit()
conn.close()

print("Marca de deploy creada/actualizada en db.sqlite3")
