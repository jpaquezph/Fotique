"""Gráfico de torta sobre ``tk.Canvas`` (sin dependencias externas)."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Sequence

import customtkinter as ctk

from .theme import BORDE, FONDO, Color, colores_tema, elegir

# Tonos distinguibles entre sí en ambos modos: (claro, oscuro).
PALETA: list[Color] = [
    ("#2f7fc4", "#4a90c9"),
    ("#2b9348", "#4aa869"),
    ("#d9772b", "#cf8a4a"),
    ("#8a5cc2", "#9a78c9"),
    ("#c94f6d", "#c96a82"),
    ("#2a9d9d", "#4aa8a8"),
    ("#b8a12e", "#b5a24f"),
]
OTROS: Color = ("#9aa0aa", "#6b6f7b")
MAX_PORCIONES = len(PALETA)


class Torta(ctk.CTkFrame):
    """Torta con título y leyenda. ``mostrar`` recibe pares ``(etiqueta, valor)``."""

    def __init__(self, master: Any, titulo: str, *, diametro: int = 150,
                 formato: Callable[[float], str] = lambda v: f"{v:g}"):
        super().__init__(master, corner_radius=10, fg_color=FONDO, border_width=1,
                         border_color=BORDE)
        self._formato = formato
        self._datos: list[tuple[str, float]] = []
        escala = self._get_widget_scaling()
        self._lado = int(diametro * escala)
        self._letra = -round(12 * escala)  # tk no escala sus fuentes en puntos
        ctk.CTkLabel(self, text=titulo, font=("Segoe UI", 12, "bold"), anchor="w").pack(
            fill="x", padx=14, pady=(10, 2))
        self._lienzo = tk.Canvas(self, width=self._lado, height=self._lado,
                                 highlightthickness=0, bd=0)
        self._lienzo.pack(padx=14, pady=4)
        self._leyenda = tk.Frame(self)
        self._leyenda.pack(fill="x", padx=14, pady=(2, 10))
        self._dibujar()

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "_lienzo"):  # tk.Canvas no sigue el modo por su cuenta
            self._dibujar()

    def mostrar(self, datos: Sequence[tuple[str, float]]) -> None:
        porciones = sorted(((e, float(v)) for e, v in datos if v and v > 0),
                           key=lambda par: par[1], reverse=True)
        if len(porciones) > MAX_PORCIONES:  # el resto se agrupa para que se lea
            resto = sum(v for _e, v in porciones[MAX_PORCIONES - 1:])
            porciones = porciones[:MAX_PORCIONES - 1] + [("Otros", resto)]
        if porciones != self._datos:
            self._datos = porciones
            self._dibujar()

    def _dibujar(self) -> None:
        c = colores_tema()
        self._lienzo.configure(bg=c["fondo"])
        self._leyenda.configure(bg=c["fondo"])
        self._lienzo.delete("all")
        for hijo in self._leyenda.winfo_children():
            hijo.destroy()
        total = sum(v for _e, v in self._datos)
        if not total:
            self._lienzo.create_oval(4, 4, self._lado - 4, self._lado - 4,
                                     outline=c["borde"], width=2)
            self._lienzo.create_text(self._lado / 2, self._lado / 2, text="Sin datos",
                                     fill=c["texto_suave"], font=("Segoe UI", self._letra))
            return
        caja = (4, 4, self._lado - 4, self._lado - 4)
        angulo = 90.0
        for indice, (etiqueta, valor) in enumerate(self._datos):
            color = elegir(OTROS if etiqueta == "Otros" and indice == MAX_PORCIONES - 1
                           else PALETA[indice % len(PALETA)])
            barrido = 360.0 * valor / total
            if len(self._datos) == 1:  # un arco de 360° no se dibuja: usar el círculo
                self._lienzo.create_oval(*caja, fill=color, outline=c["fondo"], width=2)
            else:
                self._lienzo.create_arc(*caja, start=angulo - barrido, extent=barrido,
                                        fill=color, outline=c["fondo"], width=2)
            angulo -= barrido

            fila = tk.Frame(self._leyenda, bg=c["fondo"])
            fila.pack(fill="x", pady=1)
            tk.Label(fila, text="■", fg=color, bg=c["fondo"],
                     font=("Segoe UI", self._letra)).pack(side="left")
            tk.Label(fila, text=etiqueta, fg=c["texto"], bg=c["fondo"], anchor="w",
                     font=("Segoe UI", self._letra)).pack(side="left", padx=(4, 8))
            tk.Label(fila, text=f"{self._formato(valor)} · {100 * valor / total:.0f} %",
                     fg=c["texto_suave"], bg=c["fondo"],
                     font=("Segoe UI", self._letra)).pack(side="right")
