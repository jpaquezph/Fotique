"""Paleta, tipografía y estilos compartidos de la UI."""

from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk

FUENTE_TITULO = ("Segoe UI", 16, "bold")
FUENTE_SUBTITULO = ("Segoe UI", 13, "bold")
FUENTE_NORMAL = ("Segoe UI", 11)
FUENTE_PEQUE = ("Segoe UI", 10)
FUENTE_TARJETA = ("Segoe UI", 22, "bold")

ACENTO = "#3b8ed0"
ACENTO_HOVER = "#36719f"
VERDE = "#2ea043"
ROJO = "#e5484d"
NARANJA = "#f0883e"
GRIS_TEXTO = "#8b8d98"

TEMAS = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}


def configurar_apariencia(modo: str = "Sistema") -> None:
    ctk.set_appearance_mode(TEMAS.get(modo, "system"))
    ctk.set_default_color_theme("blue")


def colores_tema() -> dict[str, str]:
    """Colores efectivos según el modo de apariencia activo."""
    oscuro = ctk.get_appearance_mode() == "Dark"
    return {
        "fondo": "#1a1b1e" if oscuro else "#f5f5f5",
        "superficie": "#25262b" if oscuro else "#ffffff",
        "borde": "#3a3b40" if oscuro else "#d9d9d9",
        "texto": "#ffffff" if oscuro else "#1a1b1e",
        "texto_suave": "#a0a1a8" if oscuro else "#6b6d76",
        "encabezado": "#2c2d33" if oscuro else "#ececef",
        "seleccion": "#3b8ed0",
        "filas": "#2a2b30" if oscuro else "#fafafa",
        "fila_par": "#232429" if oscuro else "#f1f1f4",
    }


def aplicar_estilo_tabla() -> None:
    """Estiliza ``ttk.Treeview`` según el modo claro/oscuro (llamar al cambiarlo)."""
    c = colores_tema()
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:  # pragma: no cover - tema inexistente
        pass
    style.configure(
        "Fotia.Treeview",
        background=c["superficie"],
        fieldbackground=c["superficie"],
        foreground=c["texto"],
        borderwidth=0,
        relief="flat",
        rowheight=26,
        font=FUENTE_NORMAL,
        padding=4,
    )
    style.configure(
        "Fotia.Treeview.Heading",
        background=c["encabezado"],
        foreground=c["texto"],
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padding=6,
    )
    style.map(
        "Fotia.Treeview",
        background=[("selected", c["seleccion"])],
        foreground=[("selected", "#ffffff")],
    )
    style.map(
        "Fotia.Treeview.Heading",
        background=[("active", c["borde"])],
    )
    style.configure("Fotia.Vertical.TScrollbar", background=c["borde"],
                    troughcolor=c["fondo"], bordercolor=c["fondo"],
                    arrowcolor=c["texto_suave"])
    style.configure("Fotia.Horizontal.TScrollbar", background=c["borde"],
                    troughcolor=c["fondo"], bordercolor=c["fondo"],
                    arrowcolor=c["texto_suave"])


def colores_etiquetas() -> dict[str, str]:
    """Tags de fila para alertas y estados en las tablas."""
    return {
        "vencido": ROJO,
        "proximo": NARANJA,
        "ok": VERDE,
        "entregado": GRIS_TEXTO,
        "pendiente": ACENTO,
    }
