"""Base común de todas las vistas."""

from __future__ import annotations

from typing import Any, Callable, Optional

import customtkinter as ctk

from ..theme import FUENTE_PEQUE, FUENTE_TITULO, GRIS_TEXTO, TEXTO
from ..widgets import DialogoMensaje, ejecutar_protegido

ESPERA_BUSQUEDA_MS = 180


class VistaBase(ctk.CTkFrame):
    """Pantalla con cabecera, refresco periódico y manejo de errores."""

    clave = ""
    titulo = ""
    solo_admin = False

    def __init__(self, master: Any, app: Any):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._refresco_pendiente: Optional[str] = None
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.grid(row=0, column=0, sticky="ew", padx=4, pady=(2, 14))
        cabecera.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cabecera, text=self.titulo, font=FUENTE_TITULO,
                     text_color=TEXTO, anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        if getattr(self, "descripcion", ""):
            ctk.CTkLabel(cabecera, text=self.descripcion, font=FUENTE_PEQUE,
                         text_color=GRIS_TEXTO, anchor="w").grid(
                row=1, column=0, sticky="w"
            )
        self.cabecera_acciones = cabecera
        self._construir()

    # -- subclases -------------------------------------------------------- #
    def _construir(self) -> None:
        raise NotImplementedError

    def refrescar(self) -> None:
        """Actualiza la vista con los datos actuales de la base."""

    def refrescar_diferido(self, *_args) -> None:
        """Refresca cuando el usuario deja de tipear (evita una consulta por tecla)."""
        if self._refresco_pendiente is not None:
            self.after_cancel(self._refresco_pendiente)
        self._refresco_pendiente = self.after(ESPERA_BUSQUEDA_MS, self._refresco_diferido)

    def _refresco_diferido(self) -> None:
        self._refresco_pendiente = None
        self.refrescar()

    # -- accesos ---------------------------------------------------------- #
    @property
    def repos(self):
        return self.app.repos

    def acciones(self, *botones: tuple) -> None:
        """Agrega botones a la cabecera: ``(texto, comando[, color])``."""
        from ..widgets import boton

        if not hasattr(self, "_n_accion"):
            self._n_accion = 1  # la columna 0 la ocupa el título
        for item in botones:
            texto, comando = item[0], item[1]
            color = item[2] if len(item) > 2 else None
            kwargs = {"color": color} if color else {}
            boton(self.cabecera_acciones, texto, comando, **kwargs).grid(
                row=0, column=self._n_accion, padx=(8, 0), sticky="e"
            )
            self._n_accion += 1
        self.cabecera_acciones.grid_columnconfigure(99, weight=1)

    # -- avisos ----------------------------------------------------------- #
    def ejecutar(self, accion: Callable[[], Any],
                 refrescar: Optional[Callable[[], Any]] = None) -> Any:
        return ejecutar_protegido(self, accion, refrescar or self.refrescar)

    def informar(self, titulo: str, mensaje: str) -> None:
        DialogoMensaje.info(self, titulo, mensaje)

    def advertir(self, titulo: str, mensaje: str) -> None:
        DialogoMensaje.error(self, titulo, mensaje)

    def confirmar(self, titulo: str, mensaje: str,
                  texto_si: str = "Eliminar") -> bool:
        return DialogoMensaje.confirmar(self, titulo, mensaje, texto_si)
