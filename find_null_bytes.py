import pathlib

root = pathlib.Path(__file__).resolve().parent

print(f"Escaneando en: {root}")

found_any = False

for path in root.rglob("*.py"):
    try:
        data = path.read_bytes()
    except Exception as e:
        print(f"[ERROR] No se pudo leer {path}: {e}")
        continue

    if b"\x00" in data:
        found_any = True
        print(f"[NULL BYTES] {path}")

if not found_any:
    print("No se encontraron archivos .py con bytes nulos.")
