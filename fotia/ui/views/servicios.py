"""Módulo D — Tarifario de servicios (RF-07)."""

from __future__ import annotations

import customtkinter as ctk

from ...domain.models import Servicio
from ...util import moneda
from ..dialogs import DialogoServicio
from ..theme import GRIS_TEXTO
from ..widgets import Tabla, boton
from .base import VistaBase


class VistaServicios(VistaBase):
    clave = "servicios"
    titulo = "Catálogo de servicios y precios"
    descripcion = "Módulo D · tarifario configurable: coberturas, paquetes, edición, fotolibros y viáticos"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        boton(barra, "Nuevo servicio", self._nuevo).pack(side="left", padx=(0, 6))
        boton(barra, "Editar", self._editar).pack(side="left", padx=(0, 6))
        boton(barra, "Eliminar", self._eliminar, color="peligro").pack(side="left", padx=(0, 6))

        self._categoria = ctk.StringVar(value="Todas las categorías")
        self._menu = ctk.CTkOptionMenu(
            barra, values=["Todas las categorías"], variable=self._categoria,
            width=200, dynamic_resizing=False,
            command=lambda _v: self.refrescar(),
        )
        self._menu.pack(side="left", padx=(14, 6))

        self._busqueda = ctk.CTkEntry(barra, width=240,
                                      placeholder_text="Buscar servicio…")
        self._busqueda.pack(side="right")
        self._busqueda.bind("<KeyRelease>", self.refrescar_diferido)

        columnas = [
            {"clave": "categoria", "titulo": "Categoría", "ancho": 160},
            {"clave": "nombre", "titulo": "Servicio", "ancho": 300},
            {"clave": "precio", "titulo": "Precio", "ancho": 140, "anchor": "e"},
            {"clave": "unidad", "titulo": "Unidad", "ancho": 130},
            {"clave": "estado", "titulo": "Estado", "ancho": 110, "anchor": "center"},
            {"clave": "notas", "titulo": "Notas", "ancho": 260},
        ]
        self.tabla = Tabla(contenedor, columnas, doble_click=lambda _e: self._editar(),
                           altura=17)
        self.tabla.grid(row=1, column=0, sticky="nsew")

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def refrescar(self) -> None:
        servicios = self.repos.servicios.listar()
        categorias = ["Todas las categorías"] + self.repos.servicios.categorias()
        actual = self._categoria.get()
        self._menu.configure(values=categorias)
        self._menu.set(actual if actual in categorias else "Todas las categorías")

        texto = self._busqueda.get().strip().lower()
        filas, objetos, etiquetas = [], [], []
        for s in servicios:
            if self._categoria.get() != "Todas las categorías" and \
                    s.categoria != self._categoria.get():
                continue
            if texto and texto not in f"{s.nombre} {s.categoria}".lower():
                continue
            filas.append([s.categoria, s.nombre, moneda(s.precio), s.unidad,
                          "Activo" if s.activo else "Inactivo", s.notas or ""])
            objetos.append(s)
            etiquetas.append("" if s.activo else "entregado")
        self.tabla.actualizar(filas, objetos, etiquetas)
        activos = sum(1 for s in objetos if s.activo)
        promedio = (sum(s.precio for s in objetos if s.activo) / activos) if activos else 0
        self._pie.configure(
            text=f"{len(objetos)} servicio(s) · {activos} activo(s) · "
            f"precio promedio {moneda(promedio)}"
        )

    def _seleccion(self):
        servicio = self.tabla.seleccionado()
        if servicio is None:
            self.advertir("Sin selección", "Elija un servicio en la tabla.")
        return servicio

    def _nuevo(self) -> None:
        servicio = DialogoServicio(
            self, self.repos.servicios.categorias()
        ).mostrar()
        if servicio is None:
            return
        self.ejecutar(lambda: self.repos.servicios.crear(servicio))

    def _editar(self) -> None:
        servicio = self._seleccion()
        if servicio is None:
            return
        editado = DialogoServicio(self, self.repos.servicios.categorias(),
                                  servicio).mostrar()
        if editado is None:
            return
        self.ejecutar(lambda: self.repos.servicios.actualizar(editado))

    def _eliminar(self) -> None:
        servicio = self._seleccion()
        if servicio is None:
            return
        if not self.confirmar("Eliminar servicio",
                              f"¿Quitar «{servicio.nombre}» del tarifario?"):
            return
        self.ejecutar(lambda: self.repos.servicios.eliminar(servicio.id))


__all__ = ["VistaServicios", "Servicio"]
