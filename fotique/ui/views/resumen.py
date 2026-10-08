"""Resumen administrativo del negocio (sólo administradores)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import customtkinter as ctk

from ...util import fecha_legible, moneda
from ..dialogs import DialogoEgreso
from ..graficos import Torta
from ..theme import GRIS_TEXTO, RELLENOS
from ..widgets import Tabla, Tarjeta, boton, boton_secundario
from .base import VistaBase

SECCIONES = ["Dinero", "Equipos", "Personal y roles", "Clientes y contratos"]
PERIODOS = ["Este mes", "Últimos 3 meses", "Este año", "Año pasado", "Todo"]


def rango_periodo(periodo: str, hoy: Optional[date] = None
                  ) -> tuple[Optional[date], Optional[date]]:
    """``(desde, hasta)`` del período; ``None`` deja ese extremo abierto."""
    hoy = hoy or date.today()
    if periodo == "Este mes":
        siguiente = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1)
        return hoy.replace(day=1), siguiente - timedelta(days=1)
    if periodo == "Últimos 3 meses":
        return hoy - timedelta(days=90), hoy
    if periodo == "Este año":
        return date(hoy.year, 1, 1), date(hoy.year, 12, 31)
    if periodo == "Año pasado":
        return date(hoy.year - 1, 1, 1), date(hoy.year - 1, 12, 31)
    return None, None


class VistaResumen(VistaBase):
    clave = "resumen"
    titulo = "Resumen administrativo"
    descripcion = "Movimientos de dinero, equipos, personal, clientes y contratos"
    solo_admin = True

    def _construir(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.grid(row=1, column=0, sticky="nsew", padx=2)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._seccion = ctk.StringVar(value=SECCIONES[0])
        ctk.CTkSegmentedButton(barra, values=SECCIONES, variable=self._seccion,
                               command=lambda _v: self._mostrar_seccion()).pack(side="left")
        self._periodo = ctk.StringVar(value="Este año")
        ctk.CTkOptionMenu(barra, values=PERIODOS, variable=self._periodo, width=150,
                          dynamic_resizing=False,
                          command=lambda _v: self.refrescar()).pack(side="right")
        ctk.CTkLabel(barra, text="Período", text_color=GRIS_TEXTO).pack(
            side="right", padx=(0, 8))

        self._paneles = {
            "Dinero": self._panel_dinero(contenedor),
            "Equipos": self._panel_equipos(contenedor),
            "Personal y roles": self._panel_personal(contenedor),
            "Clientes y contratos": self._panel_clientes(contenedor),
        }
        self._pie = ctk.CTkLabel(contenedor, text="", font=("Segoe UI", 11),
                                 text_color=GRIS_TEXTO, anchor="w")
        self._pie.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self._mostrar_seccion(refrescar=False)

    # -- armado de cada sección -------------------------------------------- #
    @staticmethod
    def _panel(master) -> ctk.CTkFrame:
        """Tablas a la izquierda (columna 0, se estira) y torta a la derecha."""
        panel = ctk.CTkFrame(master, fg_color="transparent")
        panel.grid_columnconfigure(0, weight=1)
        return panel

    def _panel_dinero(self, master) -> ctk.CTkFrame:
        panel = self._panel(master)
        panel.grid_rowconfigure(2, weight=1)
        tarjetas = ctk.CTkFrame(panel, fg_color="transparent")
        tarjetas.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self._tarjetas: dict[str, Tarjeta] = {}
        for i, (clave, titulo, color) in enumerate([
            ("ingresos", "Ingresos", "verde"), ("egresos", "Egresos", "rojo"),
            ("resultado", "Resultado", "indigo"), ("saldo", "Saldo a cobrar", "celeste"),
        ]):
            tarjetas.grid_columnconfigure(i, weight=1, uniform="tarjeta")
            tarjeta = Tarjeta(tarjetas, titulo, relleno=RELLENOS[color], compacta=True)
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            self._tarjetas[clave] = tarjeta

        acciones = ctk.CTkFrame(panel, fg_color="transparent")
        acciones.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        boton(acciones, "Registrar egreso", self._nuevo_egreso, color="aviso",
              ancho=140).pack(side="left", padx=(0, 6))
        boton_secundario(acciones, "Eliminar egreso", self._eliminar_egreso,
                         ancho=130).pack(side="left")
        self._clase = ctk.StringVar(value="Todos")
        ctk.CTkSegmentedButton(acciones, values=["Todos", "Ingresos", "Egresos"],
                               variable=self._clase,
                               command=lambda _v: self.refrescar()).pack(
            side="right", padx=(0, 16))

        self.tabla_movimientos = Tabla(panel, [
            {"clave": "fecha", "titulo": "Fecha", "ancho": 90, "anchor": "center"},
            {"clave": "clase", "titulo": "Movimiento", "ancho": 90, "anchor": "center"},
            {"clave": "concepto", "titulo": "Concepto", "ancho": 170},
            {"clave": "proyecto", "titulo": "Proyecto", "ancho": 180},
            {"clave": "categoria", "titulo": "Tipo / categoría", "ancho": 120},
            {"clave": "medio", "titulo": "Medio", "ancho": 105},
            {"clave": "monto", "titulo": "Monto", "ancho": 120, "anchor": "e"},
        ], altura=4, recordar=(self.repos, "columnas.resumen.movimientos"))
        self.tabla_movimientos.grid(row=2, column=0, sticky="nsew")
        self.torta_dinero = Torta(panel, "Ingresos por tipo de proyecto", formato=moneda)
        self.torta_dinero.grid(row=1, column=1, rowspan=2, sticky="n", padx=(10, 0))
        return panel

    def _panel_equipos(self, master) -> ctk.CTkFrame:
        panel = self._panel(master)
        panel.grid_rowconfigure(0, weight=1)
        self.tabla_equipos = Tabla(panel, [
            {"clave": "producto", "titulo": "Producto", "ancho": 170},
            {"clave": "equipo", "titulo": "Marca / Modelo", "ancho": 210},
            {"clave": "serie", "titulo": "N° de serie", "ancho": 130},
            {"clave": "estado", "titulo": "Estado", "ancho": 100, "anchor": "center"},
            {"clave": "salidas", "titulo": "Salidas", "ancho": 90, "anchor": "center"},
            {"clave": "ultima", "titulo": "Última salida", "ancho": 120, "anchor": "center"},
        ], altura=4, recordar=(self.repos, "columnas.resumen.equipos"))
        self.tabla_equipos.grid(row=0, column=0, sticky="nsew")
        self.torta_equipos = Torta(panel, "Salidas por equipo")
        self.torta_equipos.grid(row=0, column=1, sticky="n", padx=(10, 0))
        return panel

    def _panel_personal(self, master) -> ctk.CTkFrame:
        panel = self._panel(master)
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        self.tabla_fotografos = Tabla(panel, [
            {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 220},
            {"clave": "eventos", "titulo": "Eventos", "ancho": 100, "anchor": "center"},
            {"clave": "trabajos", "titulo": "Trabajos", "ancho": 100, "anchor": "center"},
            {"clave": "proyectos", "titulo": "Proyectos a cargo", "ancho": 140,
             "anchor": "center"},
        ], altura=3, recordar=(self.repos, "columnas.resumen.fotografos"))
        self.tabla_fotografos.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.tabla_roles = Tabla(panel, [
            {"clave": "rol", "titulo": "Rol cubierto", "ancho": 220},
            {"clave": "eventos", "titulo": "Eventos", "ancho": 100, "anchor": "center"},
            {"clave": "veces", "titulo": "Veces", "ancho": 100, "anchor": "center"},
        ], altura=3, recordar=(self.repos, "columnas.resumen.roles"))
        self.tabla_roles.grid(row=1, column=0, sticky="nsew")
        self.torta_roles = Torta(panel, "Roles cubiertos")
        self.torta_roles.grid(row=0, column=1, rowspan=2, sticky="n", padx=(10, 0))
        return panel

    def _panel_clientes(self, master) -> ctk.CTkFrame:
        panel = self._panel(master)
        panel.grid_rowconfigure(0, weight=3)
        panel.grid_rowconfigure(1, weight=2)
        self.tabla_clientes = Tabla(panel, [
            {"clave": "cliente", "titulo": "Cliente", "ancho": 220},
            {"clave": "proyectos", "titulo": "Proyectos", "ancho": 90, "anchor": "center"},
            {"clave": "contratado", "titulo": "Contratado", "ancho": 130, "anchor": "e"},
            {"clave": "cobrado", "titulo": "Cobrado", "ancho": 130, "anchor": "e"},
            {"clave": "saldo", "titulo": "Saldo", "ancho": 130, "anchor": "e"},
        ], altura=3, recordar=(self.repos, "columnas.resumen.clientes"))
        self.tabla_clientes.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.tabla_estados = Tabla(panel, [
            {"clave": "que", "titulo": "Proyectos y contratos", "ancho": 220},
            {"clave": "estado", "titulo": "Estado", "ancho": 160},
            {"clave": "cantidad", "titulo": "Cantidad", "ancho": 100, "anchor": "center"},
        ], altura=3, recordar=(self.repos, "columnas.resumen.estados"))
        self.tabla_estados.grid(row=1, column=0, sticky="nsew")
        self.torta_tipos = Torta(panel, "Proyectos por tipo")
        self.torta_tipos.grid(row=0, column=1, rowspan=2, sticky="n", padx=(10, 0))
        return panel

    def _mostrar_seccion(self, refrescar: bool = True) -> None:
        for nombre, panel in self._paneles.items():
            if nombre == self._seccion.get():
                panel.grid(row=1, column=0, sticky="nsew")
            else:
                panel.grid_remove()
        if refrescar:
            self.refrescar()

    # -- datos ------------------------------------------------------------- #
    def refrescar(self) -> None:
        desde, hasta = rango_periodo(self._periodo.get())
        informes = self.repos.informes
        seccion = self._seccion.get()
        if seccion == "Dinero":
            self._refrescar_dinero(informes.movimientos(desde, hasta))
        elif seccion == "Equipos":
            filas = informes.salidas_por_equipo(desde, hasta)
            self.tabla_equipos.actualizar(
                [[f["producto"] or "—", f["equipo"], f["numero_serie"] or "—",
                  f["estado"], f["salidas"], fecha_legible(f["ultima"]) or "—"]
                 for f in filas], filas)
            self.torta_equipos.mostrar(
                [(f["producto"] or f["equipo"], f["salidas"]) for f in filas])
            self._pie.configure(
                text=f"{sum(f['salidas'] for f in filas)} salida(s) de equipos en el "
                f"período · {sum(1 for f in filas if not f['salidas'])} equipo(s) sin uso")
        elif seccion == "Personal y roles":
            fotografos = informes.eventos_por_fotografo(desde, hasta)
            roles = informes.roles_cubiertos(desde, hasta)
            self.tabla_fotografos.actualizar(
                [[f["fotografo"], f["eventos"], f["trabajos"], f["proyectos"]]
                 for f in fotografos], fotografos)
            self.tabla_roles.actualizar(
                [[r["rol"], r["eventos"], r["veces"]] for r in roles], roles)
            self.torta_roles.mostrar([(r["rol"], r["veces"]) for r in roles])
            self._pie.configure(
                text=f"{sum(r['veces'] for r in roles)} trabajo(s) asignados en el "
                "período · un evento cuenta una vez por rol aunque lo cubran varios")
        else:
            clientes = informes.movimientos_por_cliente(desde, hasta)
            self.tabla_clientes.actualizar(
                [[c["cliente"], c["proyectos"], moneda(c["contratado"]),
                  moneda(c["cobrado"]), moneda(c["contratado"] - c["cobrado"])]
                 for c in clientes], clientes)
            estados = (
                [["Proyectos", f["estado"], f["proyectos"]]
                 for f in informes.proyectos_por_estado(desde, hasta)]
                + [["Contratos", f["estado"], f["contratos"]]
                   for f in informes.contratos_por_estado(desde, hasta)])
            self.tabla_estados.actualizar(estados, estados)
            tipos = informes.proyectos_por_tipo(desde, hasta)
            self.torta_tipos.mostrar([(t["tipo"], t["proyectos"]) for t in tipos])
            self._pie.configure(
                text=f"{len(clientes)} cliente(s) con movimiento · "
                f"{sum(c['proyectos'] for c in clientes)} proyecto(s) en el período")

    def _refrescar_dinero(self, movimientos: list[dict]) -> None:
        ingresos = sum(m["monto"] for m in movimientos if m["clase"] == "Ingreso")
        egresos = sum(m["monto"] for m in movimientos if m["clase"] == "Egreso")
        self._tarjetas["ingresos"].set_valor(moneda(ingresos))
        self._tarjetas["egresos"].set_valor(moneda(egresos))
        self._tarjetas["resultado"].set_valor(moneda(ingresos - egresos))
        self._tarjetas["resultado"].set_relleno(
            RELLENOS["rojo" if egresos > ingresos else "indigo"])
        self._tarjetas["saldo"].set_valor(moneda(self.repos.informes.saldo_por_cobrar()))

        clase = {"Ingresos": "Ingreso", "Egresos": "Egreso"}.get(self._clase.get())
        visibles = [m for m in movimientos if clase is None or m["clase"] == clase]
        self.tabla_movimientos.actualizar(
            [[fecha_legible(m["fecha"]), m["clase"], m["concepto"], m["proyecto"] or "—",
              m["categoria"] or "—", m["medio"] or "—", moneda(m["monto"])]
             for m in visibles],
            visibles, ["ok" if m["clase"] == "Ingreso" else "vencido" for m in visibles])

        por_tipo: dict[str, float] = {}
        for m in movimientos:
            if m["clase"] == "Ingreso":
                tipo = m["categoria"] or "Sin tipo"
                por_tipo[tipo] = por_tipo.get(tipo, 0.0) + m["monto"]
        self.torta_dinero.mostrar(list(por_tipo.items()))
        self._pie.configure(
            text=f"{len(movimientos)} movimiento(s) en el período · el saldo a cobrar "
            "es el total pendiente de todos los proyectos")

    # -- egresos ----------------------------------------------------------- #
    def _nuevo_egreso(self) -> None:
        egreso = DialogoEgreso(self, self.repos.egresos.categorias(),
                               self.repos.proyectos.listar()).mostrar()
        if egreso is not None:
            self.ejecutar(lambda: self.repos.egresos.crear(egreso))

    def _eliminar_egreso(self) -> None:
        movimiento = self.tabla_movimientos.seleccionado()
        if movimiento is None or movimiento["egreso_id"] is None:
            self.advertir("Sin selección",
                          "Elija un egreso de la tabla. Los ingresos se corrigen desde "
                          "el proyecto al que pertenecen.")
            return
        if self.confirmar("Eliminar egreso",
                          f"¿Eliminar «{movimiento['concepto']}» por "
                          f"{moneda(movimiento['monto'])}?"):
            self.ejecutar(lambda: self.repos.egresos.eliminar(movimiento["egreso_id"]))


__all__ = ["VistaResumen", "rango_periodo"]
