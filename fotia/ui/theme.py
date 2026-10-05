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

FUENTE_TITULO = ("Segoe UI", 22, "bold")
FUENTE_SUBTITULO = ("Segoe UI", 13, "bold")
FUENTE_NORMAL = ("Segoe UI", 11)
FUENTE_BOTON = ("Segoe UI", 11, "bold")
FUENTE_PEQUE = ("Segoe UI", 10)
FUENTE_TABLA = ("Segoe UI", 12)
FUENTE_TARJETA = ("Segoe UI", 22, "bold")

Color = tuple[str, str]

# -- superficies y texto ----------------------------------------------------- #
# El LIENZO es el fondo de la ventana; FONDO es la superficie de tarjetas,
# tablas y campos, que se despega del lienzo sin depender solo del borde.
LIENZO: Color = ("#f4f3f9", "#131218")
FONDO: Color = ("#ffffff", "#1c1a23")
RESALTE: Color = ("#ebe9f5", "#272431")      # hover, encabezados, día de hoy
BORDE: Color = ("#dddaea", "#2f2c3b")
TEXTO: Color = ("#18161f", "#eceaf4")
TEXTO_SUAVE: Color = ("#5e5a70", "#a09cb3")
TEXTO_TENUE: Color = ("#b3afc4", "#4d4960")  # días fuera del mes, deshabilitado
GRIS_TEXTO: Color = ("#6d697f", "#928ea6")

# -- barra lateral: tinta oscura en los dos modos, es la marca de la app ------ #
LATERAL: Color = ("#17151e", "#0e0d12")
LATERAL_HOVER: Color = ("#272432", "#1d1b26")
LATERAL_TEXTO: Color = ("#dedbea", "#dedbea")
LATERAL_SUAVE: Color = ("#8d899f", "#8d899f")

# -- acentos para texto (legibles sobre FONDO en ambos modos) ---------------- #
ACENTO: Color = ("#5b3fd6", "#a594ff")
VERDE: Color = ("#16702f", "#6fd08a")
ROJO: Color = ("#b8242e", "#ff8a8f")
NARANJA: Color = ("#b85f14", "#e0a060")
AMARILLO: Color = ("#8a6a00", "#e8cc5a")
VIOLETA: Color = ("#7446b5", "#b396e0")
TURQUESA: Color = ("#17807f", "#5fc4c2")

# -- botones sólidos: (relleno, hover), con texto en TEXTO_BOTON -------------- #
# Para la acción principal de un diálogo y para lo que está seleccionado.
TEXTO_BOTON: Color = ("#ffffff", "#ffffff")
BOTONES: dict[str, tuple[Color, Color]] = {
    "primario": (("#6d4aff", "#6d4aff"), ("#5a38e8", "#8166ff")),
    "exito": (("#17854a", "#17854a"), ("#126c3c", "#1f9d57")),
    "aviso": (("#c2570f", "#c2570f"), ("#a3480b", "#d96a1e")),
    "peligro": (("#d93651", "#d93651"), ("#bd2843", "#e8526b")),
}
# -- botones tonales: (relleno, hover, texto). Son los de las barras de -------- #
# acciones: varios juntos no compiten con el contenido.
TONOS: dict[str, tuple[Color, Color, Color]] = {
    "primario": (("#e9e4ff", "#2a2447"), ("#d9d1ff", "#372f5e"), ("#4a2fc4", "#c5baff")),
    "exito": (("#daf3e4", "#16301f"), ("#c5ebd4", "#1e4029"), ("#126c3a", "#7fe0a2")),
    "aviso": (("#fdead5", "#382614"), ("#fadcba", "#4a331b"), ("#994c0b", "#f2b272")),
    "peligro": (("#fde0e5", "#3b1922"), ("#fbcbd3", "#50222e"), ("#b3213a", "#ff9aa8")),
}
# Rellenos sólidos de las tarjetas (texto en TEXTO_BOTON): una gama análoga
# de fríos, del celeste al malva, más el verde y el rojo de los importes.
RELLENOS: dict[str, Color] = {
    "celeste": ("#3b8fc2", "#327aa8"),
    "azul": ("#5278d9", "#4366c2"),
    "indigo": ("#6d68d8", "#5c57bf"),
    "violeta": ("#8f62d0", "#7b52b8"),
    "malva": ("#b05fa6", "#984f8f"),
    "verde": ("#2f9a6a", "#288259"),
    "rojo": ("#cf4f66", "#b34258"),
}
# Selectores, segmentos y desplegables: un violeta tenue de la familia del
# acento en lugar de gris, para que se lean como controles y no como fondo.
NEUTRO: Color = ("#eceaf6", "#252230")
NEUTRO_HOVER: Color = ("#ddd9ee", "#322e42")
SEGMENTO_ACTIVO: Color = ("#cfc5ff", "#4a3d8f")
SELECCION: Color = ("#e4deff", "#332b5c")    # fila o segmento seleccionado
CON_EVENTOS: Color = ("#ece8ff", "#262040")  # día del calendario con agenda
CEBRA: Color = ("#f8f7fc", "#201e28")        # fila alternada de una tabla

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
        "CTk": {"fg_color": LIENZO},
        "CTkToplevel": {"fg_color": LIENZO},
        "CTkFrame": {"fg_color": FONDO, "top_fg_color": FONDO, "border_color": BORDE},
        "CTkButton": {"fg_color": primario, "hover_color": primario_hover,
                      "text_color": TEXTO_BOTON, "border_color": BORDE,
                      "text_color_disabled": TEXTO_TENUE, "corner_radius": 16},
        "CTkLabel": {"text_color": TEXTO},
        "CTkEntry": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                     "text_color": TEXTO, "placeholder_text_color": TEXTO_SUAVE,
                     "corner_radius": 10},
        "CTkTextbox": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                       "text_color": TEXTO, "scrollbar_button_color": BORDE,
                       "scrollbar_button_hover_color": TEXTO_TENUE,
                       "corner_radius": 10},
        "CTkCheckBox": {"fg_color": primario, "hover_color": primario_hover,
                        "border_color": TEXTO_SUAVE, "checkmark_color": TEXTO_BOTON,
                        "text_color": TEXTO, "border_width": 2},
        "CTkOptionMenu": {"fg_color": NEUTRO, "button_color": NEUTRO_HOVER,
                          "button_hover_color": SEGMENTO_ACTIVO, "text_color": TEXTO,
                          "text_color_disabled": TEXTO_TENUE, "corner_radius": 10},
        "CTkSegmentedButton": {"fg_color": NEUTRO, "selected_color": SEGMENTO_ACTIVO,
                               "selected_hover_color": SEGMENTO_ACTIVO,
                               "unselected_color": NEUTRO,
                               "unselected_hover_color": NEUTRO_HOVER,
                               "text_color": TEXTO,
                               "text_color_disabled": TEXTO_TENUE, "corner_radius": 10},
        "CTkComboBox": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                        "corner_radius": 10,
                        "button_color": NEUTRO_HOVER, "button_hover_color": SEGMENTO_ACTIVO,
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
        rowheight=32,
        font=FUENTE_TABLA,
        padding=4,
    )
    style.configure(
        "Fotia.Treeview.Heading",
        background=c["resalte"],
        foreground=c["texto_suave"],
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padding=8,
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
    # Variante de filas altas (tarifario); el resto lo hereda de Fotia.Treeview.
    style.configure("Amplia.Fotia.Treeview", rowheight=40)
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
        "presupuesto": elegir(AMARILLO),
    }


def estilos_filas() -> dict[str, dict]:
    """Tags de fila que cambian fondo o letra: grupos y filas alternadas."""
    return {
        "grupo": {"background": elegir(RESALTE), "foreground": elegir(ACENTO),
                  "font": ("Segoe UI", 10, "bold")},
        "cebra": {"background": elegir(CEBRA)},
    }
