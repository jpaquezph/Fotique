"""Smoke test de la UI: construye la ventana, refresca todas las vistas y sale."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotia.app import Aplicacion  # noqa: E402
from fotia.db import cargar_datos_demo  # noqa: E402
from fotia.ui import VentanaPrincipal  # noqa: E402
from fotia.ui.theme import aplicar_estilo_tabla, configurar_apariencia  # noqa: E402


def _log(mensaje: str) -> None:
    print(mensaje, flush=True)


def main() -> int:
    carpeta = Path(__file__).resolve().parent / "_smoke"
    shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(parents=True, exist_ok=True)

    app = Aplicacion(carpeta / "fotia_smoke.db")
    configurar_apariencia("Dark")
    aplicar_estilo_tabla()
    cargar_datos_demo(app.repos)

    ventana = VentanaPrincipal(app)
    app.ventana = ventana
    ventana.update()

    errores: list[str] = []
    for clave in list(ventana.vistas):
        try:
            ventana.mostrar(clave)
            ventana.update()
            _log(f"  vista {clave}: OK")
        except Exception as exc:  # noqa: BLE001
            errores.append(f"{clave}: {type(exc).__name__}: {exc}")
            _log(f"  vista {clave}: FALLA — {type(exc).__name__}: {exc}")

    # cambio de apariencia: vuelve a estilizar las tablas ttk
    try:
        from fotia.ui.theme import aplicar_estilo_tabla as aplicar

        configurar_apariencia("Light")
        aplicar()
        ventana.refrescar_todo()
        ventana.update()
        _log("  cambio de tema claro: OK")
    except Exception as exc:  # noqa: BLE001
        errores.append(f"tema: {type(exc).__name__}: {exc}")
        _log(f"  cambio de tema claro: FALLA — {exc}")

    try:
        ventana.destroy()
        app.cerrar()
    except Exception as exc:  # noqa: BLE001
        errores.append(f"cierre: {type(exc).__name__}: {exc}")

    if errores:
        _log(f"SMOKE FALLÓ ({len(errores)}):")
        for e in errores:
            _log(f"  - {e}")
        return 1
    _log("SMOKE OK: todas las vistas se construyeron y refrescaron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
