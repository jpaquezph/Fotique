"""Acceso — administración de usuarios (sólo administradores)."""

from __future__ import annotations

import customtkinter as ctk

from ..dialogs import DialogoSecreto, DialogoUsuario
from ..theme import GRIS_TEXTO
from ..widgets import Tabla, boton
from .base import VistaBase


class VistaUsuarios(VistaBase):
    clave = "usuarios"
    titulo = "Usuarios"
    descripcion = "Cuentas que pueden ingresar a Fotique, roles y contraseñas"
    solo_admin = True

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        boton(barra, "Nuevo usuario", self._nuevo).pack(side="left", padx=(0, 6))
        boton(barra, "Editar", self._editar).pack(side="left", padx=(0, 6))
        boton(barra, "Restablecer contraseña", self._restablecer, color="aviso",
              ancho=180).pack(side="left", padx=(0, 6))
        boton(barra, "Eliminar", self._eliminar, color="peligro").pack(
            side="left", padx=(0, 6))

        columnas = [
            {"clave": "usuario", "titulo": "Usuario", "ancho": 160},
            {"clave": "nombre", "titulo": "Nombre y apellido", "ancho": 220},
            {"clave": "email", "titulo": "Email", "ancho": 230},
            {"clave": "rol", "titulo": "Rol", "ancho": 130, "anchor": "center"},
            {"clave": "estado", "titulo": "Estado", "ancho": 100, "anchor": "center"},
            {"clave": "acceso", "titulo": "Último acceso", "ancho": 150, "anchor": "center"},
        ]
        self.tabla = Tabla(contenedor, columnas, doble_click=lambda _e: self._editar(),
                           altura=4)
        self.tabla.grid(row=1, column=0, sticky="nsew")

        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def refrescar(self) -> None:
        usuarios = self.repos.usuarios.listar()
        filas, etiquetas = [], []
        for u in usuarios:
            filas.append([
                u.usuario,
                u.nombre or "—",
                u.email or "—",
                str(u.rol),
                "Activo" if u.activo else "Inactivo",
                u.ultimo_acceso.strftime("%d/%m/%Y %H:%M") if u.ultimo_acceso else "Nunca",
            ])
            etiquetas.append("" if u.activo else "entregado")
        self.tabla.actualizar(filas, usuarios, etiquetas)
        activos = sum(1 for u in usuarios if u.activo)
        admins = sum(1 for u in usuarios if u.activo and u.es_admin)
        self._pie.configure(
            text=f"{len(usuarios)} usuario(s) · {activos} activo(s) · "
            f"{admins} administrador(es)"
        )

    # -- acciones ---------------------------------------------------------- #
    def _seleccion(self):
        usuario = self.tabla.seleccionado()
        if usuario is None:
            self.advertir("Sin selección", "Elija un usuario en la tabla.")
        return usuario

    def _es_propio(self, usuario) -> bool:
        actual = self.app.usuario
        return actual is not None and actual.id == usuario.id

    def _nuevo(self) -> None:
        datos = DialogoUsuario(self).mostrar()
        if datos is None:
            return
        usuario, password = datos
        codigo = self.ejecutar(lambda: self.repos.usuarios.crear(usuario, password))
        if codigo:
            DialogoSecreto(
                self, "Código de recuperación",
                f"Entregue este código a {usuario.nombre_visible}: es la forma de "
                "recuperar la cuenta si olvida la contraseña. Se muestra una sola vez.",
                codigo,
            ).mostrar()

    def _editar(self) -> None:
        usuario = self._seleccion()
        if usuario is None:
            return
        editado = DialogoUsuario(self, usuario).mostrar()
        if editado is None:
            return
        if self._es_propio(usuario) and not (editado.activo and editado.es_admin):
            self.advertir("Cuenta propia",
                          "No puede desactivar ni quitarle el rol de administrador a "
                          "la cuenta con la que está trabajando.")
            return
        if self.ejecutar(lambda: self.repos.usuarios.actualizar(editado)) is None:
            return
        if self._es_propio(usuario):
            self.app.ventana.actualizar_sesion(editado)

    def _restablecer(self) -> None:
        usuario = self._seleccion()
        if usuario is None:
            return
        if self._es_propio(usuario):
            self.advertir("Cuenta propia",
                          "Para su propia contraseña use «Mi cuenta ▸ Cambiar contraseña».")
            return
        if not self.confirmar(
            "Restablecer contraseña",
            f"Se generará una contraseña provisoria para {usuario.nombre_visible}.\n"
            "La actual dejará de funcionar.",
            texto_si="Restablecer",
        ):
            return
        temporal = self.ejecutar(
            lambda: self.repos.usuarios.restablecer_por_admin(usuario.id))
        if temporal:
            DialogoSecreto(
                self, "Contraseña provisoria",
                f"Entréguesela a {usuario.nombre_visible}. Al ingresar se le pedirá "
                "que elija una contraseña nueva.",
                temporal,
            ).mostrar()

    def _eliminar(self) -> None:
        usuario = self._seleccion()
        if usuario is None:
            return
        if self._es_propio(usuario):
            self.advertir("Cuenta propia",
                          "No puede eliminar la cuenta con la que está trabajando.")
            return
        if not self.confirmar("Eliminar usuario",
                              f"¿Eliminar la cuenta «{usuario.usuario}»?"):
            return
        self.ejecutar(lambda: self.repos.usuarios.eliminar(usuario.id))


__all__ = ["VistaUsuarios"]
