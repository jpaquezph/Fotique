"""Selector de fecha con calendario desplegable.

El calendario se arma con widgets ``tk`` simples (abre al instante) y tiene
tres niveles: días ➜ meses ➜ años. Un clic en el título sube de nivel, así que
llegar a una fecha de hace varios años son tres clics: año, mes, día. La grilla
de años arranca en 2010, de modo que hoy se ve entera sin cambiar de página.
"""

from __future__ import annotations

import time
import tkinter as tk
from datetime import date, timedelta
from typing import Any, Callable, Optional

import customtkinter as ctk

from ..util import fecha_legible
from .theme import (
    BOTONES,
    FUENTE_NORMAL,
    NEUTRO,
    NEUTRO_HOVER,
    TEXTO,
    area_de_trabajo,
    colores_tema,
    elegir,
)

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
ANIO_BASE = 2010          # primer año de la página que se ve hoy
ANIOS_POR_PAGINA = 24
COLUMNAS_ANIOS = 4


def parsear(texto: str) -> Optional[date]:
    try:
        dia, mes, anio = (int(p) for p in (texto or "").strip().split("/"))
        return date(anio, mes, dia)
    except ValueError:
        return None


class Calendario(tk.Toplevel):
    """Desplegable sin bordes; se cierra al elegir, con Escape o al hacer clic
    en otra parte de la ventana."""

    def __init__(self, ancla: tk.Misc, fecha: Optional[date],
                 al_elegir: Callable[[Optional[date]], None], *, opcional: bool = True):
        super().__init__(ancla)
        self.overrideredirect(True)
        self._al_elegir = al_elegir
        self._elegida = fecha
        base = fecha or date.today()
        self._anio, self._mes = base.year, base.month
        self._modo = "dias"

        c = colores_tema()
        self._c = c
        # Tamaño en píxeles (negativo) según el escalado: las fuentes de tk en
        # puntos no siguen el escalado de pantalla que aplica CustomTkinter.
        self._letra = -round(13 * ctk.ScalingTracker.get_widget_scaling(ancla))
        self._acento = elegir(BOTONES["primario"][0])
        self._texto_acento = "#ffffff"
        self.configure(bg=c["borde"])
        marco = tk.Frame(self, bg=c["fondo"])
        marco.pack(padx=1, pady=1)

        cabecera = tk.Frame(marco, bg=c["fondo"])
        cabecera.pack(fill="x", padx=6, pady=(6, 2))
        self._boton(cabecera, "‹", lambda: self._mover(-1)).pack(side="left")
        self._boton(cabecera, "›", lambda: self._mover(1)).pack(side="right")
        self._titulo = self._boton(cabecera, "", self._subir_nivel, negrita=True)
        self._titulo.pack(side="left", fill="x", expand=True, padx=4)

        self._grilla = tk.Frame(marco, bg=c["fondo"])
        self._grilla.pack(padx=6, pady=2)

        pie = tk.Frame(marco, bg=c["fondo"])
        pie.pack(fill="x", padx=6, pady=(2, 6))
        self._boton(pie, "Hoy", lambda: self._elegir(date.today())).pack(side="left")
        if opcional:
            self._boton(pie, "Sin fecha", lambda: self._elegir(None)).pack(side="right")

        self._dibujar()
        self.update_idletasks()
        x0, y0, ancho_area, alto_area = area_de_trabajo(self)
        x = ancla.winfo_rootx()
        y = ancla.winfo_rooty() + ancla.winfo_height() + 2
        if y + self.winfo_reqheight() > y0 + alto_area:  # no entra abajo: va arriba
            y = max(y0, ancla.winfo_rooty() - self.winfo_reqheight() - 2)
        x = max(x0, min(x, x0 + ancho_area - self.winfo_reqwidth() - 8))
        self.geometry(f"+{x}+{y}")
        self.bind("<Escape>", lambda _e: self.destroy())
        # Un clic en cualquier otro lugar de la ventana dueña lo cierra. El
        # enlace se instala una vez por ventana y consulta el calendario abierto.
        duena = ancla.winfo_toplevel()
        if not getattr(duena, "_fotique_cierra_calendario", False):
            duena._fotique_cierra_calendario = True
            duena.bind("<Button-1>", lambda _e, d=duena: _cerrar_abierto(d), add="+")
        duena._fotique_calendario = self
        self.transient(duena)  # acompaña a su ventana al cambiar de aplicación
        self.lift()
        self.focus_force()

    # -- piezas -------------------------------------------------------------- #
    def _boton(self, master: tk.Misc, texto: str, comando: Callable[[], None], *,
               negrita: bool = False, ancho: int = 0) -> tk.Label:
        c = self._c
        etiqueta = tk.Label(master, text=texto, bg=c["fondo"], fg=c["texto"],
                            font=("Segoe UI", self._letra, "bold" if negrita else "normal"),
                            padx=8, pady=4, width=ancho, cursor="hand2")
        etiqueta.bind("<Button-1>", lambda _e: comando())
        etiqueta.bind("<Enter>", lambda _e: etiqueta.configure(bg=c["resalte"]))
        etiqueta.bind("<Leave>", lambda _e: etiqueta.configure(bg=c["fondo"]))
        return etiqueta

    def _celda(self, fila: int, columna: int, texto: str,
               comando: Optional[Callable[[], None]], *, ancho: int,
               marcada: bool = False, tenue: bool = False, hoy: bool = False) -> None:
        c = self._c
        fondo = self._acento if marcada else c["resalte"] if hoy else c["fondo"]
        color = (self._texto_acento if marcada
                 else c["texto_suave"] if tenue else c["texto"])
        celda = tk.Label(self._grilla, text=texto, width=ancho, pady=5, bg=fondo, fg=color,
                         font=("Segoe UI", self._letra, "bold" if marcada or hoy else "normal"),
                         cursor="hand2" if comando else "")
        celda.grid(row=fila, column=columna, padx=1, pady=1)
        if comando is not None:
            celda.bind("<Button-1>", lambda _e: comando())
            if not marcada:
                celda.bind("<Enter>", lambda _e: celda.configure(bg=c["borde"]))
                celda.bind("<Leave>", lambda _e: celda.configure(bg=fondo))

    def _dibujar(self) -> None:
        for hijo in self._grilla.winfo_children():
            hijo.destroy()
        getattr(self, f"_dibujar_{self._modo}")()

    def _dibujar_dias(self) -> None:
        self._titulo.configure(text=f"{MESES[self._mes - 1]} {self._anio}")
        for columna, dia in enumerate(DIAS):
            self._celda(0, columna, dia, None, ancho=3, tenue=True)
        primero = date(self._anio, self._mes, 1)
        inicio = primero - timedelta(days=primero.weekday())
        hoy = date.today()
        for indice in range(42):
            dia = inicio + timedelta(days=indice)
            self._celda(1 + indice // 7, indice % 7, str(dia.day),
                        lambda d=dia: self._elegir(d), ancho=3,
                        marcada=dia == self._elegida, hoy=dia == hoy,
                        tenue=dia.month != self._mes)

    def _dibujar_meses(self) -> None:
        self._titulo.configure(text=str(self._anio))
        for indice, mes in enumerate(MESES):
            marcada = (self._elegida is not None and self._elegida.year == self._anio
                       and self._elegida.month == indice + 1)
            self._celda(indice // 3, indice % 3, mes[:3],
                        lambda m=indice + 1: self._ir_a(mes=m), ancho=8, marcada=marcada)

    def _dibujar_anios(self) -> None:
        inicio = ANIO_BASE + (self._anio - ANIO_BASE) // ANIOS_POR_PAGINA * ANIOS_POR_PAGINA
        self._titulo.configure(text=f"{inicio} – {inicio + ANIOS_POR_PAGINA - 1}")
        for indice in range(ANIOS_POR_PAGINA):
            anio = inicio + indice
            if not 1 <= anio <= 9999:
                continue
            self._celda(indice // COLUMNAS_ANIOS, indice % COLUMNAS_ANIOS, str(anio),
                        lambda a=anio: self._ir_a(anio=a), ancho=6,
                        marcada=self._elegida is not None and self._elegida.year == anio,
                        hoy=anio == date.today().year)

    # -- navegación ---------------------------------------------------------- #
    def _mover(self, paso: int) -> None:
        if self._modo == "dias":
            indice = self._anio * 12 + self._mes - 1 + paso
            self._anio, self._mes = indice // 12, indice % 12 + 1
        elif self._modo == "meses":
            self._anio += paso
        else:
            self._anio += paso * ANIOS_POR_PAGINA
        self._anio = min(max(self._anio, 1), 9999)
        self._dibujar()

    def _subir_nivel(self) -> None:
        self._modo = {"dias": "anios", "anios": "meses", "meses": "dias"}[self._modo]
        self._dibujar()

    def _ir_a(self, *, anio: Optional[int] = None, mes: Optional[int] = None) -> None:
        if anio is not None:
            self._anio, self._modo = anio, "meses"
        if mes is not None:
            self._mes, self._modo = mes, "dias"
        self._dibujar()

    def _elegir(self, fecha: Optional[date]) -> None:
        self._al_elegir(fecha)
        self.destroy()

    def destroy(self) -> None:
        self.cerrado_en = time.monotonic()
        super().destroy()


def _cerrar_abierto(duena: tk.Misc) -> None:
    calendario = getattr(duena, "_fotique_calendario", None)
    if calendario is not None and calendario.winfo_exists():
        calendario.destroy()


class SelectorFecha(ctk.CTkFrame):
    """Campo de fecha: muestra ``dd/mm/aaaa`` y se elige desde el calendario."""

    def __init__(self, master: Any, valor: Optional[date] = None, *,
                 opcional: bool = True, ancho: int = 160,
                 al_cambiar: Optional[Callable[[Optional[date]], Any]] = None):
        """``al_cambiar(fecha)`` avisa cada vez que se elige o se borra la fecha."""
        super().__init__(master, fg_color="transparent")
        self._opcional = opcional
        self._al_cambiar = None  # recién después de cargar el valor inicial
        self._calendario: Optional[Calendario] = None
        self._entrada = ctk.CTkEntry(self, width=ancho - 40, font=FUENTE_NORMAL,
                                     placeholder_text="Sin fecha")
        self._entrada.pack(side="left")
        self._boton = ctk.CTkButton(self, text="▾", width=34, command=self.abrir,
                                    fg_color=NEUTRO, hover_color=NEUTRO_HOVER,
                                    text_color=TEXTO)
        self._boton.pack(side="left", padx=(6, 0))
        # "break": el clic no le da el foco al campo, que cerraría el calendario.
        self._entrada.bind("<Button-1>", lambda _e: (self.abrir(), "break")[1])
        # Sólo se elige del calendario: se descarta lo que se intente tipear.
        self._entrada.bind("<Key>", self._al_teclear)
        self.set(valor)
        self._al_cambiar = al_cambiar

    def _al_teclear(self, evento: tk.Event) -> Optional[str]:
        if evento.keysym in ("Tab", "ISO_Left_Tab", "Escape", "Return"):
            return None
        if evento.keysym in ("space", "Down"):
            self.abrir()
        elif evento.keysym in ("Delete", "BackSpace") and self._opcional:
            self.set(None)
        return "break"

    def abrir(self) -> None:
        anterior = self._calendario
        if anterior is not None:
            if anterior.winfo_exists():
                anterior.destroy()
                return
            # El clic en ▾ ya lo cerró (clic fuera del calendario): no reabrirlo.
            if time.monotonic() - getattr(anterior, "cerrado_en", 0) < 0.4:
                self._calendario = None
                return
        self._calendario = Calendario(self._entrada, self.fecha(), self.set,
                                      opcional=self._opcional)

    def set(self, valor: Optional[date]) -> None:
        self._entrada.delete(0, "end")
        if valor is not None:
            self._entrada.insert(0, fecha_legible(valor))
        else:  # CTkEntry sólo repone el texto de ayuda al perder el foco
            self._entrada._activate_placeholder()
        if self._al_cambiar is not None:
            self._al_cambiar(valor)

    def get(self) -> str:
        return self._entrada.get()

    def fecha(self) -> Optional[date]:
        return parsear(self.get())
