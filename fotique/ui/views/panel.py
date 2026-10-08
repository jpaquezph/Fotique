"""Panel de control: resumen operativo y alertas."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import customtkinter as ctk

from ...domain.models import EstadoEquipo
from ...util import fecha_legible, moneda
from ..theme import (
    BORDE,
    FONDO,
    GRIS_TEXTO,
    NARANJA,
    RELLENOS,
    ROJO,
    TEXTO,
    TEXTO_SUAVE,
    VERDE,
    Color,
)
from ..widgets import Tarjeta
from .base import VistaBase

Fila = tuple[str, str, Color]  # (principal, secundario, color)


class _Lista:
    """Lista de filas que reutiliza sus widgets entre refrescos.

    Crear y destruir widgets de CustomTkinter es lo más caro del panel; acá las
    filas se crean una vez y después solo se les cambia el texto.
    """

    def __init__(self, contenedor: ctk.CTkScrollableFrame):
        self._contenedor = contenedor
        self._filas: list[tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = []
        self._mostrado: list[Fila] = []

    def mostrar(self, filas: list[Fila]) -> None:
        if filas == self._mostrado:
            return
        for indice, (principal, secundario, color) in enumerate(filas):
            if indice == len(self._filas):
                self._filas.append(self._crear(indice))
            marco, lbl_principal, lbl_secundario = self._filas[indice]
            if indice >= len(self._mostrado) or self._mostrado[indice] != filas[indice]:
                lbl_principal.configure(text=principal, text_color=color)
                lbl_secundario.configure(text=secundario)
            if indice >= len(self._mostrado):
                marco.grid()
        for marco, _p, _s in self._filas[len(filas):len(self._mostrado)]:
            marco.grid_remove()
        self._mostrado = list(filas)

    def _crear(self, indice: int):
        marco = ctk.CTkFrame(self._contenedor, fg_color="transparent")
        marco.grid(row=indice, column=0, sticky="ew", pady=3, padx=(0, 16))
        marco.grid_columnconfigure(0, weight=1)
        principal = ctk.CTkLabel(marco, text="", font=("Segoe UI", 12, "bold"), anchor="w",
                                 wraplength=280, justify="left")
        principal.grid(row=0, column=0, sticky="w")
        secundario = ctk.CTkLabel(marco, text="", font=("Segoe UI", 11, "bold"),
                                  text_color=TEXTO_SUAVE, anchor="e")
        secundario.grid(row=0, column=1, sticky="e", padx=(8, 0))
        return marco, principal, secundario


class VistaPanel(VistaBase):
    clave = "panel"
    titulo = "Panel de control"
    descripcion = "Estado general del estudio hoy"

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        for columna in range(3):
            contenedor.grid_columnconfigure(columna, weight=1, uniform="panel")

        self._tarjetas: dict[str, Tarjeta] = {}
        fila_tarjetas = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila_tarjetas.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))
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
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            self._tarjetas[clave] = tarjeta

        self._service = self._crear_panel(contenedor, "Inventario", 0)
        self._eventos = self._crear_panel(contenedor, "Próximos eventos", 1)
        self._saldos = self._crear_panel(contenedor, "Saldos por cobrar", 2)

        self._estado = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11, "bold"),
                                    text_color=GRIS_TEXTO, anchor="w")
        self._estado.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self._estado_actual: Optional[str] = None

    def _crear_panel(self, master, titulo: str, columna: int) -> _Lista:
        marco = ctk.CTkFrame(master, corner_radius=10, fg_color=FONDO,
                             border_width=1, border_color=BORDE)
        marco.grid(row=1, column=columna, sticky="nsew", padx=(0, 8), pady=(0, 8))
        marco.grid_rowconfigure(1, weight=1)
        marco.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(marco, text=titulo, font=("Segoe UI", 13, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14,
                                      pady=(12, 4))
        contenido = ctk.CTkScrollableFrame(marco, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))
        contenido.grid_columnconfigure(0, weight=1)
        return _Lista(contenido)

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
            (equipo.descripcion, fecha_legible(equipo.fecha_service_proximo),
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
