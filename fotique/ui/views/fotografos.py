"""Módulo B — Gestión de fotógrafos / personal."""

from __future__ import annotations

import customtkinter as ctk

from ...domain.models import Fotografo
from ..dialogs import (
    DialogoFichaFotografo,
    DialogoFotografo,
    DialogoHistorialEntregas,
    DialogoSecreto,
    DialogoTrabajo,
)
from ..theme import GRIS_TEXTO
from ..widgets import Tabla, boton, boton_secundario
from .base import VistaBase


class VistaFotografos(VistaBase):
    clave = "fotografos"
    titulo = "Fotógrafos y personal"
    descripcion = "Personal del estudio: equipos tomados, trabajos e historial de entregas"

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
        boton(barra, "Nuevo trabajo", self._nuevo_trabajo, color="exito").pack(
            side="left", padx=(0, 6)
        )
        boton(barra, "Historial", self._historial).pack(side="left", padx=(0, 6))
        boton(barra, "Eliminar", self._eliminar, color="peligro").pack(side="left", padx=(0, 6))

        self._busqueda = ctk.CTkEntry(barra, width=250,
                                      placeholder_text="Buscar nombre, teléfono o email…")
        self._busqueda.pack(side="right")
        self._busqueda.bind("<KeyRelease>", self.refrescar_diferido)

        columnas = [
            {"clave": "nombre", "titulo": "Nombre y apellido", "ancho": 210},
            {"clave": "telefono", "titulo": "Teléfono", "ancho": 150},
            {"clave": "email", "titulo": "Email", "ancho": 200},
            {"clave": "equipos", "titulo": "Equipos", "ancho": 80, "anchor": "center"},
            {"clave": "activas", "titulo": "Entregas activas", "ancho": 110, "anchor": "center"},
            {"clave": "proxima", "titulo": "Próxima entrega", "ancho": 125, "anchor": "center"},
            {"clave": "rol", "titulo": "Rol en el sistema", "ancho": 130, "anchor": "center"},
        ]
        self.tabla = Tabla(contenedor, columnas, doble_click=lambda _e: self._ficha(),
                           altura=4)
        self.tabla.grid(row=1, column=0, sticky="nsew")

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def refrescar(self) -> None:
        texto = self._busqueda.get().strip().lower()
        resumenes = self.repos.fotografos.listar_resumen()
        filas, objetos = [], []
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
                r["rol"] or "Sin cuenta",
            ])
            objetos.append(f)
        self.tabla.actualizar(filas, objetos)
        pendientes = sum(r["n_activos"] for r in resumenes)
        self._pie.configure(
            text=f"{len(objetos)} fotógrafo(s) · {pendientes} entrega(s) en curso"
        )

    # -- acciones ---------------------------------------------------------- #
    def _seleccion(self):
        fotografo = self.tabla.seleccionado()
        if fotografo is None:
            self.advertir("Sin selección", "Elija un fotógrafo en la tabla.")
        return fotografo

    def _nuevo(self) -> None:
        # El rol (y con él la cuenta de acceso) sólo lo define un administrador.
        con_cuenta = self.app.usuario is not None and self.app.es_admin
        dialogo = DialogoFotografo(self, elegir_rol=con_cuenta)
        fotografo = dialogo.mostrar()
        if fotografo is None:
            return
        if self.ejecutar(lambda: self.repos.fotografos.crear(fotografo)) is None:
            return
        if dialogo.rol is None:
            return
        cuenta = self.ejecutar(
            lambda: self.repos.usuarios.crear_para_fotografo(fotografo, dialogo.rol))
        if cuenta:
            usuario, temporal = cuenta
            DialogoSecreto(
                self, f"Cuenta de {fotografo.nombre_completo}",
                f"Usuario: {usuario.usuario} · Rol: {usuario.rol}. Entréguele esta "
                "contraseña provisoria; al ingresar deberá elegir una propia.",
                temporal,
            ).mostrar()

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
            roles=self.repos.trabajos.roles(),
        ).mostrar()
        if trabajo is None:
            return
        self.ejecutar(lambda: self.repos.trabajos.crear(trabajo))

    def _historial(self) -> None:
        """Entregas del fotógrafo elegido (o de todos): activas, cerradas y canceladas."""
        fotografo = self.tabla.seleccionado()
        fotografo_id = fotografo.id if fotografo else None
        DialogoHistorialEntregas(
            self,
            "Historial de entregas" + (
                f" — {fotografo.nombre_completo}" if fotografo else ""),
            lambda: self.repos.trabajos.listar(fotografo_id=fotografo_id),
            lambda trabajo, estado: self.repos.trabajos.cambiar_estado(trabajo.id, estado),
        ).mostrar()
        self.refrescar()

    def _eliminar(self) -> None:
        fotografo = self._seleccion()
        if fotografo is None:
            return
        if not self.confirmar(
            "Eliminar fotógrafo",
            f"¿Dar de baja a {fotografo.nombre_completo}?\n"
            "Si tiene equipos o entregas activas el sistema lo impedirá.",
        ):
            return
        self.ejecutar(lambda: self.repos.fotografos.eliminar(fotografo.id))
