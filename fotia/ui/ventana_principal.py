"""Ventana principal de Fotia: acceso, navegación lateral, menús y apariencia."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable, Iterator, Optional

import customtkinter as ctk
from tkinter import Menu

from . import views
from .acceso import PantallaAcceso
from .theme import (
    BORDE,
    BOTONES,
    FONDO,
    FUENTE_PEQUE,
    FUENTE_SUBTITULO,
    GRIS_TEXTO,
    RESALTE,
    TEMAS,
    TEXTO,
    TEXTO_BOTON,
    aplicar_estilo_tabla,
    area_de_trabajo,
    configurar_apariencia,
)
from .widgets import boton_secundario

MENU_NAVEGACION = [
    ("panel", "Panel de control"),
    ("equipos", "Inventario de equipos"),
    ("fotografos", "Fotógrafos"),
    ("proyectos", "Clientes y proyectos"),
    ("calendario", "Calendario"),
    ("servicios", "Tarifario"),
    ("contratos", "Contratos"),
    ("respaldos", "Respaldo y datos"),
    ("resumen", "Resumen general"),
    ("usuarios", "Usuarios"),
]

VERSION = "1.2.0"


class _Vistas(Mapping):
    """Vistas por clave, construidas recién la primera vez que se piden.

    Armar las nueve pantallas al arrancar era la mayor parte del tiempo de
    inicio; así sólo se paga por las que el usuario abre.
    """

    def __init__(self, clases: list[type], crear: Callable[[type], Any]):
        self._clases = {clase.clave: clase for clase in clases}
        self._crear = crear
        self._hechas: dict[str, Any] = {}

    def __getitem__(self, clave: str):
        if clave not in self._hechas:
            self._hechas[clave] = self._crear(self._clases[clave])
        return self._hechas[clave]

    def construida(self, clave: str) -> bool:
        return clave in self._hechas

    def __iter__(self) -> Iterator[str]:
        return iter(self._clases)

    def __len__(self) -> int:
        return len(self._clases)


class VentanaPrincipal(ctk.CTk):
    def __init__(self, app: Any, *, acceso: bool = False):
        """``acceso=True`` exige iniciar sesión antes de mostrar la aplicación."""
        super().__init__()
        self.app = app
        self.title("Fotia — Gestión integral de estudio fotográfico")
        # El tamaño inicial no supera la pantalla: si no, el pie de la barra
        # lateral (sesión y apariencia) queda fuera de la vista.
        escala = self._get_window_scaling()
        x0, y0, ancho_area, alto_area = area_de_trabajo(self)
        ancho = int(min(1360, ancho_area / escala - 20))
        alto = int(min(860, alto_area / escala - 64))  # barra de título y menú
        x = x0 + int((ancho_area - ancho * escala) / 2)
        self.geometry(f"{ancho}x{alto}+{max(x0, x)}+{y0}")
        self.minsize(min(1140, ancho), min(600, alto))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        aplicar_estilo_tabla(self)

        self._acceso: Optional[PantallaAcceso] = None
        self._principal: list[ctk.CTkFrame] = []
        self._botones: dict[str, ctk.CTkButton] = {}
        self.vistas: Mapping[str, views.VistaBase] = _Vistas([], lambda clase: None)
        self.clave_activa: Optional[str] = None
        self._precarga: Optional[str] = None

        self.protocol("WM_DELETE_WINDOW", self._salir)
        if acceso:
            self._mostrar_acceso()
        else:
            self._construir_principal()

    # -- sesión -------------------------------------------------------------- #
    def _mostrar_acceso(self) -> None:
        self.config(menu=Menu(self, tearoff=0))
        self._acceso = PantallaAcceso(self, self.app, self._al_ingresar)
        self._acceso.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def _al_ingresar(self, usuario: Any) -> None:
        self.app.usuario = usuario
        if self._acceso is not None:
            self._acceso.destroy()
            self._acceso = None
        self._construir_principal()

    def cerrar_sesion(self) -> None:
        for marco in self._principal:
            marco.destroy()
        self._principal = []
        self._botones = {}
        self.vistas = _Vistas([], lambda clase: None)
        self.clave_activa = None
        self.app.usuario = None
        self._mostrar_acceso()

    def validar_sesion(self) -> None:
        """Tras restaurar un respaldo la cuenta en uso puede no existir más."""
        actual = self.app.usuario
        if actual is None:
            return
        vigente = self.app.repos.usuarios.por_nombre(actual.usuario)
        if vigente is None or not vigente.activo:
            self.cerrar_sesion()
        else:
            self.actualizar_sesion(vigente)

    def actualizar_sesion(self, usuario: Any) -> None:
        self.app.usuario = usuario
        if self._principal:
            self._etiqueta_usuario.configure(text=self._texto_usuario(usuario))

    @staticmethod
    def _texto_usuario(usuario: Any) -> str:
        return f"{usuario.nombre_visible} · {usuario.rol}"

    # -- armado -------------------------------------------------------------- #
    def _construir_principal(self) -> None:
        self._crear_menu()
        usuario = self.app.usuario
        clases = [c for c in views.TODAS if self.app.es_admin or not c.solo_admin]
        permitidas = {c.clave for c in clases}

        # -- barra lateral -------------------------------------------------- #
        lateral = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=FONDO)
        lateral.grid(row=0, column=0, sticky="nsew")
        lateral.grid_propagate(False)
        ctk.CTkLabel(lateral, text="FOTIA", font=("Segoe UI", 26, "bold"),
                     text_color=TEXTO, anchor="w").pack(
            fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(lateral, text="Estudio fotográfico", font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, anchor="w").pack(
            fill="x", padx=20, pady=(0, 14))

        # El pie se ubica antes que la navegación: si la ventana es baja, lo que
        # se recorta es el final del menú y no la sesión ni la apariencia.
        pie = ctk.CTkFrame(lateral, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=14, pady=(8, 12))
        if usuario is not None:
            self._etiqueta_usuario = ctk.CTkLabel(
                pie, text=self._texto_usuario(usuario), font=FUENTE_PEQUE,
                text_color=TEXTO, anchor="w")
            self._etiqueta_usuario.pack(fill="x")
            cuenta = ctk.CTkFrame(pie, fg_color="transparent")
            cuenta.pack(fill="x", pady=(2, 10))
            boton_secundario(cuenta, "Mi cuenta", self._mi_cuenta, ancho=96,
                             alto=28).pack(side="left")
            boton_secundario(cuenta, "Cerrar sesión", self.cerrar_sesion, ancho=106,
                             alto=28).pack(side="right")
        apariencia = ctk.CTkFrame(pie, fg_color="transparent")
        apariencia.pack(fill="x")
        ctk.CTkLabel(apariencia, text="Apariencia", font=FUENTE_PEQUE,
                     text_color=GRIS_TEXTO, anchor="w").pack(side="left")
        self._tema = ctk.StringVar(value=self.app.tema)
        ctk.CTkOptionMenu(
            apariencia, values=list(TEMAS), variable=self._tema, width=124, height=26,
            font=FUENTE_PEQUE, dynamic_resizing=False, command=self._cambiar_tema,
        ).pack(side="right")
        ctk.CTkLabel(pie, text=f"Fotia {VERSION}", font=("Segoe UI", 9),
                     text_color=GRIS_TEXTO, anchor="w").pack(fill="x", pady=(4, 0))

        for clave, texto in MENU_NAVEGACION:
            if clave not in permitidas:
                continue
            btn = ctk.CTkButton(
                lateral, text=texto, anchor="w", height=32, corner_radius=8,
                font=FUENTE_SUBTITULO, fg_color="transparent",
                hover_color=RESALTE, text_color=TEXTO,
                command=lambda k=clave: self.mostrar(k),
            )
            btn.pack(fill="x", padx=14, pady=1)
            self._botones[clave] = btn

        divisor = ctk.CTkFrame(lateral, width=1, corner_radius=0, fg_color=BORDE)
        divisor.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

        # -- contenido ------------------------------------------------------- #
        contenedor = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        contenedor.grid(row=0, column=1, sticky="nsew", padx=(14, 16), pady=14)
        contenedor.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)
        self._tamano_contenido: Optional[tuple[int, int]] = None
        contenedor.bind("<Configure>", self._al_redimensionar, add="+")

        self._principal = [lateral, contenedor]
        self.vistas = _Vistas(clases, lambda clase: clase(contenedor, self.app))
        self.clave_activa = None
        self.mostrar("panel")
        self._precarga = self.after(600, self._precargar, self.vistas)

    def _precargar(self, vistas: _Vistas) -> None:
        """Arma el resto de las vistas de a una, con la ventana ya visible.

        Así el arranque no las espera y el primer clic en cada sección tampoco.
        """
        self._precarga = None
        if vistas is not self.vistas:  # se cerró la sesión mientras tanto
            return
        pendiente = next((c for c in vistas if not vistas.construida(c)), None)
        if pendiente is not None:
            vistas[pendiente]
            self._precarga = self.after(120, self._precargar, vistas)

    # -- navegación --------------------------------------------------------- #
    def _marcar_boton(self, clave: Optional[str], activo: bool) -> None:
        btn = self._botones.get(clave) if clave else None
        if btn is None:
            return
        relleno, hover = BOTONES["primario"]
        btn.configure(
            fg_color=relleno if activo else "transparent",
            text_color=TEXTO_BOTON if activo else TEXTO,
            hover_color=hover if activo else RESALTE,
        )

    def mostrar(self, clave: str) -> None:
        vista = self.vistas.get(clave)
        if vista is None:
            return
        if clave != self.clave_activa:
            self._marcar_boton(self.clave_activa, False)
            self._marcar_boton(clave, True)
            self.clave_activa = clave
        vista.refrescar()
        # Las vistas ya ubicadas quedan apiladas y se alterna con lift(), que es
        # lo más rápido; _al_redimensionar retira las que no se ven.
        if not vista.winfo_manager():
            vista.grid(row=0, column=0, sticky="nsew")
        vista.lift()

    def _al_redimensionar(self, evento: Any) -> None:
        """Al cambiar el tamaño sólo la vista activa sigue ubicada.

        Si no, cada paso del redimensionado recalcula las nueve pantallas.
        """
        tamano = (evento.width, evento.height)
        if tamano == self._tamano_contenido:
            return
        self._tamano_contenido = tamano
        for clave in self.vistas:
            if clave != self.clave_activa and self.vistas.construida(clave):
                self.vistas[clave].grid_remove()

    def refrescar_activa(self) -> None:
        if self.clave_activa is not None:
            self.vistas[self.clave_activa].refrescar()

    def refrescar_todo(self) -> None:
        """Las vistas ocultas se refrescan solas al volver a mostrarse."""
        self.refrescar_activa()

    # -- menús y apariencia -------------------------------------------------- #
    def _crear_menu(self) -> None:
        menu = Menu(self, tearoff=0)

        archivo = Menu(menu, tearoff=0)
        archivo.add_command(label="Crear respaldo…",
                            command=lambda: self.mostrar("respaldos"))
        if self.app.usuario is not None:
            archivo.add_separator()
            archivo.add_command(label="Mi cuenta…", command=self._mi_cuenta)
            archivo.add_command(label="Cerrar sesión", command=self.cerrar_sesion)
            archivo.add_separator()
        archivo.add_command(label="Salir", command=self._salir)
        menu.add_cascade(label="Archivo", menu=archivo)

        ayuda = Menu(menu, tearoff=0)
        ayuda.add_command(label="Acerca de Fotia", command=self._acerca_de)
        menu.add_cascade(label="Ayuda", menu=ayuda)
        self.config(menu=menu)

    def _set_appearance_mode(self, mode_string: str) -> None:
        # ttk no sigue a CustomTkinter: las tablas se re-estilizan en cada cambio
        # de modo, incluso cuando lo dispara el sistema operativo.
        aplicar_estilo_tabla(self)
        super()._set_appearance_mode(mode_string)

    def _cambiar_tema(self, modo: str) -> None:
        configurar_apariencia(modo)
        self.app.guardar_tema(modo)

    def _mi_cuenta(self) -> None:
        from .dialogs import (
            DialogoCambiarPassword,
            DialogoMiCuenta,
            DialogoPassword,
            DialogoSecreto,
        )
        from .widgets import DialogoMensaje, ejecutar_protegido

        usuario = self.app.usuario
        repo = self.app.repos.usuarios

        def cambiar_password(padre: Any) -> None:
            datos = DialogoCambiarPassword(padre).mostrar()
            if datos is None:
                return
            hecho = ejecutar_protegido(
                padre, lambda: repo.cambiar_password(usuario.id, *datos) or True)
            if hecho:
                DialogoMensaje.info(padre, "Contraseña cambiada",
                                    "La nueva contraseña ya está en uso.")

        def regenerar_codigo(padre: Any) -> None:
            password = DialogoPassword(
                padre, "Nuevo código de recuperación",
                "Se anulará el código anterior. Confirme con su contraseña.",
            ).mostrar()
            if password is None:
                return
            codigo = ejecutar_protegido(
                padre, lambda: repo.regenerar_codigo(usuario.id, password))
            if codigo:
                DialogoSecreto(
                    padre, "Código de recuperación",
                    "Anótelo y guárdelo en un lugar seguro: se muestra una sola vez "
                    "y reemplaza al anterior.",
                    codigo,
                ).mostrar()

        datos = DialogoMiCuenta(self, usuario, cambiar_password, regenerar_codigo).mostrar()
        if datos is None:
            return
        usuario.nombre, usuario.email = datos
        if ejecutar_protegido(self, lambda: repo.actualizar(usuario)) is not None:
            self.actualizar_sesion(usuario)
            self.refrescar_activa()

    def _acerca_de(self) -> None:
        from .widgets import DialogoMensaje

        DialogoMensaje.info(
            self, "Acerca de Fotia",
            f"Fotia {VERSION} — sistema integral de gestión fotográfica.\n"
            "Escritorio, offline-first, base de datos SQLite local.\n"
            f"Base de datos: {self.app.ruta_db}",
        )

    def _salir(self) -> None:
        if self._precarga is not None:
            self.after_cancel(self._precarga)
        self.app.cerrar()
        self.destroy()
