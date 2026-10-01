"""Ventana principal de Fotia: navegación lateral, menús y apariencia."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import Menu

from . import views
from .theme import (
    ACENTO,
    FUENTE_PEQUE,
    FUENTE_SUBTITULO,
    GRIS_TEXTO,
    TEMAS,
    aplicar_estilo_tabla,
    configurar_apariencia,
    colores_tema,
)

MENU_NAVEGACION = [
    ("panel", "Panel de control"),
    ("equipos", "Inventario de equipos"),
    ("fotografos", "Fotógrafos"),
    ("proyectos", "Clientes y proyectos"),
    ("calendario", "Calendario"),
    ("servicios", "Tarifario"),
    ("contratos", "Contratos"),
    ("respaldos", "Respaldo y datos"),
]

VERSION = "1.0.0"


class VentanaPrincipal(ctk.CTk):
    def __init__(self, app: Any):
        super().__init__()
        self.app = app
        self.title("Fotia — Gestión integral de estudio fotográfico")
        self.geometry("1360x860")
        self.minsize(1140, 720)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        c = colores_tema()
        self._crear_menu()

        # -- barra lateral -------------------------------------------------- #
        lateral = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=None)
        lateral.grid(row=0, column=0, sticky="nsew")
        lateral.grid_propagate(False)
        ctk.CTkLabel(lateral, text="FOTIA", font=("Segoe UI", 26, "bold"),
                     text_color=c["texto"], anchor="w").pack(
            fill="x", padx=20, pady=(26, 0))
        ctk.CTkLabel(lateral, text="Estudio fotográfico", font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, anchor="w").pack(
            fill="x", padx=20, pady=(0, 22))

        self._botones: dict[str, ctk.CTkButton] = {}
        for clave, texto in MENU_NAVEGACION:
            btn = ctk.CTkButton(
                lateral, text=texto, anchor="w", height=38, corner_radius=8,
                font=FUENTE_SUBTITULO, fg_color="transparent",
                hover_color=c["borde"], text_color=c["texto"],
                command=lambda k=clave: self.mostrar(k),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self._botones[clave] = btn

        pie = ctk.CTkFrame(lateral, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=14, pady=16)
        ctk.CTkLabel(pie, text="Apariencia", font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, anchor="w").pack(fill="x")
        self._tema = ctk.StringVar(value=self.app.tema)
        menu_tema = ctk.CTkOptionMenu(
            pie, values=list(TEMAS), variable=self._tema, dynamic_resizing=False,
            command=self._cambiar_tema,
        )
        menu_tema.pack(fill="x", pady=(4, 8))
        self._ruta_label = ctk.CTkLabel(pie, text="", font=("Segoe UI", 9),
                                        text_color=GRIS_TEXTO, anchor="w",
                                        wraplength=210, justify="left")
        self._ruta_label.pack(fill="x")
        ctk.CTkLabel(pie, text=f"Fotia {VERSION}", font=("Segoe UI", 9),
                     text_color=GRIS_TEXTO, anchor="w").pack(fill="x", pady=(6, 0))

        # -- contenido ------------------------------------------------------- #
        contenedor = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        contenedor.grid(row=0, column=1, sticky="nsew", padx=(14, 16), pady=14)
        contenedor.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        self.vistas: dict[str, views.VistaBase] = {}
        for clase in views.TODAS:
            vista = clase(contenedor, app)
            vista.grid(row=0, column=0, sticky="nsew")
            self.vistas[vista.clave] = vista
        self.clave_activa = None
        self.mostrar("panel")

        self.protocol("WM_DELETE_WINDOW", self._salir)

    # -- navegación --------------------------------------------------------- #
    def mostrar(self, clave: str) -> None:
        vista = self.vistas.get(clave)
        if vista is None:
            return
        c = colores_tema()
        for k, btn in self._botones.items():
            activo = k == clave
            btn.configure(
                fg_color=ACENTO if activo else "transparent",
                text_color="#ffffff" if activo else c["texto"],
                hover_color="#36719f" if activo else c["borde"],
            )
        vista.lift()
        vista.refrescar()
        self.clave_activa = clave

    def refrescar_activa(self) -> None:
        if self.clave_activa and self.clave_activa in self.vistas:
            self.vistas[self.clave_activa].refrescar()

    def refrescar_todo(self) -> None:
        for vista in self.vistas.values():
            try:
                vista.refrescar()
            except Exception:  # pragma: no cover - nunca frenar la app por una vista
                pass

    # -- menús y apariencia -------------------------------------------------- #
    def _crear_menu(self) -> None:
        menu = Menu(self, tearoff=0)

        archivo = Menu(menu, tearoff=0)
        archivo.add_command(label="Crear respaldo…",
                            command=lambda: self.mostrar("respaldos"))
        archivo.add_command(label="Salir", command=self._salir)
        menu.add_cascade(label="Archivo", menu=archivo)

        ayuda = Menu(menu, tearoff=0)
        ayuda.add_command(label="Acerca de Fotia", command=self._acerca_de)
        menu.add_cascade(label="Ayuda", menu=ayuda)
        self.config(menu=menu)

    def _cambiar_tema(self, modo: str) -> None:
        configurar_apariencia(modo)
        aplicar_estilo_tabla()
        self.app.guardar_tema(modo)
        self.refrescar_todo()

    def _acerca_de(self) -> None:
        from .widgets import DialogoMensaje

        DialogoMensaje.info(
            self, "Acerca de Fotia",
            f"Fotia {VERSION} — sistema integral de gestión fotográfica.\n"
            "Escritorio, offline-first, base de datos SQLite local.\n"
            f"Base de datos: {self.app.ruta_db}",
        )

    def _salir(self) -> None:
        self.app.cerrar()
        self.destroy()
