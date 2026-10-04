"""Paleta, tipografía y estilos compartidos de la UI.

Los colores son pares ``(claro, oscuro)``: CustomTkinter elige el que
corresponde y repinta solo al cambiar de apariencia, así ningún widget queda
con el color del modo anterior. ``ttk`` no entiende pares, por eso las tablas
se estilizan con :func:`aplicar_estilo_tabla` usando :func:`elegir`.
"""

from __future__ import annotations

import sys
import tkinter
from tkinter import ttk
from typing import Optional

import customtkinter as ctk

FUENTE_TITULO = ("Segoe UI", 16, "bold")
FUENTE_SUBTITULO = ("Segoe UI", 13, "bold")
FUENTE_NORMAL = ("Segoe UI", 11)
FUENTE_PEQUE = ("Segoe UI", 10)
FUENTE_TARJETA = ("Segoe UI", 22, "bold")

Color = tuple[str, str]

# -- superficies y texto ----------------------------------------------------- #
FONDO: Color = ("#f3f4f6", "#1a1b1e")
RESALTE: Color = ("#e6e8ed", "#26272c")      # hover, encabezados, día de hoy
BORDE: Color = ("#cfd3da", "#34363c")
TEXTO: Color = ("#1a1b1e", "#e8e9ec")
TEXTO_SUAVE: Color = ("#5f6470", "#9a9ca6")
TEXTO_TENUE: Color = ("#aeb3bd", "#4c4f57")  # días fuera del mes, deshabilitado
GRIS_TEXTO: Color = ("#6b6f7b", "#8f919b")

# -- acentos para texto (legibles sobre FONDO en ambos modos) ---------------- #
ACENTO: Color = ("#1f6fb5", "#6aaee6")
VERDE: Color = ("#1e7f3a", "#5fbf7a")
ROJO: Color = ("#c4323b", "#ef7a80")
NARANJA: Color = ("#b85f14", "#e0a060")
VIOLETA: Color = ("#7446b5", "#b396e0")
TURQUESA: Color = ("#17807f", "#5fc4c2")

# -- botones: (relleno, hover). En oscuro son tonos apagados, no saturados ---- #
TEXTO_BOTON: Color = ("#ffffff", "#e6ebf0")
BOTONES: dict[str, tuple[Color, Color]] = {
    "primario": (("#2f7fc4", "#2c5a82"), ("#276aa5", "#356b99")),
    "exito": (("#2b9348", "#2a5c3d"), ("#237a3b", "#33704a")),
    "aviso": (("#d9772b", "#7d5427"), ("#bd6622", "#946430")),
    "peligro": (("#d5404a", "#7c3237"), ("#b9343d", "#933b41")),
}
NEUTRO: Color = ("#e2e5ea", "#2a2c31")       # selectores, botones secundarios
NEUTRO_HOVER: Color = ("#d3d7de", "#34363c")
SELECCION: Color = ("#c9dcf0", "#2c5a82")    # fila o segmento seleccionado
CON_EVENTOS: Color = ("#d8e9f7", "#1f3347")  # día del calendario con agenda

TEMAS = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}

_tema_cargado = False


def _cargar_tema() -> None:
    """Parte del tema «blue» y lo ajusta a la paleta de Fotia (una sola vez)."""
    global _tema_cargado
    if _tema_cargado:
        return
    ctk.set_default_color_theme("blue")
    primario, primario_hover = BOTONES["primario"]
    ajustes = {
        "CTk": {"fg_color": FONDO},
        "CTkToplevel": {"fg_color": FONDO},
        "CTkFrame": {"fg_color": FONDO, "top_fg_color": FONDO, "border_color": BORDE},
        "CTkButton": {"fg_color": primario, "hover_color": primario_hover,
                      "text_color": TEXTO_BOTON, "border_color": BORDE,
                      "text_color_disabled": TEXTO_TENUE},
        "CTkLabel": {"text_color": TEXTO},
        "CTkEntry": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                     "text_color": TEXTO, "placeholder_text_color": TEXTO_SUAVE},
        "CTkTextbox": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                       "text_color": TEXTO, "scrollbar_button_color": BORDE,
                       "scrollbar_button_hover_color": TEXTO_TENUE},
        "CTkCheckBox": {"fg_color": primario, "hover_color": primario_hover,
                        "border_color": TEXTO_SUAVE, "checkmark_color": TEXTO_BOTON,
                        "text_color": TEXTO, "border_width": 2},
        "CTkOptionMenu": {"fg_color": NEUTRO, "button_color": NEUTRO_HOVER,
                          "button_hover_color": BORDE, "text_color": TEXTO,
                          "text_color_disabled": TEXTO_TENUE},
        "CTkSegmentedButton": {"fg_color": NEUTRO, "selected_color": SELECCION,
                               "selected_hover_color": SELECCION,
                               "unselected_color": NEUTRO,
                               "unselected_hover_color": NEUTRO_HOVER,
                               "text_color": TEXTO,
                               "text_color_disabled": TEXTO_TENUE},
        "CTkComboBox": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                        "button_color": NEUTRO_HOVER, "button_hover_color": BORDE,
                        "text_color": TEXTO, "text_color_disabled": TEXTO_TENUE},
        "CTkScrollbar": {"button_color": BORDE, "button_hover_color": TEXTO_TENUE},
        "CTkScrollableFrame": {"label_fg_color": RESALTE},
        "DropdownMenu": {"fg_color": FONDO, "hover_color": NEUTRO_HOVER,
                         "text_color": TEXTO},
    }
    for widget, valores in ajustes.items():
        seccion = ctk.ThemeManager.theme.setdefault(widget, {})
        for clave, valor in valores.items():
            seccion[clave] = list(valor) if isinstance(valor, tuple) else valor
    _tema_cargado = True


def configurar_apariencia(modo: str = "Sistema") -> None:
    _cargar_tema()
    ctk.set_appearance_mode(TEMAS.get(modo, "system"))


def area_de_trabajo(widget: tkinter.Misc) -> tuple[int, int, int, int]:
    """``(x, y, ancho, alto)`` del escritorio sin la barra de tareas, en píxeles.

    ``winfo_screenwidth`` no sirve en Windows con escalado: Tk lo lee antes de
    que el proceso sea *DPI aware* y devuelve un tamaño menor al real.
    """
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    return 0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight()


def modo_oscuro() -> bool:
    return ctk.get_appearance_mode() == "Dark"


def elegir(color: Color) -> str:
    """Valor efectivo de un par ``(claro, oscuro)`` en el modo activo."""
    return color[1] if modo_oscuro() else color[0]


def colores_tema() -> dict[str, str]:
    """Colores efectivos según el modo de apariencia activo (para ``ttk``)."""
    return {
        "fondo": elegir(FONDO),
        "resalte": elegir(RESALTE),
        "borde": elegir(BORDE),
        "texto": elegir(TEXTO),
        "texto_suave": elegir(TEXTO_SUAVE),
        "seleccion": elegir(SELECCION),
    }


def aplicar_estilo_tabla(master: Optional[tkinter.Misc] = None) -> None:
    """Estiliza ``ttk.Treeview`` según el modo claro/oscuro (llamar al cambiarlo).

    Los estilos de ``ttk`` son por intérprete Tk: sin ventana todavía no hay
    dónde aplicarlos (y ``ttk.Style()`` crearía una ventana raíz de más), así
    que la ventana principal vuelve a llamar a esta función al crearse.
    """
    master = master or tkinter._default_root
    if master is None:
        return
    c = colores_tema()
    style = ttk.Style(master)
    try:
        style.theme_use("clam")
    except Exception:  # pragma: no cover - tema inexistente
        pass
    # Sin el borde propio de «clam»: el marco lo dibuja la Tabla, con la paleta.
    style.layout("Fotia.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure(
        "Fotia.Treeview",
        background=c["fondo"],
        fieldbackground=c["fondo"],
        foreground=c["texto"],
        borderwidth=0,
        relief="flat",
        rowheight=26,
        font=FUENTE_NORMAL,
        padding=4,
    )
    style.configure(
        "Fotia.Treeview.Heading",
        background=c["resalte"],
        foreground=c["texto"],
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padding=6,
    )
    style.map(
        "Fotia.Treeview",
        background=[("selected", c["seleccion"])],
        foreground=[("selected", c["texto"])],
    )
    style.map(
        "Fotia.Treeview.Heading",
        background=[("active", c["borde"])],
    )
    for orientacion in ("Vertical", "Horizontal"):
        style.configure(
            f"Fotia.{orientacion}.TScrollbar",
            background=c["borde"], troughcolor=c["fondo"], bordercolor=c["fondo"],
            lightcolor=c["borde"], darkcolor=c["borde"], arrowcolor=c["texto_suave"],
            relief="flat", borderwidth=0,
        )
        style.map(f"Fotia.{orientacion}.TScrollbar",
                  background=[("active", c["texto_suave"])])


def colores_etiquetas() -> dict[str, str]:
    """Tags de fila para alertas y estados en las tablas."""
    return {
        "vencido": elegir(ROJO),
        "proximo": elegir(NARANJA),
        "ok": elegir(VERDE),
        "entregado": elegir(GRIS_TEXTO),
        "pendiente": elegir(ACENTO),
        "alerta": elegir(ROJO),
    }
