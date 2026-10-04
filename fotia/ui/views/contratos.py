"""Módulo D — Contratos y plantillas."""

from __future__ import annotations

import customtkinter as ctk

from ...domain.models import Contrato, PlantillaContrato
from ...util import fecha_legible
from ..dialogs import DialogoContrato, DialogoPlantilla
from ..theme import BORDE, FONDO, GRIS_TEXTO
from ..widgets import Tabla, boton
from .base import VistaBase


class VistaContratos(VistaBase):
    clave = "contratos"
    titulo = "Contratos y plantillas"
    descripcion = "Contratos generados a partir de plantillas y vinculados a cada proyecto"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(2, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        self._tab = ctk.CTkTabview(contenedor, command=self.refrescar, fg_color=FONDO,
                                   border_width=1, border_color=BORDE)
        self._tab.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._tab.add("Contratos")
        self._tab.add("Plantillas")

        barra_c = ctk.CTkFrame(self._tab.tab("Contratos"), fg_color="transparent")
        barra_c.pack(fill="x", pady=(0, 6))
        boton(barra_c, "Nuevo contrato", self._nuevo_contrato).pack(
            side="left", padx=(0, 6))
        boton(barra_c, "Editar", self._editar_contrato).pack(side="left", padx=(0, 6))
        boton(barra_c, "Eliminar", self._eliminar_contrato, color="peligro").pack(
            side="left", padx=(0, 6))

        barra_p = ctk.CTkFrame(self._tab.tab("Plantillas"), fg_color="transparent")
        barra_p.pack(fill="x", pady=(0, 6))
        boton(barra_p, "Nueva plantilla", self._nueva_plantilla).pack(
            side="left", padx=(0, 6))
        boton(barra_p, "Editar", self._editar_plantilla).pack(side="left", padx=(0, 6))
        boton(barra_p, "Eliminar", self._eliminar_plantilla, color="peligro").pack(
            side="left", padx=(0, 6))

        columnas_c = [
            {"clave": "nombre", "titulo": "Contrato", "ancho": 260},
            {"clave": "proyecto", "titulo": "Proyecto", "ancho": 230},
            {"clave": "estado", "titulo": "Estado", "ancho": 110, "anchor": "center"},
            {"clave": "fecha", "titulo": "Fecha", "ancho": 110, "anchor": "center"},
            {"clave": "plantilla", "titulo": "Plantilla", "ancho": 200},
        ]
        self.tabla_contratos = Tabla(self._tab.tab("Contratos"), columnas_c,
                                     doble_click=lambda _e: self._editar_contrato(),
                                     altura=4)
        self.tabla_contratos.pack(fill="both", expand=True)

        columnas_p = [
            {"clave": "nombre", "titulo": "Plantilla", "ancho": 300},
            {"clave": "lineas", "titulo": "Líneas", "ancho": 90, "anchor": "center"},
            {"clave": "preview", "titulo": "Vista previa", "ancho": 520},
        ]
        self.tabla_plantillas = Tabla(self._tab.tab("Plantillas"), columnas_p,
                                      doble_click=lambda _e: self._editar_plantilla(),
                                      altura=4)
        self.tabla_plantillas.pack(fill="both", expand=True)

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=3, column=0, sticky="ew", pady=(6, 0))

    def refrescar(self, *_args) -> None:
        plantillas = self.repos.plantillas.listar()
        contratos = self.repos.contratos.listar()
        nombres_plantillas = {p.id: p.nombre for p in plantillas}

        filas_c, objetos_c = [], []
        for c in contratos:
            filas_c.append([
                c.nombre,
                (c.proyecto.titulo if c.proyecto else "—") or "—",
                c.estado,
                fecha_legible(c.fecha) or "—",
                nombres_plantillas.get(c.plantilla_id, "—"),
            ])
            objetos_c.append(c)
        self.tabla_contratos.actualizar(filas_c, objetos_c)

        filas_p, objetos_p = [], []
        for p in plantillas:
            preview = " ".join((p.contenido or "").split())[:160]
            filas_p.append([p.nombre, str(len((p.contenido or "").splitlines())), preview])
            objetos_p.append(p)
        self.tabla_plantillas.actualizar(filas_p, objetos_p)
        self._pie.configure(
            text=f"{len(contratos)} contrato(s) · {len(plantillas)} plantilla(s)"
        )

    # -- contratos --------------------------------------------------------- #
    def _nuevo_contrato(self) -> None:
        contrato = DialogoContrato(
            self, self.repos.proyectos.listar(), self.repos.plantillas.listar(),
            estudio=self.repos.nombre_estudio,
        ).mostrar()
        if contrato is None:
            return
        if contrato.proyecto_id is None:
            self.advertir("Proyecto requerido",
                          "Vincule el contrato a un proyecto para poder guardarlo.")
            return
        self.ejecutar(lambda: self.repos.contratos.crear(contrato))

    def _editar_contrato(self) -> None:
        contrato = self.tabla_contratos.seleccionado()
        if contrato is None:
            self.advertir("Sin selección", "Elija un contrato en la tabla.")
            return
        editado = DialogoContrato(
            self, self.repos.proyectos.listar(), self.repos.plantillas.listar(),
            contrato=contrato, estudio=self.repos.nombre_estudio,
        ).mostrar()
        if editado is None:
            return
        self.ejecutar(lambda: self.repos.contratos.actualizar(editado))

    def _eliminar_contrato(self) -> None:
        contrato = self.tabla_contratos.seleccionado()
        if contrato is None:
            self.advertir("Sin selección", "Elija un contrato en la tabla.")
            return
        if not self.confirmar("Eliminar contrato", f"¿Eliminar «{contrato.nombre}»?"):
            return
        self.ejecutar(lambda: self.repos.contratos.eliminar(contrato.id))

    # -- plantillas -------------------------------------------------------- #
    def _nueva_plantilla(self) -> None:
        plantilla = DialogoPlantilla(self).mostrar()
        if plantilla is None:
            return
        self.ejecutar(lambda: self.repos.plantillas.crear(plantilla))

    def _editar_plantilla(self) -> None:
        plantilla = self.tabla_plantillas.seleccionado()
        if plantilla is None:
            self.advertir("Sin selección", "Elija una plantilla en la tabla.")
            return
        editada = DialogoPlantilla(self, plantilla).mostrar()
        if editada is None:
            return
        self.ejecutar(lambda: self.repos.plantillas.actualizar(editada))

    def _eliminar_plantilla(self) -> None:
        plantilla = self.tabla_plantillas.seleccionado()
        if plantilla is None:
            self.advertir("Sin selección", "Elija una plantilla en la tabla.")
            return
        if not self.confirmar("Eliminar plantilla",
                              f"¿Eliminar «{plantilla.nombre}»?\n"
                              "Los contratos ya generados conservan su texto."):
            return
        self.ejecutar(lambda: self.repos.plantillas.eliminar(plantilla.id))


__all__ = ["VistaContratos", "Contrato", "PlantillaContrato"]
