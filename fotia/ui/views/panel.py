"""Panel de control: resumen operativo y alertas."""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from ...domain.models import EstadoService
from ...util import fecha_legible, moneda
from ..theme import (
    GRIS_TEXTO,
    NARANJA,
    ROJO,
    VERDE,
    colores_tema,
)
from ..widgets import Tarjeta
from .base import VistaBase


class VistaPanel(VistaBase):
    clave = "panel"
    titulo = "Panel de control"
    descripcion = "Estado general del estudio hoy"

    def _construir(self) -> None:
        c = colores_tema()
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(2, weight=1)
        contenedor.grid_columnconfigure(2, weight=1)

        self._tarjetas: dict[str, Tarjeta] = {}
        fila_tarjetas = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila_tarjetas.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        for i in range(6):
            fila_tarjetas.grid_columnconfigure(i, weight=1, uniform="tarjeta")
        for i, (clave, titulo) in enumerate([
            ("equipos", "Equipos"),
            ("en_uso", "En uso"),
            ("fotografos", "Fotógrafos"),
            ("proyectos", "Proyectos"),
            ("entregas", "Entregas abiertas"),
            ("saldo", "Saldo a cobrar"),
        ]):
            tarjeta = Tarjeta(fila_tarjetas, titulo)
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            self._tarjetas[clave] = tarjeta

        self._panel_service = self._crear_panel(contenedor, "Alertas de service (RF-03)", 1, 0)
        self._panel_eventos = self._crear_panel(contenedor, "Próximos eventos", 1, 1)
        self._panel_saldos = self._crear_panel(contenedor, "Saldos por cobrar (RF-05)", 1, 2)

        self._estado = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                    text_color=GRIS_TEXTO, anchor="w")
        self._estado.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        del c

    def _crear_panel(self, master, titulo: str, fila: int, columna: int):
        marco = ctk.CTkFrame(master, corner_radius=10)
        marco.grid(row=fila, column=columna, sticky="nsew", padx=(0, 8), pady=(0, 8))
        marco.grid_rowconfigure(1, weight=1)
        marco.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(marco, text=titulo, font=("Segoe UI", 12, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14,
                                      pady=(12, 4))
        contenido = ctk.CTkScrollableFrame(marco, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))
        contenido.grid_columnconfigure(0, weight=1)
        return contenido

    def _fila_lista(self, contenedor, indice: int, principal: str,
                    secundario: str = "", color: str | None = None) -> None:
        c = colores_tema()
        marco = ctk.CTkFrame(contenedor, fg_color="transparent")
        marco.grid(row=indice, column=0, sticky="ew", pady=3)
        marco.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(marco, text=principal, font=("Segoe UI", 11),
                     text_color=color or c["texto"], anchor="w",
                     wraplength=280, justify="left").grid(row=0, column=0,
                                                          sticky="w")
        if secundario:
            ctk.CTkLabel(marco, text=secundario, font=("Segoe UI", 10),
                         text_color=GRIS_TEXTO, anchor="e").grid(
                row=0, column=1, sticky="e", padx=(8, 0))

    def _vaciar(self, contenedor) -> None:
        for hijo in contenedor.winfo_children():
            hijo.destroy()

    def refrescar(self) -> None:
        hoy = date.today()
        resumen = self.repos.resumen()
        proyectos = self.repos.proyectos.listar()
        saldo_total = sum(max(p.obtener_saldo_pendiente(), 0) for p in proyectos)
        alertas = self.repos.equipos.alertas_service(dias_aviso=30, hoy=hoy)

        self._tarjetas["equipos"].set_valor(resumen["equipos"])
        self._tarjetas["en_uso"].set_valor(resumen["en_uso"])
        self._tarjetas["fotografos"].set_valor(resumen["fotografos"])
        self._tarjetas["proyectos"].set_valor(resumen["proyectos"])
        self._tarjetas["entregas"].set_valor(resumen["trabajos_abiertos"])
        self._tarjetas["saldo"].set_valor(moneda(saldo_total),
                                          color=NARANJA if saldo_total else VERDE)

        # -- service -------------------------------------------------------- #
        self._vaciar(self._panel_service)
        if not alertas:
            self._fila_lista(self._panel_service, 0, "Sin alertas de service.",
                             color=VERDE)
        for indice, (equipo, estado) in enumerate(alertas):
            color = ROJO if estado == EstadoService.VENCIDO else NARANJA
            texto = ("Vencido" if estado == EstadoService.VENCIDO
                     else f"En {(equipo.fecha_service_proximo - hoy).days} día(s)")
            responsable = (equipo.fotografo_actual.nombre_completo
                           if equipo.fotografo_actual else "Sin asignar")
            self._fila_lista(
                self._panel_service, indice,
                f"{equipo.descripcion} ({equipo.numero_serie})",
                f"{texto} · {fecha_legible(equipo.fecha_service_proximo)} · {responsable}",
                color=color,
            )

        # -- eventos -------------------------------------------------------- #
        self._vaciar(self._panel_eventos)
        eventos = self.repos.eventos.consolidado(hoy, hoy + timedelta(days=21))
        if not eventos:
            self._fila_lista(self._panel_eventos, 0, "No hay eventos en las próximas 3 semanas.",
                             color=GRIS_TEXTO)
        for indice, evento in enumerate(eventos[:14]):
            dias = (evento.fecha - hoy).days
            when = ("Hoy" if dias == 0 else
                    "Mañana" if dias == 1 else fecha_legible(evento.fecha))
            self._fila_lista(
                self._panel_eventos, indice,
                evento.titulo,
                f"{when} {evento.hora}".strip(),
                color=NARANJA if dias <= 1 else None,
            )

        # -- saldos --------------------------------------------------------- #
        self._vaciar(self._panel_saldos)
        pendientes = sorted(
            (p for p in proyectos if p.obtener_saldo_pendiente() > 0),
            key=lambda p: p.obtener_saldo_pendiente(), reverse=True,
        )
        if not pendientes:
            self._fila_lista(self._panel_saldos, 0, "Todos los proyectos están saldados.",
                             color=VERDE)
        for indice, proyecto in enumerate(pendientes[:14]):
            self._fila_lista(
                self._panel_saldos, indice,
                f"{proyecto.nombre} — {proyecto.cliente}",
                moneda(proyecto.obtener_saldo_pendiente()),
                color=NARANJA,
            )

        self._estado.configure(
            text=f"Base: {self.app.ruta_db} · {resumen['equipos']} equipos · "
            f"{resumen['eventos']} eventos de agenda · "
            f"{resumen['contratos']} contratos · actualizado "
            f"{hoy.strftime('%d/%m/%Y')}"
        )


__all__ = ["VistaPanel"]
