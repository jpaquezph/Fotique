"""Módulo D — Calendario general del estudio (RF-08)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

import customtkinter as ctk

from ...domain.models import Evento
from ..dialogs import DialogoEvento, DialogoTabla
from ..theme import ACENTO, ACENTO_HOVER, GRIS_TEXTO, ROJO, colores_tema
from ..widgets import Tabla, boton, boton_secundario
from .base import VistaBase

DIAS_CABECERA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


class VistaCalendario(VistaBase):
    clave = "calendario"
    titulo = "Calendario general"
    descripcion = ("Módulo D · eventos de clientes, entregas, service y agenda "
                   "personal en una sola vista (RF-08)")

    def _construir(self) -> None:
        c = colores_tema()
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(1, weight=1)

        hoy = date.today()
        self._mes = hoy.replace(day=1)
        self._dia = hoy

        # -- barra superior ------------------------------------------------- #
        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        boton_secundario(barra, "◀", lambda: self._mover_mes(-1), ancho=42).pack(
            side="left", padx=(0, 6))
        self._etiqueta_mes = ctk.CTkLabel(barra, text="", font=("Segoe UI", 14, "bold"),
                                          width=210, anchor="w")
        self._etiqueta_mes.pack(side="left", padx=(0, 6))
        boton_secundario(barra, "▶", lambda: self._mover_mes(1), ancho=42).pack(
            side="left", padx=(0, 10))
        boton_secundario(barra, "Hoy", self._ir_hoy, ancho=70).pack(
            side="left", padx=(0, 14))

        boton(barra, "Nuevo evento", self._nuevo_evento).pack(side="left", padx=(0, 6))
        boton_secundario(barra, "Editar evento", self._editar_evento).pack(
            side="left", padx=(0, 6))
        boton(barra, "Eliminar", self._eliminar_evento, color=ROJO).pack(
            side="left", padx=(0, 6))
        boton_secundario(barra, "Ver todo el mes", self._ver_mes).pack(
            side="left", padx=(0, 6))

        self._filtro = ctk.StringVar(value="Todos los fotógrafos")
        self._menu_fotografos = ctk.CTkOptionMenu(
            barra, values=["Todos los fotógrafos"], variable=self._filtro,
            width=210, dynamic_resizing=False, command=lambda _v: self.refrescar(),
        )
        self._menu_fotografos.pack(side="right")

        # -- calendario ------------------------------------------------------ #
        panel_mes = ctk.CTkFrame(contenedor, fg_color="transparent")
        panel_mes.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        panel_mes.grid_columnconfigure(6, weight=1)
        panel_mes.grid_rowconfigure(6, weight=1)

        for i, dia in enumerate(DIAS_CABECERA):
            ctk.CTkLabel(panel_mes, text=dia, font=("Segoe UI", 11, "bold"),
                         text_color=c["texto_suave"], width=54).grid(
                row=0, column=i, padx=2, pady=(0, 4))
        self._celdas: list[ctk.CTkButton] = []
        for indice in range(42):
            fila, columna = divmod(indice, 7)
            celda = ctk.CTkButton(
                panel_mes, text="", width=54, height=44, corner_radius=8,
                font=("Segoe UI", 11), fg_color="transparent",
                hover_color=c["borde"], anchor="center",
                command=lambda i=indice: self._seleccionar_celda(i),
            )
            celda.grid(row=fila + 1, column=columna, padx=2, pady=2, sticky="nsew")
            self._celdas.append(celda)

        # -- panel del día --------------------------------------------------- #
        panel_dia = ctk.CTkFrame(contenedor, fg_color="transparent")
        panel_dia.grid(row=1, column=1, sticky="nsew")
        panel_dia.grid_rowconfigure(1, weight=1)
        panel_dia.grid_columnconfigure(0, weight=1)

        self._etiqueta_dia = ctk.CTkLabel(panel_dia, text="", anchor="w",
                                          font=("Segoe UI", 13, "bold"))
        self._etiqueta_dia.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        columnas = [
            {"clave": "hora", "titulo": "Hora", "ancho": 70, "anchor": "center"},
            {"clave": "titulo", "titulo": "Evento", "ancho": 300},
            {"clave": "tipo", "titulo": "Tipo", "ancho": 100, "anchor": "center"},
            {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 150},
            {"clave": "proyecto", "titulo": "Proyecto", "ancho": 160},
        ]
        self.tabla = Tabla(panel_dia, columnas, doble_click=lambda _e: self._editar_evento(),
                           altura=14)
        self.tabla.grid(row=1, column=0, sticky="nsew")

        self._pie = ctk.CTkLabel(panel_dia, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w", wraplength=430,
                                 justify="left")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    # -- datos ------------------------------------------------------------- #
    def _id_fotografo_filtro(self):
        valor = self._filtro.get()
        if valor == "Todos los fotógrafos":
            return None
        for f in self.repos.fotografos.listar():
            if f.nombre_completo == valor:
                return f.id
        return None

    def refrescar(self, *_args) -> None:
        fotografos = [f.nombre_completo for f in self.repos.fotografos.listar()]
        valores = ["Todos los fotógrafos"] + fotografos
        actual = self._filtro.get()
        self._menu_fotografos.configure(values=valores)
        self._menu_fotografos.set(
            actual if actual in valores else "Todos los fotógrafos"
        )

        self._etiqueta_mes.configure(
            text=f"{MESES[self._mes.month - 1].capitalize()} de {self._mes.year}"
        )
        fotografo_id = self._id_fotografo_filtro()

        # eventos de toda la grilla (6 semanas) en una sola consulta
        inicio = self._inicio_grilla()
        fin = inicio + timedelta(days=41)
        eventos = self.repos.eventos.consolidado(inicio, fin, fotografo_id=fotografo_id)
        por_dia: dict[date, list[Evento]] = {}
        for evento in eventos:
            por_dia.setdefault(evento.fecha, []).append(evento)
        self._eventos_por_dia = por_dia

        c = colores_tema()
        primero = inicio
        for indice, celda in enumerate(self._celdas):
            dia = primero + timedelta(days=indice)
            fuera = dia.month != self._mes.month
            tiene = bool(por_dia.get(dia))
            texto = str(dia.day)
            if dia == self._dia:
                fondo, texto_color = ACENTO, "#ffffff"
                hover = ACENTO_HOVER
            elif dia == date.today():
                fondo, texto_color = c["borde"], c["texto"]
                hover = c["encabezado"]
            elif tiene:
                fondo = "#1f3b52" if c["texto"] == "#ffffff" else "#d8e9f7"
                texto_color = c["texto"]
                hover = c["encabezado"]
            else:
                fondo, texto_color = "transparent", c["texto"]
                hover = c["borde"]
            if fuera:
                texto_color = c["borde"]
            celda.configure(text=texto, fg_color=fondo, text_color=texto_color,
                            hover_color=hover,
                            font=("Segoe UI", 11, "bold" if tiene else "normal"))
        self._mostrar_dia()

    def _inicio_grilla(self) -> date:
        offset = self._mes.weekday()  # lunes = 0
        return self._mes - timedelta(days=offset)

    def _mostrar_dia(self) -> None:
        eventos = self._eventos_por_dia.get(self._dia, [])
        self._etiqueta_dia.configure(
            text=f"{DIAS_SEMANA[self._dia.weekday()]} {self._dia.day} de "
            f"{MESES[self._dia.month - 1]} · {len(eventos)} evento(s)"
        )
        filas = [
            [
                e.hora or "—",
                e.titulo,
                e.tipo,
                _nombre_fotografo(self.repos, e.fotografo_id),
                _nombre_proyecto(self.repos, e.proyecto_id),
            ]
            for e in eventos
        ]
        etiquetas = [_tag_tipo(e.tipo) for e in eventos]
        self.tabla.actualizar(filas, eventos, etiquetas)
        self._pie.configure(
            text="Los eventos de proyectos, entregas y service se generan solos; "
            "para editarlos use su módulo correspondiente."
            if not any(e.id for e in eventos) else
            "Use «Editar evento» para modificar los eventos de agenda propios."
        )

    # -- acciones ----------------------------------------------------------- #
    def _mover_mes(self, desplazamiento: int) -> None:
        anio, mes = self._mes.year, self._mes.month + desplazamiento
        if mes < 1:
            mes, anio = 12, anio - 1
        elif mes > 12:
            mes, anio = 1, anio + 1
        ultimo = monthrange(anio, mes)[1]
        self._mes = date(anio, mes, 1)
        if self._dia.month != mes or self._dia.year != anio:
            self._dia = date(anio, mes, min(self._dia.day, ultimo))
        self.refrescar()

    def _ir_hoy(self) -> None:
        self._dia = date.today()
        self._mes = self._dia.replace(day=1)
        self.refrescar()

    def _seleccionar_celda(self, indice: int) -> None:
        dia = self._inicio_grilla() + timedelta(days=indice)
        self._dia = dia
        if dia.month != self._mes.month:
            self._mes = dia.replace(day=1)
        self.refrescar()

    def _evento_seleccionado(self):
        evento = self.tabla.seleccionado()
        if evento is None:
            self.advertir("Sin selección", "Elija un evento del día.")
        return evento

    def _nuevo_evento(self) -> None:
        evento = DialogoEvento(
            self, self.repos.fotografos.listar(), self.repos.proyectos.listar(),
            self._dia,
        ).mostrar()
        if evento is None:
            return
        self.ejecutar(lambda: self.repos.eventos.crear(evento))

    def _editar_evento(self) -> None:
        evento = self._evento_seleccionado()
        if evento is None:
            return
        if evento.id is None:
            self.advertir(
                "Evento automático",
                "Este evento proviene de un proyecto, una entrega o un service.\n"
                "Edítelo en su módulo correspondiente.",
            )
            return
        editado = DialogoEvento(
            self, self.repos.fotografos.listar(), self.repos.proyectos.listar(),
            evento.fecha, evento,
        ).mostrar()
        if editado is None:
            return
        self.ejecutar(lambda: self.repos.eventos.actualizar(editado))

    def _eliminar_evento(self) -> None:
        evento = self._evento_seleccionado()
        if evento is None:
            return
        if evento.id is None:
            self.advertir("Evento automático",
                          "Los eventos de proyectos, entregas y service no se "
                          "pueden borrar desde aquí.")
            return
        if not self.confirmar("Eliminar evento", f"¿Eliminar «{evento.titulo}»?"):
            return
        self.ejecutar(lambda: self.repos.eventos.eliminar(evento.id))

    def _ver_mes(self) -> None:
        fotografo_id = self._id_fotografo_filtro()
        inicio = self._mes
        fin = self._mes.replace(day=monthrange(self._mes.year, self._mes.month)[1])
        eventos = self.repos.eventos.consolidado(inicio, fin, fotografo_id=fotografo_id)
        filas = [
            [
                e.fecha.strftime("%d/%m/%Y"),
                e.hora or "—",
                e.titulo,
                e.tipo,
                _nombre_fotografo(self.repos, e.fotografo_id),
            ]
            for e in eventos
        ]
        DialogoTabla(
            self, f"Agenda de {MESES[self._mes.month - 1]} {self._mes.year}",
            [
                {"clave": "fecha", "titulo": "Fecha", "ancho": 110, "anchor": "center"},
                {"clave": "hora", "titulo": "Hora", "ancho": 80, "anchor": "center"},
                {"clave": "titulo", "titulo": "Evento", "ancho": 340},
                {"clave": "tipo", "titulo": "Tipo", "ancho": 110, "anchor": "center"},
                {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 170},
            ],
            filas,
        ).mostrar()


def _tag_tipo(tipo: str) -> str:
    return {"Service": "proximo", "Entrega": "ok", "Sesión": "pendiente"}.get(tipo, "")


def _nombre_fotografo(repos, fotografo_id) -> str:
    if fotografo_id is None:
        return "—"
    fotografo = repos.fotografos.obtener(fotografo_id)
    return fotografo.nombre_completo if fotografo else "—"


def _nombre_proyecto(repos, proyecto_id) -> str:
    if proyecto_id is None:
        return "—"
    proyecto = repos.proyectos.obtener(proyecto_id)
    return (proyecto.titulo or "—") if proyecto else "—"
