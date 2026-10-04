"""Punto de entrada de la aplicación Fotia."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Union

from .db import BaseDatos, cargar_datos_demo
from .domain.models import Usuario
from .ui import VentanaPrincipal
from .ui.theme import aplicar_estilo_tabla, configurar_apariencia
from .util import ruta_base_datos


class Aplicacion:
    """Contexto compartido: base de datos, preferencias, sesión y ventana."""

    def __init__(self, ruta: Optional[Union[str, Path]] = None):
        self.db = BaseDatos(ruta)
        self.ruta_db = self.db.ruta
        self.ventana: Optional[VentanaPrincipal] = None
        self.tema = self.db.repos.config("tema", "Sistema")
        self.usuario: Optional[Usuario] = None

    @property
    def repos(self):
        return self.db.repos

    @property
    def es_admin(self) -> bool:
        """Sin sesión (pruebas, scripts) no hay restricciones de rol."""
        return self.usuario is None or self.usuario.es_admin

    def guardar_tema(self, modo: str) -> None:
        self.tema = modo
        self.repos.set_config("tema", modo)

    def refrescar_todo(self) -> None:
        if self.ventana is not None:
            self.ventana.refrescar_todo()

    def cerrar(self) -> None:
        self.db.cerrar()


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ruta = argv[0] if argv else None
    destino = Path(ruta) if ruta else ruta_base_datos()
    primera_vez = not Path(destino).exists()

    app = Aplicacion(destino)
    configurar_apariencia(app.tema)
    aplicar_estilo_tabla()

    # La primera instalación arranca con datos de ejemplo para poder explorar.
    if primera_vez or app.repos.esta_vacio():
        cargar_datos_demo(app.repos)

    try:
        ventana = VentanaPrincipal(app, acceso=True)
        app.ventana = ventana
        ventana.mainloop()
    finally:
        app.cerrar()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
