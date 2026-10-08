"""Configuración: cuenta propia, apariencia, versión y respaldo de datos."""

from __future__ import annotations

import customtkinter as ctk

from ... import __version__
from ..theme import (
    BORDE,
    FONDO,
    FUENTE_PEQUE,
    FUENTE_SUBTITULO,
    GRIS_TEXTO,
    RADIO,
    SEMINEGRITA,
    TEMAS,
)
from ..widgets import boton, boton_secundario
from .base import VistaBase
from .respaldos import VistaRespaldos

SECCIONES = ["General", "Respaldo de datos"]


class VistaConfiguracion(VistaBase):
    clave = "configuracion"
    titulo = "Configuración"
    descripcion = "Mi cuenta, apariencia, versión y respaldo de datos"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        self._seccion = ctk.StringVar(value=SECCIONES[0])
        ctk.CTkSegmentedButton(contenedor, values=SECCIONES, variable=self._seccion,
                               command=lambda _v: self.mostrar_seccion()).grid(
            row=0, column=0, sticky="w", pady=(0, 10))

        self.respaldos = VistaRespaldos(contenedor, self.app)
        self._paneles = {
            "General": self._panel_general(contenedor),
            "Respaldo de datos": self.respaldos,
        }
        self.mostrar_seccion(refrescar=False)

    def _tarjeta(self, master, columna: int, titulo: str) -> ctk.CTkFrame:
        tarjeta = ctk.CTkFrame(master, corner_radius=RADIO, fg_color=FONDO,
                               border_width=1, border_color=BORDE)
        tarjeta.grid(row=0, column=columna, sticky="nsew",
                     padx=(0 if columna == 0 else 12, 0))
        ctk.CTkLabel(tarjeta, text=titulo, font=FUENTE_SUBTITULO,
                     anchor="w").pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkFrame(tarjeta, height=2, corner_radius=0, fg_color=BORDE).pack(
            fill="x", padx=16, pady=(0, 10))
        return tarjeta

    def _dato(self, master, etiqueta: str) -> ctk.CTkLabel:
        ctk.CTkLabel(master, text=etiqueta, font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, anchor="w", height=16).pack(
            fill="x", padx=16)
        valor = ctk.CTkLabel(master, text="—", font=(SEMINEGRITA, 12),
                             anchor="w", wraplength=260, justify="left")
        valor.pack(fill="x", padx=16, pady=(0, 8))
        return valor

    def _panel_general(self, master) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(master, fg_color="transparent")
        for columna in range(3):
            panel.grid_columnconfigure(columna, weight=1, uniform="config")

        cuenta = self._tarjeta(panel, 0, "Mi cuenta")
        self._cuenta = {clave: self._dato(cuenta, etiqueta) for clave, etiqueta in [
            ("usuario", "Usuario"), ("nombre", "Nombre y apellido"),
            ("email", "Email"), ("rol", "Rol"),
        ]}
        self._editar = boton(cuenta, "Editar datos y contraseña", self._mi_cuenta,
                             ancho=220)
        self._editar.pack(anchor="w", padx=16, pady=(6, 16))

        apariencia = self._tarjeta(panel, 1, "Apariencia")
        ctk.CTkLabel(apariencia, text="Modo de color", font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, anchor="w", height=16).pack(fill="x", padx=16)
        self._tema = ctk.StringVar(value=self.app.tema)
        ctk.CTkOptionMenu(apariencia, values=list(TEMAS), variable=self._tema,
                          width=200, dynamic_resizing=False,
                          command=self._cambiar_tema).pack(anchor="w", padx=16, pady=(2, 8))
        ctk.CTkLabel(apariencia, text="«Sistema» sigue el modo claro u oscuro de Windows.",
                     font=FUENTE_PEQUE, text_color=GRIS_TEXTO, anchor="w",
                     wraplength=260, justify="left").pack(fill="x", padx=16, pady=(0, 16))

        version = self._tarjeta(panel, 2, "Versión")
        self._dato(version, "Fotique").configure(text=__version__)
        self._dato(version, "Base de datos").configure(text=str(self.app.ruta_db))
        boton_secundario(version, "Ir al respaldo de datos",
                         lambda: self.mostrar_seccion("Respaldo de datos"),
                         ancho=200).pack(anchor="w", padx=16, pady=(6, 16))
        return panel

    def mostrar_seccion(self, seccion: str | None = None, refrescar: bool = True) -> None:
        if seccion is not None:
            self._seccion.set(seccion)
        for nombre, panel in self._paneles.items():
            if nombre == self._seccion.get():
                panel.grid(row=1, column=0, sticky="nsew")
            else:
                panel.grid_remove()
        if refrescar:
            self.refrescar()

    def refrescar(self) -> None:
        if self._seccion.get() == "Respaldo de datos":
            self.respaldos.refrescar()
            return
        usuario = self.app.usuario
        datos = ({"usuario": usuario.usuario, "nombre": usuario.nombre or "—",
                  "email": usuario.email or "—", "rol": str(usuario.rol)}
                 if usuario is not None else dict.fromkeys(self._cuenta, "—"))
        for clave, valor in datos.items():
            if self._cuenta[clave].cget("text") != valor:
                self._cuenta[clave].configure(text=valor)
        self._editar.configure(state="normal" if usuario is not None else "disabled")
        if self._tema.get() != self.app.tema:
            self._tema.set(self.app.tema)

    def _mi_cuenta(self) -> None:
        self.app.ventana.mi_cuenta()
        self.refrescar()

    def _cambiar_tema(self, modo: str) -> None:
        self.app.ventana.cambiar_tema(modo)


__all__ = ["VistaConfiguracion"]
