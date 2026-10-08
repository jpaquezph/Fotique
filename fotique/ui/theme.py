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

# La negrita queda para títulos y cifras; etiquetas, botones y encabezados van
# en seminegrita, que pesa menos al lado del contenido.
FAMILIA = "Segoe UI"
SEMINEGRITA = "Segoe UI Semibold"
FUENTE_TITULO = (FAMILIA, 22, "bold")
FUENTE_SUBTITULO = (FAMILIA, 14, "bold")
FUENTE_DIALOGO = (FAMILIA, 17, "bold")
FUENTE_NORMAL = (FAMILIA, 11)
FUENTE_BOTON = (SEMINEGRITA, 11)
FUENTE_PEQUE = (FAMILIA, 10)
FUENTE_ETIQUETA = (SEMINEGRITA, 10)
FUENTE_TABLA = (FAMILIA, 12)
FUENTE_TARJETA = (FAMILIA, 22, "bold")
FUENTE_NAV = (FAMILIA, 13)

# Esquinas: tarjetas y paneles, controles, y la tarjeta de acceso.
RADIO = 16
RADIO_CH = 10
RADIO_GR = 22

Color = tuple[str, str]

# -- superficies y texto ----------------------------------------------------- #
# El LIENZO es el fondo de la ventana; FONDO es la superficie de tarjetas,
# tablas y campos, que se despega del lienzo sin depender solo del borde.
# En claro los neutros son cálidos (crema y tinta marrón); en oscuro todo
# parte de la tinta violácea de la marca, la misma de la barra lateral.
LIENZO: Color = ("#faf6ef", "#0e0d12")
FONDO: Color = ("#ffffff", "#1a1822")
RESALTE: Color = ("#f3eee3", "#262330")      # hover, encabezados, día de hoy
BORDE: Color = ("#e7e0d2", "#2f2c3b")
BORDE_FUERTE: Color = ("#d6cdba", "#403c50")  # contorno de los botones secundarios
# En oscuro todo el texto va en blanco: los grises se leían apagados.
TEXTO: Color = ("#2b2620", "#ffffff")
TEXTO_SUAVE: Color = ("#6f6656", "#ffffff")
TEXTO_TENUE: Color = ("#bdb4a2", "#555168")  # días fuera del mes, deshabilitado
GRIS_TEXTO: Color = ("#857b68", "#ffffff")
MARCADOR: Color = ("#857b68", "#928ea6")     # texto de ayuda de un campo vacío

# -- barra lateral: blanca en claro; en oscuro se funde con el lienzo ---------- #
LATERAL: Color = ("#ffffff", "#0e0d12")
LATERAL_HOVER: Color = ("#f3eee3", "#1d1b26")
LATERAL_TEXTO: Color = ("#2b2620", "#ffffff")
LATERAL_SUAVE: Color = ("#857b68", "#ffffff")
# Tarjeta del acceso: en oscuro toda la pantalla de ingreso es un solo fondo.
TARJETA_ACCESO: Color = ("#ffffff", "#0e0d12")

# -- acentos para texto (legibles sobre FONDO en ambos modos) ---------------- #
ACENTO: Color = ("#5b3fd6", "#a594ff")
VERDE: Color = ("#128a43", "#5fdc8c")
ROJO: Color = ("#d42a3a", "#ff7f88")
NARANJA: Color = ("#cf5f0a", "#f5a04e")
AMARILLO: Color = ("#8a6a00", "#e8cc5a")
VIOLETA: Color = ("#7446b5", "#b396e0")
TURQUESA: Color = ("#17807f", "#5fc4c2")

# -- botones: (relleno, hover), con texto en TEXTO_BOTON ---------------------- #
# Color pleno y vivo: el tono dice qué hace cada acción (crear, cobrar,
# devolver, borrar). También pinta lo que está seleccionado.
TEXTO_BOTON: Color = ("#ffffff", "#ffffff")
TEXTO_BOTON_INACTIVO: Color = ("#e6e0ff", "#b9b2d6")  # sobre un botón deshabilitado
BOTONES: dict[str, tuple[Color, Color]] = {
    "primario": (("#6d4aff", "#6d4aff"), ("#5a38e8", "#8166ff")),
    "exito": (("#149653", "#149653"), ("#0f7f45", "#1bb065")),
    "aviso": (("#e8641b", "#e8641b"), ("#cf5410", "#f57a33")),
    "peligro": (("#e5384f", "#e5384f"), ("#cc2940", "#f0546a")),
}
# Rellenos sólidos de las tarjetas (texto en TEXTO_BOTON): una gama análoga
# de fríos, del celeste al malva, más el verde y el rojo de los importes.
RELLENOS: dict[str, Color] = {
    "celeste": ("#1c96d6", "#1883bd"),
    "azul": ("#3d6ff2", "#3460d6"),
    "indigo": ("#5f55ee", "#5249d4"),
    "violeta": ("#8b4eea", "#7a41d1"),
    "malva": ("#c043b4", "#a8389d"),
    "verde": ("#149653", "#12854a"),
    "rojo": ("#e5384f", "#cc2f44"),
}
# Selectores, segmentos y desplegables: reposan en el neutro cálido y lo que
# está elegido toma un tinte del acento, para leerse como control activo.
NEUTRO: Color = ("#f3eee3", "#252230")
NEUTRO_HOVER: Color = ("#e7e0d2", "#322e42")
SEGMENTO_ACTIVO: Color = ("#d9d0ff", "#4a3d8f")
SELECCION: Color = ("#e9e3ff", "#332b5c")    # fila o segmento seleccionado
CON_EVENTOS: Color = ("#efeafb", "#2c2744")  # día del calendario con agenda
CEBRA: Color = ("#fcfaf6", "#1f1d27")        # fila alternada de una tabla

TEMAS = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}

_tema_cargado = False


def _cargar_tema() -> None:
    """Parte del tema «blue» y lo ajusta a la paleta de Fotique (una sola vez)."""
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
                      "text_color_disabled": TEXTO_TENUE, "corner_radius": RADIO_CH},
        "CTkLabel": {"text_color": TEXTO},
        "CTkEntry": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                     "text_color": TEXTO, "placeholder_text_color": MARCADOR,
                     "corner_radius": RADIO_CH},
        "CTkTextbox": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                       "text_color": TEXTO, "scrollbar_button_color": BORDE,
                       "scrollbar_button_hover_color": TEXTO_TENUE,
                       "corner_radius": RADIO_CH},
        "CTkCheckBox": {"fg_color": primario, "hover_color": primario_hover,
                        "border_color": TEXTO_SUAVE, "checkmark_color": TEXTO_BOTON,
                        "text_color": TEXTO, "border_width": 2},
        "CTkOptionMenu": {"fg_color": NEUTRO, "button_color": NEUTRO_HOVER,
                          "button_hover_color": SEGMENTO_ACTIVO, "text_color": TEXTO,
                          "text_color_disabled": TEXTO_TENUE, "corner_radius": RADIO_CH},
        "CTkSegmentedButton": {"fg_color": NEUTRO, "selected_color": SEGMENTO_ACTIVO,
                               "selected_hover_color": SEGMENTO_ACTIVO,
                               "unselected_color": NEUTRO,
                               "unselected_hover_color": NEUTRO_HOVER,
                               "text_color": TEXTO,
                               "text_color_disabled": TEXTO_TENUE, "corner_radius": RADIO_CH},
        "CTkComboBox": {"fg_color": FONDO, "border_color": BORDE, "border_width": 1,
                        "corner_radius": RADIO_CH,
                        "button_color": NEUTRO_HOVER, "button_hover_color": SEGMENTO_ACTIVO,
                        "text_color": TEXTO, "text_color_disabled": TEXTO_TENUE},
        "CTkScrollbar": {"button_color": BORDE, "button_hover_color": TEXTO_TENUE},
        "CTkScrollableFrame": {"label_fg_color": RESALTE},
        "CTkFont": {"family": FAMILIA, "size": 12, "weight": "normal"},
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


def ancho_par(widget: tkinter.Misc, ancho: int) -> int:
    """``ancho`` o el siguiente que, con el escalado de pantalla, da píxeles pares.

    CustomTkinter dibuja los botones sólo en anchos pares: con uno impar (118
    al 150 % son 177 px) sobra una columna y la esquina derecha queda cortada.
    """
    escala = ctk.ScalingTracker.get_widget_scaling(widget)
    for candidato in range(ancho, ancho + 8):
        pixeles = candidato * escala
        if abs(pixeles - round(pixeles)) < 1e-6 and round(pixeles) % 2 == 0:
            return candidato
    return ancho


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
    style.layout("Fotique.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure(
        "Fotique.Treeview",
        background=c["fondo"],
        fieldbackground=c["fondo"],
        foreground=c["texto"],
        borderwidth=0,
        relief="flat",
        rowheight=34,
        font=FUENTE_TABLA,
        padding=4,
    )
    style.configure(
        "Fotique.Treeview.Heading",
        background=c["resalte"],
        foreground=c["texto_suave"],
        borderwidth=0,
        relief="flat",
        font=(FAMILIA, 10, "bold"),
        padding=9,
    )
    style.map(
        "Fotique.Treeview",
        background=[("selected", c["seleccion"])],
        foreground=[("selected", c["texto"])],
    )
    style.map(
        "Fotique.Treeview.Heading",
        background=[("active", c["borde"])],
    )
    # Variante de filas altas (tarifario); el resto lo hereda de Fotique.Treeview.
    style.configure("Amplia.Fotique.Treeview", rowheight=40)
    for orientacion in ("Vertical", "Horizontal"):
        style.configure(
            f"Fotique.{orientacion}.TScrollbar",
            background=c["borde"], troughcolor=c["fondo"], bordercolor=c["fondo"],
            lightcolor=c["borde"], darkcolor=c["borde"], arrowcolor=c["texto_suave"],
            relief="flat", borderwidth=0,
        )
        style.map(f"Fotique.{orientacion}.TScrollbar",
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
                  "font": FUENTE_ETIQUETA},
        "cebra": {"background": elegir(CEBRA)},
    }
