"""Gráfico de torta sobre ``tk.Canvas`` (sin dependencias externas)."""

from __future__ import annotations

import math
import tkinter as tk
from bisect import bisect_right
from functools import lru_cache
from typing import Any, Callable, Sequence

import customtkinter as ctk

from .theme import BORDE, FONDO, RADIO, SEMINEGRITA, Color, colores_tema, elegir

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


@lru_cache(maxsize=16)  # se repite al volver a una sección o cambiar de modo
def _pixeles(lado: int, fracciones: tuple[float, ...], colores: tuple[str, ...],
             fondo: str, *, aro: str = "") -> list[str]:
    """Filas de píxeles de la torta, listas para ``PhotoImage.put``.

    ``tk.Canvas`` dibuja sin suavizado y el círculo queda escalonado; acá cada
    píxel del borde y de las divisiones se mezcla con el fondo según cuánto lo
    cubre la porción. ``aro`` dibuja sólo el contorno (torta sin datos).
    """
    def rgb(color: str) -> tuple[int, int, int]:
        return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

    base = rgb(fondo)
    tintas = [rgb(color) for color in (colores or [aro])]
    mezclas: dict[tuple[int, int], str] = {}

    def mezcla(indice: int, cobertura: float) -> str:
        paso = int(cobertura * 16 + 0.5)
        clave = (indice, paso)
        if clave not in mezclas:
            mezclas[clave] = "#%02x%02x%02x" % tuple(
                round(b + (t - b) * paso / 16) for b, t in zip(base, tintas[indice]))
        return mezclas[clave]

    centro, radio = lado / 2, lado / 2 - 4
    limites, acumulado = [], 0.0
    for fraccion in fracciones:
        limites.append(acumulado * math.tau)
        acumulado += fraccion
    # Cada división es un rayo desde el centro; 0 rad es arriba y crece horario.
    rayos = [(math.sin(a), -math.cos(a)) for a in limites]
    cantidad = len(rayos)
    corte = (radio + 1) ** 2
    filas = []
    for y in range(lado):
        dy = y + 0.5 - centro
        fila = []
        for x in range(lado):
            dx = x + 0.5 - centro
            d2 = dx * dx + dy * dy
            if d2 >= corte:
                fila.append(fondo)
                continue
            d = math.sqrt(d2)
            cobertura = min(1.0, radio - d + 0.5)
            indice = 0
            if aro:  # contorno de 2 px
                cobertura = min(cobertura, max(0.0, d - radio + 2.5))
            elif cantidad > 1:
                indice = bisect_right(limites, math.atan2(dx, -dy) % math.tau) - 1
                for ux, uy in (rayos[indice], rayos[(indice + 1) % cantidad]):
                    lejos = abs(dx * uy - dy * ux) if dx * ux + dy * uy > 0 else d
                    cobertura = min(cobertura, max(0.0, lejos - 0.5))  # división de 2 px
            fila.append(mezcla(indice, cobertura) if cobertura > 0 else fondo)
        filas.append("{" + " ".join(fila) + "}")
    return filas


class Torta(ctk.CTkFrame):
    """Torta con título y leyenda. ``mostrar`` recibe pares ``(etiqueta, valor)``."""

    def __init__(self, master: Any, titulo: str, *, diametro: int = 150,
                 formato: Callable[[float], str] = lambda v: f"{v:g}"):
        super().__init__(master, corner_radius=RADIO, fg_color=FONDO, border_width=1,
                         border_color=BORDE)
        self._formato = formato
        self._datos: list[tuple[str, float]] = []
        escala = self._get_widget_scaling()
        self._lado = int(diametro * escala)
        self._letra = -round(12 * escala)  # tk no escala sus fuentes en puntos
        ctk.CTkLabel(self, text=titulo, font=(SEMINEGRITA, 12), anchor="w").pack(
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

    def _pintar(self, filas: list[str]) -> None:
        # La referencia se guarda: tk descarta la imagen si nadie más la tiene.
        self._imagen = tk.PhotoImage(master=self._lienzo, width=self._lado,
                                     height=self._lado)
        self._imagen.put(" ".join(filas))
        self._lienzo.create_image(0, 0, anchor="nw", image=self._imagen)

    def _dibujar(self) -> None:
        c = colores_tema()
        self._lienzo.configure(bg=c["fondo"])
        self._leyenda.configure(bg=c["fondo"])
        self._lienzo.delete("all")
        for hijo in self._leyenda.winfo_children():
            hijo.destroy()
        total = sum(v for _e, v in self._datos)
        if not total:
            self._pintar(_pixeles(self._lado, (), (), c["fondo"], aro=c["borde"]))
            self._lienzo.create_text(self._lado / 2, self._lado / 2, text="Sin datos",
                                     fill=c["texto_suave"], font=("Segoe UI", self._letra))
            return
        colores = tuple(
            elegir(OTROS if etiqueta == "Otros" and indice == MAX_PORCIONES - 1
                   else PALETA[indice % len(PALETA)])
            for indice, (etiqueta, _v) in enumerate(self._datos))
        self._pintar(_pixeles(self._lado, tuple(v / total for _e, v in self._datos),
                              colores, c["fondo"]))
        for (etiqueta, valor), color in zip(self._datos, colores):
            fila = tk.Frame(self._leyenda, bg=c["fondo"])
            fila.pack(fill="x", pady=1)
            tk.Label(fila, text="■", fg=color, bg=c["fondo"],
                     font=("Segoe UI", self._letra)).pack(side="left")
            tk.Label(fila, text=etiqueta, fg=c["texto"], bg=c["fondo"], anchor="w",
                     font=("Segoe UI", self._letra)).pack(side="left", padx=(4, 8))
            tk.Label(fila, text=f"{self._formato(valor)} · {100 * valor / total:.0f} %",
                     fg=c["texto_suave"], bg=c["fondo"],
                     font=("Segoe UI", self._letra)).pack(side="right")
