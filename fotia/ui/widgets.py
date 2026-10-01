"""Componentes reutilizables de la interfaz (tablas, diálogos, campos)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Optional, Sequence

import customtkinter as ctk
from tkinter import ttk

from ..domain.errors import DatosInvalidosError, FotiaError
from ..util import fecha_legible
from .theme import (
    ACENTO,
    FUENTE_NORMAL,
    FUENTE_PEQUE,
    FUENTE_SUBTITULO,
    FUENTE_TITULO,
    GRIS_TEXTO,
    ROJO,
    colores_etiquetas,
    colores_tema,
)

# --------------------------------------------------------------------------- #
# Conversiones de campos
# --------------------------------------------------------------------------- #


def parsear_fecha(texto: str) -> Optional[date]:
    """``30/09/2026`` o ``2026-09-30`` ➜ ``date`` (vacío ➜ ``None``)."""
    valor = (texto or "").strip()
    if not valor:
        return None
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    raise DatosInvalidosError(f"Fecha inválida: {valor}. Use dd/mm/aaaa.")


def parsear_monto(texto: str) -> float:
    """Soporta ``1500000``, ``1.500.000,00`` y ``1,500,000.00``."""
    valor = (texto or "").strip().replace("$", "").replace(" ", "")
    if not valor:
        return 0.0
    negativo = valor.startswith("-")
    valor = valor.lstrip("-")
    if "," in valor and "." in valor:
        if valor.rfind(",") > valor.rfind("."):
            valor = valor.replace(".", "").replace(",", ".")  # 1.500.000,00
        else:
            valor = valor.replace(",", "")  # 1,500,000.00
    elif "," in valor:
        valor = valor.replace(",", ".")
    elif "." in valor:
        partes = valor.split(".")
        if len(partes) > 2 or (len(partes[1]) == 3 and len(partes[0]) <= 3):
            valor = valor.replace(".", "")  # 1.500.000
    try:
        monto = float(valor)
    except ValueError as exc:
        raise DatosInvalidosError(f"Importe inválido: {texto}") from exc
    return -monto if negativo else monto


# --------------------------------------------------------------------------- #
# Tabla (ttk.Treeview)
# --------------------------------------------------------------------------- #


class Tabla(ctk.CTkFrame):
    """Tabla con encabezados fijos, doble clic y selección de objeto."""

    def __init__(
        self,
        master: Any,
        columnas: Sequence[dict],
        *,
        doble_click: Optional[Callable[[Any], None]] = None,
        altura: int = 12,
    ):
        super().__init__(master, fg_color="transparent")
        self.columnas = list(columnas)
        self._objetos: dict[str, Any] = {}
        self._doble_click = doble_click

        claves = [c["clave"] for c in self.columnas]
        self.tree = ttk.Treeview(
            self,
            columns=claves,
            show="headings",
            selectmode="browse",
            height=altura,
            style="Fotia.Treeview",
        )
        for col in self.columnas:
            self.tree.heading(col["clave"], text=col["titulo"])
            self.tree.column(
                col["clave"],
                width=col.get("ancho", 120),
                minwidth=col.get("min", 60),
                anchor=col.get("anchor", "w"),
                stretch=col.get("stretch", True),
            )
        for nombre, color in colores_etiquetas().items():
            self.tree.tag_configure(nombre, foreground=color)
        self.tree.tag_configure("alerta", foreground=ROJO)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview,
                            style="Fotia.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview,
                            style="Fotia.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._al_doble_clic)
        self.tree.bind("<Return>", self._al_doble_clic)

    # -- datos ------------------------------------------------------------ #
    def actualizar(
        self,
        filas: Sequence[Sequence[str]],
        objetos: Sequence[Any],
        etiquetas: Optional[Sequence[str]] = None,
    ) -> None:
        seleccion = self.id_seleccionado()
        self.tree.delete(*self.tree.get_children())
        self._objetos.clear()
        for i, valores in enumerate(filas):
            iid = str(self.tree.insert("", "end", values=list(valores)))
            self._objetos[iid] = objetos[i]
            if etiquetas and i < len(etiquetas) and etiquetas[i]:
                self.tree.item(iid, tags=(etiquetas[i],))
        if seleccion and seleccion in self._objetos:
            self.tree.selection_set(seleccion)

    def limpiar(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._objetos.clear()

    # -- selección -------------------------------------------------------- #
    def id_seleccionado(self) -> Optional[str]:
        seleccion = self.tree.selection()
        return seleccion[0] if seleccion else None

    def seleccionado(self) -> Any:
        iid = self.id_seleccionado()
        return self._objetos.get(iid) if iid else None

    def seleccionados(self) -> list[Any]:
        return [self._objetos[i] for i in self.tree.selection() if i in self._objetos]

    def vacio(self) -> bool:
        return not self.tree.get_children()

    def enfocar_primero(self) -> None:
        hijos = self.tree.get_children()
        if hijos:
            self.tree.selection_set(hijos[0])
            self.tree.focus(hijos[0])

    def _al_doble_clic(self, _evento=None) -> None:
        if self._doble_click is None:
            return
        objeto = self.seleccionado()
        if objeto is not None:
            self._doble_click(objeto)


# --------------------------------------------------------------------------- #
# Botones, tarjetas y barras
# --------------------------------------------------------------------------- #


def boton(
    master: Any,
    texto: str,
    comando: Optional[Callable[[], Any]],
    *,
    color: str = ACENTO,
    ancho: int = 118,
    alto: int = 32,
    estado: str = "normal",
) -> ctk.CTkButton:
    return ctk.CTkButton(
        master, text=texto, command=comando, width=ancho, height=alto,
        fg_color=color, hover_color=_hover(color), font=FUENTE_NORMAL, state=estado,
    )


def _hover(color: str) -> str:
    return {
        ACENTO: "#36719f",
        ROJO: "#c93c41",
        "transparent": "#d0d0d4",
    }.get(color, color)


def boton_secundario(master: Any, texto: str, comando: Optional[Callable[[], Any]],
                     **kwargs) -> ctk.CTkButton:
    kwargs.setdefault("color", "transparent")
    btn = boton(master, texto, comando, **kwargs)
    btn.configure(fg_color="transparent", border_width=1,
                  border_color=colores_tema()["texto_suave"],
                  hover_color=colores_tema()["borde"],
                  text_color=colores_tema()["texto"])
    return btn


class Tarjeta(ctk.CTkFrame):
    """Tarjeta de resumen con número grande y leyenda."""

    def __init__(self, master: Any, titulo: str, valor: Any = "0",
                 *, color: Optional[str] = None):
        super().__init__(master, corner_radius=10, height=96)
        self.grid_propagate(False)
        self._titulo = ctk.CTkLabel(self, text=titulo.upper(), font=("Segoe UI", 10),
                                    text_color=GRIS_TEXTO, anchor="w")
        self._valor = ctk.CTkLabel(self, text=str(valor), font=("Segoe UI", 24, "bold"),
                                   text_color=color or "gray90", anchor="w")
        self._titulo.pack(fill="x", padx=14, pady=(12, 0))
        self._valor.pack(fill="x", padx=14, pady=(2, 12))

    def set_valor(self, valor: Any, color: Optional[str] = None) -> None:
        self._valor.configure(text=str(valor))
        if color:
            self._valor.configure(text_color=color)


class BarraBotones(ctk.CTkFrame):
    """Barra de herramientas con acciones a la izquierda y búsqueda a la derecha."""

    def __init__(self, master: Any, *, busqueda: bool = True,
                 placeholder: str = "Buscar…",
                 al_buscar: Optional[Callable[[str], None]] = None):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(99, weight=1)
        self._indice = 0
        self._al_buscar = al_buscar
        if busqueda:
            self._buscador = ctk.CTkEntry(
                self, width=230, height=32, placeholder_text=placeholder,
                font=FUENTE_NORMAL,
            )
        else:
            self._buscador = None

    def agregar(self, texto: str, comando: Optional[Callable[[], Any]],
                *, color: str = ACENTO) -> ctk.CTkButton:
        btn = boton(self, texto, comando, color=color)
        btn.grid(row=0, column=self._indice, padx=(0, 8), pady=2, sticky="w")
        self._indice += 1
        return btn

    def espaciador(self) -> None:
        self.grid_columnconfigure(self._indice, weight=1)
        self._indice += 1

    def terminar_busqueda(self) -> None:
        if self._buscador is None:
            return
        self._buscador.grid(row=0, column=99, padx=(8, 0), pady=2, sticky="e")
        if self._al_buscar:
            self._buscador.bind("<KeyRelease>", lambda e: self._al_buscar(self.texto()))

    def texto(self) -> str:
        return self._buscador.get() if self._buscador else ""


# --------------------------------------------------------------------------- #
# Diálogos
# --------------------------------------------------------------------------- #


class Dialogo(ctk.CTkToplevel):
    """Base modal con formulario en dos columnas y botones Aceptar/Cancelar."""

    def __init__(self, master: Any, titulo: str, *, ancho: int = 560, alto: int = 560):
        super().__init__(master)
        self.withdraw()
        self.title(titulo)
        self.geometry(f"{ancho}x{alto}")
        self.resizable(False, False)
        self.transient(master)
        self.resultado: Any = None
        self._fila = 0
        self._campos: dict[str, Any] = {}
        self._objetos_selector: dict[str, dict[str, Any]] = {}

        c = colores_tema()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._cabecera = ctk.CTkLabel(self, text=titulo, font=FUENTE_TITULO,
                                      anchor="w", text_color=c["texto"])
        self._cabecera.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))

        self.form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.form.grid(row=1, column=0, sticky="nsew", padx=8)
        self.form.grid_columnconfigure(1, weight=1)

        self._pie = ctk.CTkFrame(self, fg_color="transparent")
        self._pie.grid(row=2, column=0, sticky="ew", padx=16, pady=(6, 16))

    # -- campos ----------------------------------------------------------- #
    def _etiqueta(self, texto: str) -> ctk.CTkLabel:
        label = ctk.CTkLabel(self.form, text=texto, font=FUENTE_NORMAL, anchor="w")
        label.grid(row=self._fila, column=0, sticky="w", padx=10, pady=6, ipady=6)
        return label

    def campo_texto(self, clave: str, etiqueta: str, valor: str = "",
                    placeholder: str = "", ancho: int = 330) -> ctk.CTkEntry:
        self._etiqueta(etiqueta)
        entrada = ctk.CTkEntry(self.form, width=ancho, font=FUENTE_NORMAL,
                               placeholder_text=placeholder)
        entrada.insert(0, valor or "")
        entrada.grid(row=self._fila, column=1, sticky="ew", padx=10, pady=6, ipady=4)
        self._fila += 1
        self._campos[clave] = entrada
        return entrada

    def campo_fecha(self, clave: str, etiqueta: str,
                    valor: Optional[date] = None) -> ctk.CTkEntry:
        return self.campo_texto(
            clave, etiqueta, fecha_legible(valor), placeholder="dd/mm/aaaa", ancho=160
        )

    def campo_monto(self, clave: str, etiqueta: str, valor: float = 0.0) -> ctk.CTkEntry:
        texto = "" if not valor else f"{valor:.2f}".replace(",", "")
        entrada = self.campo_texto(clave, etiqueta, texto, placeholder="0.00", ancho=160)
        return entrada

    def campo_selector(self, clave: str, etiqueta: str, valores: Sequence[str],
                       valor: Optional[str] = None) -> ctk.CTkOptionMenu:
        self._etiqueta(etiqueta)
        valores = list(valores) or ["—"]
        menu = ctk.CTkOptionMenu(self.form, values=valores, width=330,
                                 font=FUENTE_NORMAL, dynamic_resizing=False)
        menu.set(valor if valor in valores else valores[0])
        menu.grid(row=self._fila, column=1, sticky="w", padx=10, pady=6, ipady=2)
        self._fila += 1
        self._campos[clave] = menu
        return menu

    def campo_check(self, clave: str, etiqueta: str, valor: bool = False) -> ctk.CTkCheckBox:
        self._etiqueta(etiqueta)
        caja = ctk.CTkCheckBox(self.form, text="", font=FUENTE_NORMAL)
        if valor:
            caja.select()
        caja.grid(row=self._fila, column=1, sticky="w", padx=10, pady=6)
        self._fila += 1
        self._campos[clave] = caja
        return caja

    def campo_area(self, clave: str, etiqueta: str, valor: str = "",
                   altura: int = 140) -> ctk.CTkTextbox:
        label = ctk.CTkLabel(self.form, text=etiqueta, font=FUENTE_NORMAL, anchor="nw")
        label.grid(row=self._fila, column=0, sticky="nw", padx=10, pady=6, ipady=6)
        area = ctk.CTkTextbox(self.form, height=altura, font=FUENTE_NORMAL)
        area.insert("1.0", valor or "")
        area.grid(row=self._fila, column=1, sticky="ew", padx=10, pady=6)
        self._fila += 1
        self._campos[clave] = area
        return area

    def separador(self, texto: str) -> None:
        label = ctk.CTkLabel(self.form, text=texto, font=FUENTE_SUBTITULO,
                             anchor="w", text_color=ACENTO)
        label.grid(row=self._fila, column=0, columnspan=2, sticky="w",
                   padx=10, pady=(14, 2))
        self._fila += 1

    def nota(self, texto: str) -> None:
        label = ctk.CTkLabel(self.form, text=texto, font=FUENTE_PEQUE,
                             anchor="w", text_color=GRIS_TEXTO, wraplength=440,
                             justify="left")
        label.grid(row=self._fila, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
        self._fila += 1

    # -- lectura ---------------------------------------------------------- #
    def texto(self, clave: str) -> str:
        widget = self._campos[clave]
        if isinstance(widget, ctk.CTkTextbox):
            return widget.get("1.0", "end-1c").strip()
        if isinstance(widget, (ctk.CTkOptionMenu,)):
            return widget.get()
        if isinstance(widget, ctk.CTkCheckBox):
            return "1" if widget.get() else "0"
        return widget.get().strip()

    def fecha(self, clave: str) -> Optional[date]:
        return parsear_fecha(self.texto(clave))

    def monto(self, clave: str) -> float:
        return parsear_monto(self.texto(clave))

    def es_verdadero(self, clave: str) -> bool:
        widget = self._campos[clave]
        return bool(widget.get()) if isinstance(widget, ctk.CTkCheckBox) else bool(self.texto(clave))

    def valor_selector(self, clave: str) -> str:
        return self._campos[clave].get()

    def objeto_selector(self, clave: str, objetos: Sequence[Any],
                        clave_atributo: str = "id") -> Any:
        """Devuelve el objeto asociado al ítem seleccionado del ``OptionMenu``."""
        texto = self._campos[clave].get()
        for objeto in objetos:
            if str(getattr(objeto, clave_atributo)) == texto:
                return objeto
        return None

    def campo_selector_objetos(
        self,
        clave: str,
        etiqueta: str,
        objetos: Sequence[Any],
        etiquetador: Callable[[Any], str] = str,
        seleccion: Any = None,
        vacio: str = "— Ninguno —",
    ) -> ctk.CTkOptionMenu:
        """Selector cuyo valor visible es una etiqueta y cuyo objeto se recupera con :meth:`objeto`."""
        mapa: dict[str, Any] = {}
        valores: list[str] = []
        for objeto in objetos:
            base = etiquetador(objeto)
            texto, n = base, 2
            while texto in mapa:
                texto = f"{base} ({n})"
                n += 1
            mapa[texto] = objeto
            valores.append(texto)
        self._objetos_selector[clave] = mapa
        if not valores:
            valores = [vacio]
        menu = self.campo_selector(clave, etiqueta, valores)
        if seleccion is not None:
            for texto, objeto in mapa.items():
                if objeto is seleccion or getattr(objeto, "id", None) == getattr(
                    seleccion, "id", None
                ):
                    menu.set(texto)
                    break
        return menu

    def objeto(self, clave: str) -> Any:
        """Objeto elegido en un selector creado con :meth:`campo_selector_objetos`."""
        mapa = self._objetos_selector.get(clave, {})
        return mapa.get(self._campos[clave].get())

    # -- acciones --------------------------------------------------------- #
    def botones(self, texto_ok: str = "Guardar",
                al_aceptar: Optional[Callable[[], Any]] = None) -> None:
        self._al_aceptar = al_aceptar
        cancelar = boton_secundario(self._pie, "Cancelar", self.cancelar, ancho=110)
        cancelar.pack(side="right", padx=(8, 0))
        ok = boton(self._pie, texto_ok, self.aceptar, ancho=130)
        ok.pack(side="right")
        self.bind("<Escape>", lambda e: self.cancelar())
        self.bind("<Return>", lambda e: self.aceptar())

    def aceptar(self) -> None:
        if getattr(self, "_al_aceptar", None) is None:
            self.resultado = True
            self.destroy()
            return
        try:
            resultado = self._al_aceptar()
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            DialogoMensaje.error(self, "Datos inválidos", str(exc))
            return
        if resultado is not False:
            self.resultado = resultado
            self.destroy()

    def cancelar(self) -> None:
        self.resultado = None
        self.destroy()

    def mostrar(self) -> Any:
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window(self)
        return self.resultado


def ejecutar_protegido(
    parent: Any,
    accion: Callable[[], Any],
    refrescar: Optional[Callable[[], Any]] = None,
) -> Any:
    """Ejecuta una operación de negocio mostrando errores como diálogo."""
    try:
        resultado = accion()
    except FotiaError as exc:
        DialogoMensaje.error(parent, "Operación no válida", str(exc))
        return None
    except Exception as exc:  # noqa: BLE001 - último recurso para el usuario
        DialogoMensaje.error(parent, "Error inesperado", f"{type(exc).__name__}: {exc}")
        return None
    if refrescar:
        refrescar()
    return resultado


class DialogoMensaje(ctk.CTkToplevel):
    """Diálogo pequeño de información, error o confirmación."""

    def __init__(self, master: Any, titulo: str, mensaje: str,
                 *, tipo: str = "info", texto_si: str = "Aceptar"):
        super().__init__(master)
        self.withdraw()
        self.title(titulo)
        self.resizable(False, False)
        self.transient(master)
        self.resultado = False

        ancho = max(360, min(640, 12 + len(mensaje)))
        self.geometry(f"{ancho}x170")
        color = ROJO if tipo == "error" else ACENTO
        ctk.CTkLabel(self, text=titulo, font=FUENTE_SUBTITULO, text_color=color,
                     anchor="w").pack(fill="x", padx=18, pady=(18, 4))
        ctk.CTkLabel(self, text=mensaje, font=FUENTE_NORMAL, anchor="w",
                     justify="left", wraplength=ancho - 40).pack(
            fill="both", expand=True, padx=18, pady=4
        )
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=18, pady=(4, 16))

        if tipo == "confirmar":
            boton_secundario(pie, "Cancelar", lambda: self._cerrar(False)).pack(
                side="right", padx=(8, 0)
            )
            boton(pie, texto_si, lambda: self._cerrar(True)).pack(side="right")
        else:
            boton(pie, "Aceptar", lambda: self._cerrar(True)).pack(side="right")
        self.bind("<Escape>", lambda e: self._cerrar(False))

    def _cerrar(self, valor: bool) -> None:
        self.resultado = valor
        self.destroy()

    @classmethod
    def info(cls, master: Any, titulo: str, mensaje: str) -> None:
        cls(master, titulo, mensaje, tipo="info").mostrar()

    @classmethod
    def error(cls, master: Any, titulo: str, mensaje: str) -> None:
        cls(master, titulo, mensaje, tipo="error").mostrar()

    @classmethod
    def confirmar(cls, master: Any, titulo: str, mensaje: str,
                  texto_si: str = "Eliminar") -> bool:
        return bool(cls(master, titulo, mensaje, tipo="confirmar",
                        texto_si=texto_si).mostrar())

    def mostrar(self) -> bool:
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window(self)
        return self.resultado
