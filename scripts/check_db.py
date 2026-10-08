import os
import sqlite3

ruta = os.path.join(os.environ["APPDATA"], "Fotique", "fotique.db")
conn = sqlite3.connect(ruta)
tablas = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("tablas:", ", ".join(tablas))
for tabla in ["equipos", "fotografos", "clientes", "proyectos", "pagos",
              "trabajos_pendientes", "servicios", "plantillas_contrato",
              "contratos", "eventos"]:
    total = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    print(f"  {tabla}: {total}")
conn.close()
