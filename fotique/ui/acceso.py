"""Pantalla de acceso: primer usuario, ingreso y recuperación de contraseña."""

from __future__ import annotations

from typing import Any, Callable, Optional

import customtkinter as ctk

from ..domain.errors import DatosInvalidosError, FotiqueError
from ..domain.models import RolUsuario, Usuario
from .theme import (
    ACENTO,
    BORDE,
    FONDO,
    FUENTE_NORMAL,
    FUENTE_PEQUE,
    FUENTE_SUBTITULO,
    GRIS_TEXTO,
    LATERAL,
    RESALTE,
    ROJO,
    TEXTO,
)
from .logo import Logo
from .widgets import boton, boton_secundario

OCULTO = "•"


class PantallaAcceso(ctk.CTkFrame):
    """Ocupa la ventana hasta que alguien ingresa; avisa con ``al_ingresar(usuario)``."""

    def __init__(self, master: Any, app: Any, al_ingresar: Callable[[Usuario], None]):
        super().__init__(master, fg_color=LATERAL, corner_radius=0)
        self.app = app
        self._al_ingresar = al_ingresar
        self._campos: dict[str, ctk.CTkEntry] = {}
        self._aceptar: Optional[Callable[[], None]] = None

        self._tarjeta = ctk.CTkFrame(self, width=420, fg_color=FONDO, corner_radius=18,
                                     border_width=1, border_color=BORDE)
        self._tarjeta.place(relx=0.5, rely=0.5, anchor="center")
        # Enter en cualquier campo envía el formulario: se enlaza en la ventana.
        self._ventana = self.winfo_toplevel()
        self._enlace_enter = self._ventana.bind("<Return>", self._al_enter, add="+")

        if self.app.repos.usuarios.hay_usuarios():
            self.mostrar_ingreso()
        else:
            self.mostrar_primer_usuario()

    def destroy(self) -> None:
        self._ventana.unbind("<Return>", self._enlace_enter)
        super().destroy()

    def _al_enter(self, _evento=None) -> None:
        if self._aceptar is not None:
            self._aceptar()

    # -- armado de formularios --------------------------------------------- #
    def _reiniciar(self, titulo: str, subtitulo: str) -> None:
        for hijo in self._tarjeta.winfo_children():
            hijo.destroy()
        self._campos = {}
        self._aceptar = None
        Logo(self._tarjeta, FONDO).pack(padx=40, pady=(22, 0))
        ctk.CTkLabel(self._tarjeta, text=titulo, font=FUENTE_SUBTITULO,
                     text_color=TEXTO).pack(padx=40, pady=(8, 0))
        ctk.CTkLabel(self._tarjeta, text=subtitulo, font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, wraplength=340, justify="center").pack(
            padx=40, pady=(2, 12))

    def _campo(self, clave: str, etiqueta: str, *, oculto: bool = False,
               valor: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(self._tarjeta, text=etiqueta, font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, anchor="w").pack(fill="x", padx=40)
        entrada = ctk.CTkEntry(self._tarjeta, width=340, height=32, font=FUENTE_NORMAL,
                               show=OCULTO if oculto else "")
        entrada.insert(0, valor)
        entrada.pack(padx=40, pady=(0, 6))
        self._campos[clave] = entrada
        return entrada

    def _ver_passwords(self, *claves: str) -> None:
        ver = ctk.BooleanVar(value=False)

        def alternar() -> None:
            for clave in claves:
                self._campos[clave].configure(show="" if ver.get() else OCULTO)

        ctk.CTkCheckBox(self._tarjeta, text="Mostrar contraseña", variable=ver,
                        command=alternar, font=FUENTE_PEQUE, checkbox_width=18,
                        checkbox_height=18).pack(anchor="w", padx=40, pady=(0, 6))

    def _cierre(self, texto_ok: str, accion: Callable[[], None], *,
                enlace: Optional[tuple[str, Callable[[], None]]] = None) -> None:
        self._mensaje = ctk.CTkLabel(self._tarjeta, text="", font=FUENTE_PEQUE,
                                     text_color=ROJO, wraplength=340, justify="left",
                                     anchor="w")
        self._mensaje.pack(fill="x", padx=40)
        boton(self._tarjeta, texto_ok, accion, ancho=340, alto=36, solido=True).pack(
            padx=40, pady=(6, 8 if enlace else 26))
        if enlace:
            ctk.CTkButton(self._tarjeta, text=enlace[0], command=enlace[1],
                          fg_color="transparent", hover_color=RESALTE,
                          text_color=ACENTO, font=FUENTE_PEQUE, height=26).pack(
                pady=(0, 20))
        self._accion = accion
        self._aceptar = accion
        primero = next(iter(self._campos.values()), None)
        if primero is not None:
            self.after(60, primero.focus_set)

    def _valor(self, clave: str) -> str:
        return self._campos[clave].get()

    def _intentar(self, accion: Callable[[], None]) -> None:
        """Ejecuta la acción del formulario y muestra el error de negocio debajo."""
        try:
            accion()
        except FotiqueError as exc:
            self._mensaje.configure(text=str(exc))

    def _passwords_iguales(self) -> str:
        nueva = self._valor("password")
        if nueva != self._valor("repetir"):
            raise DatosInvalidosError("Las contraseñas no coinciden.")
        return nueva

    # -- primer usuario ----------------------------------------------------- #
    def mostrar_primer_usuario(self) -> None:
        self._reiniciar("Crear la cuenta de administrador",
                        "Es la primera vez que se abre esta base de datos. "
                        "Esta cuenta podrá crear al resto de los usuarios.")
        self._campo("nombre", "Nombre y apellido")
        self._campo("usuario", "Usuario")
        self._campo("email", "Email (opcional)")
        self._campo("password", "Contraseña (mínimo 8, con letras y números)", oculto=True)
        self._campo("repetir", "Repetir contraseña", oculto=True)
        self._ver_passwords("password", "repetir")
        self._cierre("Crear cuenta e ingresar", lambda: self._intentar(self._crear_admin))

    def _crear_admin(self) -> None:
        password = self._passwords_iguales()
        usuario = Usuario(usuario=self._valor("usuario").strip(),
                          nombre=self._valor("nombre").strip(),
                          email=self._valor("email").strip(),
                          rol=RolUsuario.ADMINISTRADOR)
        repo = self.app.repos.usuarios
        codigo = repo.crear(usuario, password)
        self._mostrar_codigo(codigo, lambda: self._al_ingresar(
            repo.autenticar(usuario.usuario, password)))

    # -- ingreso ------------------------------------------------------------ #
    def mostrar_ingreso(self, usuario: str = "", aviso: str = "") -> None:
        self._reiniciar("Iniciar sesión", "Ingrese con su usuario y contraseña.")
        self._campo("usuario", "Usuario", valor=usuario)
        self._campo("password", "Contraseña", oculto=True)
        self._ver_passwords("password")
        self._cierre("Ingresar", lambda: self._intentar(self._ingresar),
                     enlace=("¿Olvidó su contraseña?", self.mostrar_recuperacion))
        if aviso:
            self._mensaje.configure(text=aviso, text_color=GRIS_TEXTO)
        if usuario:
            self.after(80, self._campos["password"].focus_set)

    def _ingresar(self) -> None:
        self._mensaje.configure(text_color=ROJO)
        usuario = self.app.repos.usuarios.autenticar(
            self._valor("usuario"), self._valor("password"))
        if usuario.debe_cambiar_password:
            self.mostrar_cambio_obligatorio(usuario)
        else:
            self._al_ingresar(usuario)

    # -- cambio obligatorio (tras un restablecimiento del administrador) ----- #
    def mostrar_cambio_obligatorio(self, usuario: Usuario) -> None:
        self._reiniciar("Elija una contraseña nueva",
                        "Ingresó con una contraseña provisoria. "
                        "Debe reemplazarla para continuar.")
        self._campo("password", "Nueva contraseña", oculto=True)
        self._campo("repetir", "Repetir contraseña", oculto=True)
        self._ver_passwords("password", "repetir")

        def guardar() -> None:
            self.app.repos.usuarios.definir_password(usuario.id, self._passwords_iguales())
            usuario.debe_cambiar_password = False
            self._al_ingresar(usuario)

        self._cierre("Guardar e ingresar", lambda: self._intentar(guardar))

    # -- recuperación ------------------------------------------------------- #
    def mostrar_recuperacion(self) -> None:
        self._reiniciar("Recuperar la contraseña",
                        "Use el código de recuperación que se le entregó al crear la "
                        "cuenta. Si no lo tiene, un administrador puede restablecerle "
                        "la contraseña desde «Usuarios».")
        self._campo("usuario", "Usuario")
        self._campo("codigo", "Código de recuperación (XXXX-XXXX-XXXX-XXXX)")
        self._campo("password", "Nueva contraseña", oculto=True)
        self._campo("repetir", "Repetir contraseña", oculto=True)
        self._ver_passwords("password", "repetir")
        self._cierre("Restablecer contraseña", lambda: self._intentar(self._recuperar),
                     enlace=("Volver al inicio de sesión", self.mostrar_ingreso))

    def _recuperar(self) -> None:
        password = self._passwords_iguales()
        usuario = self._valor("usuario").strip()
        codigo = self.app.repos.usuarios.restablecer_con_codigo(
            usuario, self._valor("codigo"), password)
        self._mostrar_codigo(codigo, lambda: self.mostrar_ingreso(
            usuario, "Contraseña restablecida. Ingrese con la nueva."))

    # -- código de recuperación --------------------------------------------- #
    def _mostrar_codigo(self, codigo: str, continuar: Callable[[], None]) -> None:
        self._reiniciar("Guarde su código de recuperación",
                        "Es la única forma de recuperar la cuenta si olvida la "
                        "contraseña. Se muestra una sola vez y sirve para un único "
                        "uso: anótelo y guárdelo en un lugar seguro.")
        entrada = ctk.CTkEntry(self._tarjeta, width=340, height=42, justify="center",
                               font=("Consolas", 16, "bold"))
        entrada.insert(0, codigo)
        entrada.configure(state="readonly")
        entrada.pack(padx=40, pady=(0, 8))

        def copiar() -> None:
            self.clipboard_clear()
            self.clipboard_append(codigo)
            copia.configure(text="Copiado")

        copia = boton_secundario(self._tarjeta, "Copiar al portapapeles", copiar,
                                 ancho=340)
        copia.pack(padx=40, pady=(0, 8))
        self._cierre("Ya lo guardé, continuar", continuar)
        self._aceptar = None  # un Enter repetido no debe saltear esta pantalla
