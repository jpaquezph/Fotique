"""Logo de Fotique dentro de la interfaz e ícono de las ventanas.

Las imágenes salen de ``scripts/generar_logo.ps1``: el logo en negro (modo
claro) y en blanco (modo oscuro), una por cada escala de pantalla, y el
``.ico``. Se cargan con ``tk.PhotoImage``, sin dependencias externas.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from typing import Any, Optional

import customtkinter as ctk

from .theme import Color, elegir, modo_oscuro

RECURSOS = Path(__file__).parent / "recursos"
ICONO = RECURSOS / "fotique.ico"
ESCALAS = (100, 125, 150, 175, 200)


def aplicar_icono(ventana: tk.Misc) -> None:
    """Pone el ícono de Fotique en la barra de título (y en la barra de tareas)."""
    if sys.platform != "win32" or not ICONO.exists():
        return
    try:
        ventana.iconbitmap(str(ICONO))
    except tk.TclError:  # pragma: no cover - ícono ilegible: queda el de Tk
        pass


def identificar_aplicacion() -> None:
    """Hace que Windows agrupe la ventana como «Fotique» y no como Python.

    Sin esto la barra de tareas muestra el ícono del intérprete.
    """
    if sys.platform == "win32":
        import ctypes

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Fotique.App")
        except (AttributeError, OSError):  # pragma: no cover
            pass


class Logo(ctk.CTkFrame):
    """El logo sobre ``fondo``; elige negro o blanco según el modo activo."""

    def __init__(self, master: Any, fondo: Color):
        super().__init__(master, fg_color="transparent")
        self._fondo = fondo
        porcentaje = self._get_widget_scaling() * 100
        self._escala = min(ESCALAS, key=lambda e: abs(e - porcentaje))
        self._imagenes: dict[str, tk.PhotoImage] = {}
        self._etiqueta = tk.Label(self, bd=0, highlightthickness=0)
        self._etiqueta.pack()
        self._pintar()

    def _imagen(self, variante: str) -> Optional[tk.PhotoImage]:
        if variante not in self._imagenes:
            ruta = RECURSOS / f"logo_{variante}_{self._escala}.png"
            if not ruta.exists():
                return None
            imagen = self._leer(ruta)
            if imagen is None:
                return None
            self._imagenes[variante] = imagen
        return self._imagenes[variante]

    def _leer(self, ruta: Path) -> Optional[tk.PhotoImage]:
        """Decodifica el PNG; Tk falla a veces sin motivo y al reintentar anda."""
        for _ in range(3):
            try:
                return tk.PhotoImage(master=self, file=str(ruta))
            except tk.TclError:
                continue
        return None  # pragma: no cover - queda el nombre en texto

    def _pintar(self) -> None:
        blanco = modo_oscuro()
        imagen = self._imagen("blanco" if blanco else "negro")
        if imagen is None:  # sin recursos: el nombre en texto
            self._etiqueta.configure(text="fotique", font=("Segoe UI", 20, "bold"),
                                     fg="#ffffff" if blanco else "#18161f",
                                     bg=elegir(self._fondo))
        else:
            self._etiqueta.configure(image=imagen, bg=elegir(self._fondo))

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "_etiqueta"):  # tk.Label no sigue el modo por su cuenta
            self._pintar()
