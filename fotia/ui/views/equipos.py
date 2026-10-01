"""Módulo A — Inventario y control de equipos (RF-01, RF-02, RF-03)."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from ...domain.models import EstadoEquipo, EstadoService
from ..dialogs import (
    DialogoAsignar,
    DialogoDevolver,
    DialogoEquipo,
    DialogoFichaEquipo,
    DialogoTabla,
)
from ..theme import GRIS_TEXTO, NARANJA, ROJO, VERDE, colores_tema
from ..widgets import Tabla, boton, boton_secundario
from .base import VistaBase


class VistaEquipos(VistaBase):
    clave = "equipos"
    titulo = "Inventario de equipos"
    descripcion = "Módulo A · ficha de cada unidad, trazabilidad y alertas de service"

    # -- construcción ------------------------------------------------------ #
    def _construir(self) -> None:
        c = colores_tema()
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        boton(barra, "Nuevo equipo", self._nuevo).pack(side="left", padx=(0, 6))
        boton(barra, "Editar", self._editar).pack(side="left", padx=(0, 6))
        boton(barra, "Asignar", self._asignar, color=VERDE).pack(side="left", padx=(0, 6))
        boton(barra, "Devolver", self._devolver, color=NARANJA).pack(side="left", padx=(0, 6))
        boton_secundario(barra, "Ficha", self._ficha).pack(side="left", padx=(0, 6))
        boton(barra, "Eliminar", self._eliminar, color=ROJO).pack(side="left", padx=(0, 6))

        self._alertas_var = ctk.StringVar(value="Servicio: todos")
        menu = ctk.CTkOptionMenu(
            barra, values=["Servicio: todos", "Solo alertas"],
            variable=self._alertas_var, width=150, dynamic_resizing=False,
            command=lambda _v: self.refrescar(),
        )
        menu.pack(side="left", padx=(12, 6))

        self._busqueda = ctk.CTkEntry(barra, width=260, placeholder_text="Buscar serie, marca, modelo o fotógrafo…")
        self._busqueda.pack(side="right")
        self._busqueda.bind("<KeyRelease>", lambda _e: self.refrescar())

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
        self.tabla = Tabla(contenedor, columnas, doble_click=lambda _e: self._ficha(),
                           altura=16)
        self.tabla.grid(row=1, column=0, sticky="nsew")

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        self.acciones(("Historial global", self._historial_global))

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
            etiqueta_service = {
                EstadoService.VENCIDO: "vencido",
                EstadoService.PROXIMO: "proximo",
                EstadoService.EN_REGLA: "ok",
            }.get(estado_service, "")
            filas.append([
                equipo.numero_serie,
                equipo.descripcion,
                str(equipo.estado),
                equipo.fotografo_actual.nombre_completo if equipo.fotografo_actual else "—",
                _fecha_o_guion(equipo.fecha_adquisicion),
                _fecha_o_guion(equipo.fecha_service_proximo),
                _texto_service(equipo, estado_service),
                equipo.notas or "",
            ])
            objetos.append(equipo)
            etiquetas.append(etiqueta_service)
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
        fotografos = [f for f in self.repos.fotografos.listar() if f.activo]
        if not fotografos:
            self.advertir("Sin fotógrafos", "Registre un fotógrafo antes de asignar equipos.")
            return
        datos = DialogoAsignar(self, equipo, fotografos).mostrar()
        if datos is None:
            return
        self.ejecutar(lambda: self.repos.equipos.asignar(
            equipo.id, datos["fotografo_id"], datos["fecha"], datos["observaciones"]))

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

    def _ficha(self) -> None:
        equipo = self._seleccion()
        if equipo is None:
            return
        historial = self.repos.equipos.historial(equipo_id=equipo.id)
        DialogoFichaEquipo(self, equipo, historial).mostrar()

    def _historial_global(self) -> None:
        filas = [
            [
                f"{r['marca']} {r['modelo']} ({r['numero_serie']})",
                f"{r['f_nombre'] or ''} {r['f_apellido'] or ''}".strip() or "—",
                _fecha_o_guion(r["fecha_asignacion"]),
                _fecha_o_guion(r["fecha_devolucion"]) or "En uso",
                r["observaciones"] or "",
            ]
            for r in self.repos.equipos.historial()
        ]
        DialogoTabla(
            self,
            "Historial de movimientos de stock",
            [
                {"clave": "equipo", "titulo": "Equipo", "ancho": 220},
                {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 170},
                {"clave": "salida", "titulo": "Asignado", "ancho": 110, "anchor": "center"},
                {"clave": "devuelto", "titulo": "Devuelto", "ancho": 110, "anchor": "center"},
                {"clave": "obs", "titulo": "Observaciones", "ancho": 300},
            ],
            filas,
        ).mostrar()

    def _eliminar(self) -> None:
        equipo = self._seleccion()
        if equipo is None:
            return
        if not self.confirmar("Eliminar equipo",
                              f"¿Dar de baja {equipo.descripcion} ({equipo.numero_serie})?"):
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
