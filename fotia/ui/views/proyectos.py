"""Módulo C — Clientes y proyectos con control de seña y saldos."""

from __future__ import annotations

import customtkinter as ctk

from ...util import moneda
from ..dialogs import (
    DialogoCliente,
    DialogoContrato,
    DialogoDetalleProyecto,
    DialogoPago,
    DialogoProyecto,
)
from ..theme import GRIS_TEXTO
from ..widgets import Tabla, boton, boton_secundario
from .base import VistaBase


class VistaProyectos(VistaBase):
    clave = "proyectos"
    titulo = "Clientes y proyectos"
    descripcion = "Seña, cobros parciales y saldo pendiente de cada proyecto"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        # -- barra superior ------------------------------------------------ #
        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._modo = ctk.StringVar(value="Proyectos")
        switch = ctk.CTkSegmentedButton(
            barra, values=["Proyectos", "Clientes"],
            variable=self._modo, command=lambda _v: self._mostrar_modo(),
        )
        switch.pack(side="left", padx=(0, 14))

        self._botones_proyectos = ctk.CTkFrame(barra, fg_color="transparent")
        boton(self._botones_proyectos, "Nuevo proyecto", self._nuevo_proyecto).pack(
            side="left", padx=(0, 6))
        boton(self._botones_proyectos, "Editar", self._editar_proyecto).pack(
            side="left", padx=(0, 6))
        boton(self._botones_proyectos, "Detalles", self._detalles).pack(
            side="left", padx=(0, 6))
        boton(self._botones_proyectos, "Registrar pago", self._registrar_pago,
              color="exito").pack(side="left", padx=(0, 6))
        boton(self._botones_proyectos, "Contrato", self._contrato).pack(
            side="left", padx=(0, 6))
        boton(self._botones_proyectos, "Eliminar", self._eliminar_proyecto,
              color="peligro").pack(side="left", padx=(0, 6))

        self._botones_clientes = ctk.CTkFrame(barra, fg_color="transparent")
        boton(self._botones_clientes, "Nuevo cliente", self._nuevo_cliente).pack(
            side="left", padx=(0, 6))
        boton(self._botones_clientes, "Editar", self._editar_cliente).pack(
            side="left", padx=(0, 6))
        boton(self._botones_clientes, "Eliminar", self._eliminar_cliente,
              color="peligro").pack(side="left", padx=(0, 6))

        self._busqueda = ctk.CTkEntry(barra, width=250,
                                      placeholder_text="Buscar proyecto o cliente…")
        self._busqueda.pack(side="right")
        self._busqueda.bind("<KeyRelease>", self.refrescar_diferido)

        # -- pestañas internas --------------------------------------------- #
        self._panel_proyectos = ctk.CTkFrame(contenedor, fg_color="transparent")
        self._panel_clientes = ctk.CTkFrame(contenedor, fg_color="transparent")

        columnas_p = [
            {"clave": "titulo", "titulo": "Proyecto", "ancho": 200},
            {"clave": "tipo", "titulo": "Tipo", "ancho": 105},
            {"clave": "cliente", "titulo": "Cliente", "ancho": 150},
            {"clave": "fecha", "titulo": "Evento", "ancho": 100, "anchor": "center"},
            {"clave": "estado", "titulo": "Estado", "ancho": 105, "anchor": "center"},
            {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 130},
            {"clave": "cobro", "titulo": "Cobro total", "ancho": 120, "anchor": "e"},
            {"clave": "sena", "titulo": "Seña", "ancho": 110, "anchor": "e"},
            {"clave": "pagos", "titulo": "Pagos", "ancho": 110, "anchor": "e"},
            {"clave": "saldo", "titulo": "Saldo", "ancho": 120, "anchor": "e"},
        ]
        self.tabla = Tabla(self._panel_proyectos, columnas_p,
                           doble_click=lambda _e: self._detalles(), altura=4)
        self.tabla.grid(row=0, column=0, sticky="nsew")
        self._panel_proyectos.grid_rowconfigure(0, weight=1)
        self._panel_proyectos.grid_columnconfigure(0, weight=1)

        columnas_c = [
            {"clave": "nombre", "titulo": "Cliente", "ancho": 200},
            {"clave": "responsable", "titulo": "Responsable", "ancho": 180},
            {"clave": "telefono", "titulo": "Celular / Teléfono", "ancho": 160},
            {"clave": "email", "titulo": "Email", "ancho": 200},
            {"clave": "direccion", "titulo": "Dirección / locación", "ancho": 260},
        ]
        self.tabla_clientes = Tabla(self._panel_clientes, columnas_c,
                                    doble_click=lambda _e: self._editar_cliente(),
                                    altura=4)
        self.tabla_clientes.grid(row=0, column=0, sticky="nsew")
        self._panel_clientes.grid_rowconfigure(0, weight=1)
        self._panel_clientes.grid_columnconfigure(0, weight=1)

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self._mostrar_modo()

    # -- pestañas ---------------------------------------------------------- #
    def _mostrar_modo(self) -> None:
        proyectos = self._modo.get() == "Proyectos"
        self._botones_proyectos.pack_forget()
        self._botones_clientes.pack_forget()
        (self._botones_proyectos if proyectos else self._botones_clientes).pack(
            side="left")
        if proyectos:
            self._panel_clientes.grid_remove()
            self._panel_proyectos.grid(row=1, column=0, sticky="nsew")
        else:
            self._panel_proyectos.grid_remove()
            self._panel_clientes.grid(row=1, column=0, sticky="nsew")
        self.refrescar()

    # -- datos ------------------------------------------------------------- #
    def refrescar(self) -> None:
        texto = self._busqueda.get().strip().lower()
        if self._modo.get() == "Proyectos":
            self._refrescar_proyectos(texto)
        else:
            self._refrescar_clientes(texto)

    def _refrescar_proyectos(self, texto: str) -> None:
        proyectos = self.repos.proyectos.listar()
        filas, objetos, etiquetas = [], [], []
        saldo_total = 0.0
        for p in proyectos:
            referencia = f"{p.titulo} {p.cliente} {p.tipo}".lower()
            if texto and texto not in referencia:
                continue
            saldo = p.obtener_saldo_pendiente()
            saldo_total += max(saldo, 0)
            filas.append([
                p.titulo or "—",
                p.tipo or "—",
                p.cliente,
                p.fecha_evento.strftime("%d/%m/%Y") if p.fecha_evento else "—",
                str(p.estado),
                p.fotografo.nombre_completo if p.fotografo else "—",
                moneda(p.cobro_total),
                moneda(p.sena),
                moneda(p.total_pagos_parciales),
                moneda(saldo),
            ])
            objetos.append(p)
            etiquetas.append("ok" if saldo <= 0 else "proximo")
        self.tabla.actualizar(filas, objetos, etiquetas)
        abiertos = [p for p in proyectos if str(p.estado) != "Cerrado"]
        self._pie.configure(
            text=f"{len(proyectos)} proyecto(s) · {len(abiertos)} activo(s) · "
            f"saldo a cobrar {moneda(saldo_total)}"
        )

    def _refrescar_clientes(self, texto: str) -> None:
        clientes = self.repos.clientes.listar()
        filas, objetos = [], []
        for c in clientes:
            if texto and texto not in f"{c.nombre} {c.responsable}".lower():
                continue
            filas.append([c.nombre, c.responsable or "—", c.telefono or "—",
                          c.email or "—", c.direccion or "—"])
            objetos.append(c)
        self.tabla_clientes.actualizar(filas, objetos)
        self._pie.configure(text=f"{len(clientes)} cliente(s) en la base.")

    # -- proyectos --------------------------------------------------------- #
    def _seleccion_proyecto(self):
        proyecto = self.tabla.seleccionado()
        if proyecto is None:
            self.advertir("Sin selección", "Elija un proyecto en la tabla.")
        return proyecto

    def _nuevo_proyecto(self) -> None:
        clientes = self.repos.clientes.listar()
        if not clientes:
            self.advertir("Sin clientes",
                          "Primero registre un cliente en la pestaña Clientes.")
            return
        proyecto = DialogoProyecto(self, clientes, self.repos.fotografos.listar(),
                                   tipos=self.repos.proyectos.tipos()).mostrar()
        if proyecto is None:
            return
        self.ejecutar(lambda: self.repos.proyectos.crear(proyecto))

    def _editar_proyecto(self) -> None:
        proyecto = self._seleccion_proyecto()
        if proyecto is None:
            return
        editado = DialogoProyecto(
            self, self.repos.clientes.listar(), self.repos.fotografos.listar(), proyecto,
            tipos=self.repos.proyectos.tipos(),
        ).mostrar()
        if editado is None:
            return
        self.ejecutar(lambda: self.repos.proyectos.actualizar(editado))

    def _detalles(self) -> None:
        proyecto = self._seleccion_proyecto()
        if proyecto is None:
            return
        completo = self.repos.proyectos.obtener(proyecto.id)
        DialogoDetalleProyecto(self, completo or proyecto).mostrar()

    def _registrar_pago(self) -> None:
        proyecto = self._seleccion_proyecto()
        if proyecto is None:
            return
        if proyecto.obtener_saldo_pendiente() <= 0:
            self.advertir("Proyecto saldado",
                          "Lo abonado ya cubre el cobro total: no admite más pagos.")
            return
        datos = DialogoPago(self, proyecto).mostrar()
        if datos is None:
            return
        self.ejecutar(lambda: self.repos.proyectos.crear_pago(
            proyecto.id, datos["monto"], datos["fecha"], datos["medio"],
            datos["notas"]))

    def _contrato(self) -> None:
        proyecto = self._seleccion_proyecto()
        if proyecto is None:
            return
        contrato = DialogoContrato(
            self, self.repos.proyectos.listar(), self.repos.plantillas.listar(),
            estudio=self.repos.nombre_estudio,
        ).mostrar()
        if contrato is None:
            return
        contrato.proyecto_id = proyecto.id
        contrato.nombre = contrato.nombre or f"Contrato {proyecto.nombre}"
        self.ejecutar(lambda: self.repos.contratos.crear(contrato))

    def _eliminar_proyecto(self) -> None:
        proyecto = self._seleccion_proyecto()
        if proyecto is None:
            return
        if not self.confirmar("Eliminar proyecto",
                              f"¿Eliminar «{proyecto.nombre}» y sus pagos asociados?"):
            return
        self.ejecutar(lambda: self.repos.proyectos.eliminar(proyecto.id))

    # -- clientes ---------------------------------------------------------- #
    def _seleccion_cliente(self):
        cliente = self.tabla_clientes.seleccionado()
        if cliente is None:
            self.advertir("Sin selección", "Elija un cliente en la tabla.")
        return cliente

    def _nuevo_cliente(self) -> None:
        cliente = DialogoCliente(self).mostrar()
        if cliente is None:
            return
        self.ejecutar(lambda: self.repos.clientes.crear(cliente))

    def _editar_cliente(self) -> None:
        cliente = self._seleccion_cliente()
        if cliente is None:
            return
        editado = DialogoCliente(self, cliente).mostrar()
        if editado is None:
            return
        self.ejecutar(lambda: self.repos.clientes.actualizar(editado))

    def _eliminar_cliente(self) -> None:
        cliente = self._seleccion_cliente()
        if cliente is None:
            return
        if not self.confirmar("Eliminar cliente",
                              f"¿Dar de baja a {cliente.nombre}?\n"
                              "Si tiene proyectos asociados el sistema lo impedirá."):
            return
        self.ejecutar(lambda: self.repos.clientes.eliminar(cliente.id))
