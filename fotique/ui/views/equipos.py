"""Módulo A — Inventario y control de equipos."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from ...domain.models import EstadoEquipo, EstadoService
from ..dialogs import (
    DialogoAsignar,
    DialogoDevolver,
    DialogoEquipo,
    DialogoHistorialEquipos,
)
from ..theme import GRIS_TEXTO
from ..widgets import Tabla, boton, boton_secundario
from .base import VistaBase


class VistaEquipos(VistaBase):
    clave = "equipos"
    titulo = "Inventario de equipos"
    descripcion = "Ficha de cada unidad, movimientos y alertas de service"

    # -- construcción ------------------------------------------------------ #
    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        boton(barra, "Nuevo equipo", self._nuevo).pack(side="left", padx=(0, 6))
        boton(barra, "Editar", self._editar).pack(side="left", padx=(0, 6))
        boton(barra, "Asignar", self._asignar, color="exito").pack(side="left", padx=(0, 6))
        boton(barra, "Devolver", self._devolver, color="aviso").pack(side="left", padx=(0, 6))
        boton_secundario(barra, "Historial", self._historial).pack(side="left", padx=(0, 6))
        if self.app.es_admin:  # dar de baja equipos es sólo para administradores
            boton(barra, "Eliminar", self._eliminar, color="peligro").pack(
                side="left", padx=(0, 6))

        self._alertas_var = ctk.StringVar(value="Servicio: todos")
        menu = ctk.CTkOptionMenu(
            barra, values=["Servicio: todos", "Solo alertas"],
            variable=self._alertas_var, width=150, dynamic_resizing=False,
            command=lambda _v: self.refrescar(),
        )
        menu.pack(side="left", padx=(12, 6))

        self._busqueda = ctk.CTkEntry(barra, width=260, placeholder_text="Buscar serie, marca, modelo o fotógrafo…")
        self._busqueda.pack(side="right")
        self._busqueda.bind("<KeyRelease>", self.refrescar_diferido)

        columnas = [
            {"clave": "serie", "titulo": "N° de serie", "ancho": 130},
            {"clave": "equipo", "titulo": "Marca / Modelo", "ancho": 170},
            {"clave": "estado", "titulo": "Estado", "ancho": 90, "anchor": "center"},
            {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 150},
            {"clave": "adquisicion", "titulo": "Adquisición", "ancho": 105, "anchor": "center"},
            {"clave": "service", "titulo": "Próximo service", "ancho": 115, "anchor": "center"},
            {"clave": "alerta", "titulo": "Alerta", "ancho": 120, "anchor": "center"},
            {"clave": "notas", "titulo": "Notas", "ancho": 240},
        ]
        self.tabla = Tabla(contenedor, columnas, doble_click=self._historial, altura=4)
        self.tabla.grid(row=1, column=0, sticky="nsew")

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    # -- datos ------------------------------------------------------------- #
    def refrescar(self) -> None:
        texto = self._busqueda.get().strip()
        equipos = self.repos.equipos.listar(texto=texto)
        hoy = date.today()

        filas, etiquetas, objetos = [], [], []
        alertas_vencidas = 0
        for equipo in equipos:
            estado_service = equipo.estado_service(hoy=hoy, dias_aviso=30)
            if self._alertas_var.get() == "Solo alertas" and estado_service not in (
                EstadoService.VENCIDO,
                EstadoService.PROXIMO,
            ):
                continue
            if estado_service == EstadoService.VENCIDO:
                alertas_vencidas += 1
            # Verde: disponible (en stock). Rojo: no disponible (en uso). El
            # estado del service se lee en la columna «Alerta».
            disponible = equipo.estado == EstadoEquipo.EN_STOCK
            filas.append([
                equipo.numero_serie or "—",
                equipo.descripcion,
                str(equipo.estado),
                equipo.fotografo_actual.nombre_completo if equipo.fotografo_actual else "—",
                _fecha_o_guion(equipo.fecha_adquisicion),
                _fecha_o_guion(equipo.fecha_service_proximo),
                _texto_service(equipo, estado_service),
                equipo.notas or "",
            ])
            objetos.append(equipo)
            etiquetas.append("ok" if disponible else "vencido")
        self.tabla.actualizar(filas, objetos, etiquetas)

        stock = sum(1 for e in equipos if e.estado == EstadoEquipo.EN_STOCK)
        en_uso = len(equipos) - stock
        self._pie.configure(
            text=f"{len(objetos)} equipo(s) listados · {stock} en stock · {en_uso} en uso"
            + (f" · {alertas_vencidas} service vencido(s)" if alertas_vencidas else "")
        )

    # -- acciones ---------------------------------------------------------- #
    def _seleccion(self):
        equipo = self.tabla.seleccionado()
        if equipo is None:
            self.advertir("Sin selección", "Elija un equipo en la tabla.")
        return equipo

    def _nuevo(self) -> None:
        equipo = DialogoEquipo(self).mostrar()
        if equipo is None:
            return
        self.ejecutar(lambda: self.repos.equipos.crear(equipo))

    def _editar(self) -> None:
        equipo = self._seleccion()
        if equipo is None:
            return
        editado = DialogoEquipo(self, equipo).mostrar()
        if editado is None:
            return
        self.ejecutar(lambda: self.repos.equipos.actualizar(editado))

    def _asignar(self) -> None:
        equipo = self._seleccion()
        if equipo is None:
            return
        if equipo.estado == EstadoEquipo.EN_USO:
            self.advertir("Equipo en uso",
                          "Devuélvalo al stock antes de asignarlo a otra persona.")
            return
        fotografos = self.repos.fotografos.listar()
        if not fotografos:
            self.advertir("Sin fotógrafos", "Registre un fotógrafo antes de asignar equipos.")
            return
        datos = DialogoAsignar(self, equipo, fotografos,
                               self.repos.proyectos.listar()).mostrar()
        if datos is None:
            return
        self.ejecutar(lambda: self.repos.equipos.asignar(
            equipo.id, datos["fotografo_id"], datos["fecha"], datos["observaciones"],
            proyecto_id=datos["proyecto_id"], fecha_prevista=datos["fecha_prevista"]))

    def _devolver(self) -> None:
        equipo = self._seleccion()
        if equipo is None:
            return
        if equipo.estado != EstadoEquipo.EN_USO:
            self.advertir("Ya está en stock", "Este equipo no está asignado.")
            return
        datos = DialogoDevolver(self, equipo).mostrar()
        if datos is None:
            return
        self.ejecutar(lambda: self.repos.equipos.devolver(
            equipo.id, datos["fecha"], datos["observaciones"]))

    def _historial(self, equipo=None) -> None:
        """Todos los movimientos; con ``equipo`` abre ya filtrado por esa unidad."""
        DialogoHistorialEquipos(
            self, self.repos.equipos.listar(), self.repos.fotografos.listar(),
            lambda equipo_id, fotografo_id, desde, hasta: self.repos.equipos.historial(
                equipo_id=equipo_id, fotografo_id=fotografo_id, desde=desde, hasta=hasta),
            equipo,
        ).mostrar()

    def _eliminar(self) -> None:
        equipo = self._seleccion()
        if equipo is None:
            return
        if not self.app.es_admin:
            self.advertir("Sólo administradores",
                          "Dar de baja un equipo requiere una cuenta de administrador.")
            return
        if not self.confirmar("Eliminar equipo", f"¿Dar de baja {equipo.nombre}?"):
            return
        self.ejecutar(lambda: self.repos.equipos.eliminar(equipo.id))


def _fecha_o_guion(valor) -> str:
    from ...util import fecha_legible

    return fecha_legible(valor) or "—"


def _texto_service(equipo, estado_service: EstadoService) -> str:
    if equipo.fecha_service_proximo is None:
        return "Sin fecha"
    if estado_service == EstadoService.VENCIDO:
        return "VENCIDO"
    if estado_service == EstadoService.PROXIMO:
        dias = (equipo.fecha_service_proximo - date.today()).days
        return f"En {dias} día(s)"
    return "En regla"
