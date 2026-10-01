"""Módulo B — Gestión de fotógrafos / personal (RF-04)."""

from __future__ import annotations

import customtkinter as ctk

from ...domain.models import Fotografo
from ..dialogs import (
    DialogoFichaFotografo,
    DialogoFotografo,
    DialogoTabla,
    DialogoTrabajo,
)
from ..theme import GRIS_TEXTO, ROJO, colores_tema
from ..widgets import Tabla, boton, boton_secundario
from .base import VistaBase


class VistaFotografos(VistaBase):
    clave = "fotografos"
    titulo = "Fotógrafos y personal"
    descripcion = "Módulo B · equipos tomados, calendario personal y entregas pendientes"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        boton(barra, "Nuevo fotógrafo", self._nuevo).pack(side="left", padx=(0, 6))
        boton(barra, "Editar", self._editar).pack(side="left", padx=(0, 6))
        boton_secundario(barra, "Ficha", self._ficha).pack(side="left", padx=(0, 6))
        boton(barra, "Nuevo trabajo", self._nuevo_trabajo, color="#2ea043").pack(
            side="left", padx=(0, 6)
        )
        boton(barra, "Ver entregas", self._ver_entregas).pack(side="left", padx=(0, 6))
        boton(barra, "Eliminar", self._eliminar, color=ROJO).pack(side="left", padx=(0, 6))

        self._busqueda = ctk.CTkEntry(barra, width=250,
                                      placeholder_text="Buscar nombre, teléfono o email…")
        self._busqueda.pack(side="right")
        self._busqueda.bind("<KeyRelease>", lambda _e: self.refrescar())

        columnas = [
            {"clave": "nombre", "titulo": "Nombre y apellido", "ancho": 210},
            {"clave": "telefono", "titulo": "Teléfono", "ancho": 150},
            {"clave": "email", "titulo": "Email", "ancho": 200},
            {"clave": "equipos", "titulo": "Equipos", "ancho": 80, "anchor": "center"},
            {"clave": "activas", "titulo": "Entregas activas", "ancho": 110, "anchor": "center"},
            {"clave": "proxima", "titulo": "Próxima entrega", "ancho": 125, "anchor": "center"},
            {"clave": "estado", "titulo": "Estado", "ancho": 90, "anchor": "center"},
        ]
        self.tabla = Tabla(contenedor, columnas, doble_click=lambda _e: self._ficha(),
                           altura=16)
        self.tabla.grid(row=1, column=0, sticky="nsew")

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def refrescar(self) -> None:
        texto = self._busqueda.get().strip().lower()
        resumenes = self.repos.fotografos.listar_resumen()
        filas, objetos, etiquetas = [], [], []
        for r in resumenes:
            f = r["fotografo"]
            if texto and texto not in (
                f.nombre_completo.lower(), (f.telefono or "").lower(),
                (f.email or "").lower(),
            ) and texto not in f.nombre_completo.lower():
                continue
            filas.append([
                f.nombre_completo,
                f.telefono or "—",
                f.email or "—",
                str(r["n_equipos"]),
                str(r["n_activos"]),
                r["proxima"].strftime("%d/%m/%Y") if r["proxima"] else "—",
                "Activo" if f.activo else "Inactivo",
            ])
            objetos.append(f)
            etiquetas.append("" if f.activo else "entregado")
        self.tabla.actualizar(filas, objetos, etiquetas)
        activos = sum(1 for f in objetos if f.activo)
        pendientes = sum(r["n_activos"] for r in resumenes)
        self._pie.configure(
            text=f"{len(objetos)} fotógrafo(s) · {activos} activos · "
            f"{pendientes} entrega(s) en curso"
        )

    # -- acciones ---------------------------------------------------------- #
    def _seleccion(self):
        fotografo = self.tabla.seleccionado()
        if fotografo is None:
            self.advertir("Sin selección", "Elija un fotógrafo en la tabla.")
        return fotografo

    def _nuevo(self) -> None:
        fotografo = DialogoFotografo(self).mostrar()
        if fotografo is None:
            return
        self.ejecutar(lambda: self.repos.fotografos.crear(fotografo))

    def _editar(self) -> None:
        fotografo = self._seleccion()
        if fotografo is None:
            return
        editado = DialogoFotografo(self, fotografo).mostrar()
        if editado is None:
            return
        self.ejecutar(lambda: self.repos.fotografos.actualizar(editado))

    def _ficha(self) -> None:
        fotografo = self._seleccion()
        if fotografo is None:
            return
        detalle = self.repos.fotografos.detalle(fotografo.id)
        if detalle is None:
            return
        DialogoFichaFotografo(
            self, detalle, detalle.equipos_tomados, detalle.trabajos
        ).mostrar()

    def _nuevo_trabajo(self) -> None:
        fotografo = self.tabla.seleccionado()
        trabajo = DialogoTrabajo(
            self,
            self.repos.fotografos.listar(),
            self.repos.proyectos.listar(),
            fotografo_inicial=fotografo,
        ).mostrar()
        if trabajo is None:
            return
        self.ejecutar(lambda: self.repos.trabajos.crear(trabajo))

    def _ver_entregas(self) -> None:
        fotografo = self.tabla.seleccionado()
        trabajos = self.repos.trabajos.listar(
            fotografo_id=fotografo.id if fotografo else None
        )
        filas = [
            [
                t.titulo,
                t.fotografo.nombre_completo if t.fotografo else "—",
                (t.proyecto.titulo if t.proyecto else "—") or "—",
                t.fecha_entrega.strftime("%d/%m/%Y") if t.fecha_entrega else "—",
                str(t.estado),
                t.descripcion or "",
            ]
            for t in trabajos
        ]
        DialogoTabla(
            self,
            "Entregas y trabajos pendientes" + (
                f" — {fotografo.nombre_completo}" if fotografo else ""),
            [
                {"clave": "titulo", "titulo": "Trabajo", "ancho": 240},
                {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 160},
                {"clave": "proyecto", "titulo": "Proyecto", "ancho": 170},
                {"clave": "entrega", "titulo": "Entrega", "ancho": 110, "anchor": "center"},
                {"clave": "estado", "titulo": "Estado", "ancho": 110, "anchor": "center"},
                {"clave": "desc", "titulo": "Descripción", "ancho": 240},
            ],
            filas,
        ).mostrar()

    def _eliminar(self) -> None:
        fotografo = self._seleccion()
        if fotografo is None:
            return
        if not self.confirmar(
            "Eliminar fotógrafo",
            f"¿Dar de baja a {fotografo.nombre_completo}?\n"
            "Si tiene equipos o entregas activas el sistema lo impedirá (RNF-04).",
        ):
            return
        self.ejecutar(lambda: self.repos.fotografos.eliminar(fotografo.id))
