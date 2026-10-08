"""Resumen general: estado operativo del estudio y alertas."""

from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from tkinter import font as tkfont
from typing import Optional

import customtkinter as ctk

from ...domain.models import EstadoEquipo
from ...util import fecha_legible, moneda
from ..theme import (
    BORDE,
    FONDO,
    FUENTE_ETIQUETA,
    FUENTE_PEQUE,
    FUENTE_SUBTITULO,
    GRIS_TEXTO,
    NARANJA,
    RADIO,
    RELLENOS,
    ROJO,
    SEMINEGRITA,
    TEXTO,
    TEXTO_SUAVE,
    VERDE,
    Color,
    elegir,
)
from ..widgets import Tarjeta
from .base import VistaBase

Fila = tuple[str, str, Color]  # (principal, secundario, color)


class _Lista(tk.Canvas):
    """Lista de filas dibujada en un único lienzo.

    Cada fila hecha con widgets de CustomTkinter son varias ventanas nativas, y
    repintarlas todas era lo que más demoraba al volver a esta pantalla.
    """

    ALTO_FILA = 33
    MARGEN = 8

    def __init__(self, master: ctk.CTkFrame):
        super().__init__(master, bd=0, highlightthickness=0, bg=elegir(FONDO))
        self._mostrado: list[Fila] = []
        # Tamaño en píxeles (negativo) según el escalado: las fuentes de tk en
        # puntos no siguen el escalado de pantalla que aplica CustomTkinter.
        self._escala = ctk.ScalingTracker.get_widget_scaling(master)
        self._fuente = tkfont.Font(self, family=SEMINEGRITA, size=-round(12 * self._escala))
        self._fuente_chica = tkfont.Font(self, family=FUENTE_ETIQUETA[0],
                                         size=-round(FUENTE_ETIQUETA[1] * self._escala))
        self._ancho = 0
        self.bind("<Configure>", self._al_cambiar_tamano)
        self.bind("<MouseWheel>", self._al_rodar)

    def mostrar(self, filas: list[Fila]) -> None:
        if filas != self._mostrado:
            self._mostrado = list(filas)
            self.dibujar()

    def _al_cambiar_tamano(self, evento) -> None:
        if evento.width != self._ancho:
            self._ancho = evento.width
            self.dibujar()

    def _al_rodar(self, evento) -> None:
        if self.yview() != (0.0, 1.0):  # sólo si no entra todo
            self.yview_scroll(-1 if evento.delta > 0 else 1, "units")

    def _recortar(self, texto: str, ancho: int) -> str:
        if self._fuente.measure(texto) <= ancho:
            return texto
        while texto and self._fuente.measure(texto + "…") > ancho:
            texto = texto[:-1]
        return texto.rstrip() + "…"

    def dibujar(self) -> None:
        """Vuelve a trazar las filas (también al cambiar de modo claro/oscuro)."""
        self.delete("all")
        self.configure(bg=elegir(FONDO))
        ancho = self._ancho or self.winfo_width()
        alto_fila = round(self.ALTO_FILA * self._escala)
        margen = round(self.MARGEN * self._escala)
        suave = elegir(TEXTO_SUAVE)
        for indice, (principal, secundario, color) in enumerate(self._mostrado):
            y = indice * alto_fila + alto_fila // 2
            libre = ancho - 2 * margen
            if secundario:
                self.create_text(ancho - margen, y, text=secundario, anchor="e",
                                 font=self._fuente_chica, fill=suave)
                libre -= self._fuente_chica.measure(secundario) + 2 * margen
            self.create_text(margen, y, text=self._recortar(principal, max(libre, 0)),
                             anchor="w", font=self._fuente, fill=elegir(color))
        self.configure(scrollregion=(0, 0, ancho, len(self._mostrado) * alto_fila),
                       yscrollincrement=alto_fila)

class VistaPanel(VistaBase):
    clave = "panel"
    titulo = "Resumen general"
    descripcion = "Estado general del estudio hoy"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        for columna in range(3):
            contenedor.grid_columnconfigure(columna, weight=1, uniform="panel")

        self._tarjetas: dict[str, Tarjeta] = {}
        fila_tarjetas = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila_tarjetas.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 16))
        for i in range(6):
            fila_tarjetas.grid_columnconfigure(i, weight=1, uniform="tarjeta")
        for i, (clave, titulo, color) in enumerate([
            ("equipos", "Equipos", "celeste"),
            ("en_uso", "En uso", "azul"),
            ("fotografos", "Fotógrafos", "indigo"),
            ("proyectos", "Proyectos", "violeta"),
            ("entregas", "Entregas abiertas", "malva"),
            ("saldo", "Saldo a cobrar", "verde"),
        ]):
            tarjeta = Tarjeta(fila_tarjetas, titulo, relleno=RELLENOS[color],
                              compacta=True)
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            self._tarjetas[clave] = tarjeta

        self._service = self._crear_panel(contenedor, "Inventario", 0)
        self._eventos = self._crear_panel(contenedor, "Próximos eventos", 1)
        self._saldos = self._crear_panel(contenedor, "Saldos por cobrar", 2)

        self._estado = ctk.CTkLabel(contenedor, text="", font=FUENTE_PEQUE,
                                    text_color=GRIS_TEXTO, anchor="w")
        self._estado.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self._estado_actual: Optional[str] = None

    def _crear_panel(self, master, titulo: str, columna: int) -> _Lista:
        marco = ctk.CTkFrame(master, corner_radius=RADIO, fg_color=FONDO,
                             border_width=1, border_color=BORDE)
        marco.grid(row=1, column=columna, sticky="nsew",
                   padx=(0, 0 if columna == 2 else 12), pady=(0, 8))
        marco.grid_rowconfigure(2, weight=1)
        marco.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(marco, text=titulo, font=FUENTE_SUBTITULO,
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=18,
                                      pady=(14, 8))
        ctk.CTkFrame(marco, height=2, corner_radius=0, fg_color=BORDE).grid(
            row=1, column=0, sticky="ew", padx=18)
        lista = _Lista(marco)
        lista.grid(row=2, column=0, sticky="nsew", padx=10, pady=(6, 14))
        return lista

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        for nombre in ("_service", "_eventos", "_saldos"):
            lista = getattr(self, nombre, None)
            if lista is not None:  # el lienzo de tk no sigue el modo por su cuenta
                lista.dibujar()

    def refrescar(self) -> None:
        hoy = date.today()
        resumen = self.repos.resumen()
        proyectos = self.repos.proyectos.listar()
        saldos = [(p, p.obtener_saldo_pendiente()) for p in proyectos]
        saldo_total = sum(max(saldo, 0) for _p, saldo in saldos)

        self._tarjetas["equipos"].set_valor(resumen["equipos"])
        self._tarjetas["en_uso"].set_valor(resumen["en_uso"])
        self._tarjetas["fotografos"].set_valor(resumen["fotografos"])
        self._tarjetas["proyectos"].set_valor(resumen["proyectos"])
        self._tarjetas["entregas"].set_valor(resumen["trabajos_abiertos"])
        self._tarjetas["saldo"].set_valor(moneda(saldo_total))

        # -- inventario ----------------------------------------------------- #
        # Verde: disponible (en stock). Rojo: no disponible (en uso). A la
        # derecha, la fecha del próximo service.
        equipos = sorted(self.repos.equipos.listar(),
                         key=lambda e: e.estado != EstadoEquipo.EN_STOCK)
        filas: list[Fila] = [
            (equipo.producto or equipo.descripcion,
             fecha_legible(equipo.fecha_service_proximo),
             VERDE if equipo.estado == EstadoEquipo.EN_STOCK else ROJO)
            for equipo in equipos
        ]
        self._service.mostrar(filas or [("Sin equipos cargados.", "", GRIS_TEXTO)])

        # -- eventos -------------------------------------------------------- #
        filas = []
        eventos = self.repos.eventos.consolidado(hoy, hoy + timedelta(days=21))
        for evento in eventos[:14]:
            dias = (evento.fecha - hoy).days
            cuando = ("Hoy" if dias == 0 else
                      "Mañana" if dias == 1 else fecha_legible(evento.fecha))
            filas.append((evento.titulo, f"{cuando} {evento.hora}".strip(),
                          NARANJA if dias <= 1 else TEXTO))
        self._eventos.mostrar(
            filas or [("No hay eventos en las próximas 3 semanas.", "", GRIS_TEXTO)])

        # -- saldos --------------------------------------------------------- #
        pendientes = sorted(((p, s) for p, s in saldos if s > 0),
                            key=lambda par: par[1], reverse=True)
        filas = [(f"{p.nombre} — {p.cliente}" if p.cliente else p.nombre,
                  moneda(saldo), NARANJA)
                 for p, saldo in pendientes[:14]]
        self._saldos.mostrar(
            filas or [("Todos los proyectos están saldados.", "", VERDE)])

        estado = (f"Base: {self.app.ruta_db} · {resumen['equipos']} equipos · "
                  f"{resumen['eventos']} eventos de agenda · "
                  f"{resumen['contratos']} contratos · actualizado "
                  f"{hoy.strftime('%d/%m/%Y')}")
        if estado != self._estado_actual:
            self._estado_actual = estado
            self._estado.configure(text=estado)


__all__ = ["VistaPanel"]
