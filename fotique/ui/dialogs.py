"""Diálogos (formularios modales) de Fotique."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Optional, Sequence

import customtkinter as ctk

from ..domain.errors import DatosInvalidosError
from ..domain.models import (
    Cliente,
    Contrato,
    Egreso,
    Equipo,
    EstadoEquipo,
    EstadoProyecto,
    EstadoTrabajo,
    Evento,
    Fotografo,
    PlantillaContrato,
    Proyecto,
    RolUsuario,
    Servicio,
    TrabajoPendiente,
    Usuario,
)
from ..domain.services import generar_texto_contrato
from ..util import fecha_legible, moneda
from .fechas import SelectorFecha
from .theme import FUENTE_NORMAL, FUENTE_SUBTITULO, GRIS_TEXTO
from .widgets import Dialogo, DialogoMensaje, Tabla, boton, boton_secundario


def _etiqueta_fotografo(f: Fotografo) -> str:
    return f.nombre_completo or "Sin nombre"


def _etiqueta_cliente(c: Cliente) -> str:
    return c.nombre


def _etiqueta_proyecto(p: Proyecto) -> str:
    return p.titulo or f"Proyecto #{p.id}"


# --------------------------------------------------------------------------- #
# Módulo A — Equipos
# --------------------------------------------------------------------------- #


class DialogoEquipo(Dialogo):
    SIN_CATEGORIA = "Sin categoría"

    def __init__(self, master: Any, equipo: Optional[Equipo] = None,
                 categorias: Sequence[str] = (),
                 administrar: Optional[Callable[[Any], Sequence[str]]] = None):
        """``administrar`` abre el alta y baja de categorías sobre este diálogo
        y devuelve la lista actualizada; sin él no se muestra el botón."""
        super().__init__(master, "Editar equipo" if equipo else "Nuevo equipo",
                         ancho=600, alto=680)
        e = equipo
        self._equipo = e
        self._administrar = administrar
        categorias = list(categorias)
        if e is not None and e.categoria and e.categoria not in categorias:
            categorias.append(e.categoria)
        menu = self.campo_selector("categoria", "Categoría",
                                   [self.SIN_CATEGORIA] + categorias,
                                   e.categoria if e else None)
        if administrar is not None:
            menu.configure(width=200)
            boton_secundario(self.form, "Agregar / quitar", self._editar_categorias,
                             ancho=120).grid(row=self._fila - 1, column=1, sticky="w",
                                             padx=(218, 10), pady=6)
        self.campo_texto("serie", "Número de serie", e.numero_serie if e else "",
                         "Opcional")
        self.campo_texto("producto", "Producto", e.producto if e else "",
                         "Cámara, lente, flash…")
        self.campo_texto("marca", "Marca *", e.marca if e else "", "Sony")
        self.campo_texto("modelo", "Modelo *", e.modelo if e else "", "A7 IV")
        self.campo_fecha("adquisicion", "Fecha de adquisición",
                         e.fecha_adquisicion if e else None)
        self.separador("Service")
        self.campo_fecha("service_ultimo", "Último service",
                         e.fecha_service_ultimo if e else None)
        self.campo_fecha("service_proximo", "Próximo service",
                         e.fecha_service_proximo if e else None)
        if e is not None:
            if e.estado == EstadoEquipo.EN_USO and e.fotografo_actual:
                self.nota(
                    f"Estado actual: En uso — {e.fotografo_actual.nombre_completo}. "
                    "Cambie el estado con los botones Asignar / Devolver."
                )
            else:
                self.nota("Estado actual: En stock.")
        self.separador("Observaciones")
        self.campo_area("notas", "Notas", e.notas if e else "", altura=110)
        self.botones("Guardar", self._guardar)

    def _editar_categorias(self) -> None:
        categorias = [self.SIN_CATEGORIA] + list(self._administrar(self))
        menu, actual = self._campos["categoria"], self.texto("categoria")
        menu.configure(values=categorias)
        menu.set(actual if actual in categorias else self.SIN_CATEGORIA)
        self.grab_set()  # el diálogo de categorías soltó la captura al cerrarse
        self.focus_set()

    def _guardar(self) -> Equipo:
        serie, marca, modelo = self.texto("serie"), self.texto("marca"), self.texto("modelo")
        if not marca or not modelo:
            raise DatosInvalidosError("Marca y modelo son obligatorios.")
        equipo = self._equipo or Equipo(numero_serie=serie, marca=marca, modelo=modelo)
        equipo.numero_serie, equipo.marca, equipo.modelo = serie, marca, modelo
        categoria = self.texto("categoria")
        equipo.categoria = "" if categoria == self.SIN_CATEGORIA else categoria
        equipo.producto = self.texto("producto")
        equipo.fecha_adquisicion = self.fecha("adquisicion")
        equipo.fecha_service_ultimo = self.fecha("service_ultimo")
        equipo.fecha_service_proximo = self.fecha("service_proximo")
        equipo.notas = self.texto("notas")
        return equipo


class DialogoAsignar(Dialogo):
    """Exige el fotógrafo responsable; el proyecto y la entrega son opcionales."""

    def __init__(self, master: Any, equipo: Equipo, fotografos: Sequence[Fotografo],
                 proyectos: Sequence[Proyecto] = ()):
        super().__init__(master, f"Asignar {equipo.descripcion}", ancho=560, alto=460)
        if not fotografos:
            self.nota("No hay fotógrafos cargados. Agregue uno en el módulo de personal.")
        self.campo_selector_objetos(
            "fotografo", "Fotógrafo responsable *", fotografos, _etiqueta_fotografo
        )
        self.campo_selector_objetos(
            "proyecto", "Proyecto", proyectos, _etiqueta_proyecto,
            vacio="— Sin proyecto —", opcional=True,
        )
        self.campo_fecha("retiro", "Fecha de retiro *", date.today(), opcional=False)
        self.campo_fecha("entrega", "Fecha de entrega")
        self.campo_texto("obs", "Observaciones", "", "Evento, cliente, sucursal…")
        self.nota(
            "Al confirmar el equipo pasa a 'En uso' y el movimiento queda registrado "
            "en el historial."
        )
        self.botones("Asignar", self._guardar)

    def _guardar(self) -> dict:
        fotografo = self.objeto("fotografo")
        if fotografo is None:
            raise DatosInvalidosError("Debe seleccionar un fotógrafo responsable.")
        retiro = self.fecha("retiro") or date.today()
        entrega = self.fecha("entrega")
        if entrega is not None and entrega < retiro:
            raise DatosInvalidosError(
                "La fecha de entrega no puede ser anterior a la de retiro.")
        proyecto = self.objeto("proyecto")
        return {
            "fotografo_id": fotografo.id,
            "proyecto_id": proyecto.id if proyecto else None,
            "fecha": retiro,
            "fecha_prevista": entrega,
            "observaciones": self.texto("obs"),
        }


class DialogoDevolver(Dialogo):
    def __init__(self, master: Any, equipo: Equipo):
        super().__init__(master, f"Devolver {equipo.descripcion}", ancho=560, alto=300)
        if equipo.fotografo_actual:
            self.nota(f"En uso de: {equipo.fotografo_actual.nombre_completo}.")
        self.campo_fecha("fecha", "Fecha de devolución", date.today(), opcional=False)
        self.campo_texto("obs", "Observaciones", "", "Estado del equipo, incidencias…")
        self.botones("Devolver al stock", self._guardar)

    def _guardar(self) -> dict:
        return {"fecha": self.fecha("fecha") or date.today(),
                "observaciones": self.texto("obs")}


class DialogoTabla(Dialogo):
    """Diálogo de solo lectura con una tabla (historiales, listados)."""

    def __init__(self, master: Any, titulo: str, columnas: Sequence[dict],
                 filas: Sequence[Sequence[str]], *, ancho: int = 860, alto: int = 520):
        super().__init__(master, titulo, ancho=ancho, alto=alto)
        self.tabla = Tabla(self.form, columnas, altura=max(8, min(18, len(filas) + 2)))
        self.tabla.grid(row=self._fila, column=0, columnspan=2, sticky="nsew",
                        padx=10, pady=10)
        self.form.grid_rowconfigure(self._fila, weight=1)
        self._fila += 1
        if not filas:
            self.nota("Sin registros.")
        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")


class DialogoHistorialEquipos(Dialogo):
    """Movimientos de todos los equipos, filtrables por equipo, fotógrafo y fecha.

    ``cargar(equipo_id, fotografo_id, desde, hasta)`` devuelve los movimientos;
    las fechas acotan el día de retiro. ``equipo`` abre el historial ya filtrado.
    """

    def __init__(self, master: Any, equipos: Sequence[Equipo],
                 fotografos: Sequence[Fotografo], cargar,
                 equipo: Optional[Equipo] = None):
        super().__init__(master, "Historial de movimientos de equipos",
                         ancho=1100, alto=580)
        self._cargar = cargar
        self._equipos = self._opciones("Todos los equipos", equipos, lambda e: e.nombre)
        self._fotografos = self._opciones("Todos los fotógrafos", fotografos,
                                          _etiqueta_fotografo)
        actual = next((texto for texto, e in self._equipos.items()
                       if e is not None and equipo is not None and e.id == equipo.id),
                      "Todos los equipos")

        barra = ctk.CTkFrame(self.form, fg_color="transparent")
        barra.grid(row=self._fila, column=0, columnspan=2, sticky="ew", padx=10,
                   pady=(4, 0))
        self._fila += 1
        self._equipo = ctk.StringVar(value=actual)
        ctk.CTkOptionMenu(barra, values=list(self._equipos), variable=self._equipo,
                          width=240, dynamic_resizing=False, font=FUENTE_NORMAL,
                          command=lambda _v: self._refrescar()).pack(
            side="left", padx=(0, 8))
        self._fotografo = ctk.StringVar(value="Todos los fotógrafos")
        ctk.CTkOptionMenu(barra, values=list(self._fotografos),
                          variable=self._fotografo, width=200, dynamic_resizing=False,
                          font=FUENTE_NORMAL,
                          command=lambda _v: self._refrescar()).pack(
            side="left", padx=(0, 14))
        ctk.CTkLabel(barra, text="Desde", font=FUENTE_NORMAL,
                     text_color=GRIS_TEXTO).pack(side="left", padx=(0, 6))
        self._desde = SelectorFecha(barra, ancho=150,
                                    al_cambiar=lambda _f: self._refrescar())
        self._desde.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(barra, text="Hasta", font=FUENTE_NORMAL,
                     text_color=GRIS_TEXTO).pack(side="left", padx=(0, 6))
        self._hasta = SelectorFecha(barra, ancho=150,
                                    al_cambiar=lambda _f: self._refrescar())
        self._hasta.pack(side="left", padx=(0, 12))
        boton_secundario(barra, "Limpiar", self._limpiar, ancho=80).pack(side="left")

        self.tabla = Tabla(self.form, [
            {"clave": "equipo", "titulo": "Equipo", "ancho": 200},
            {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 140},
            {"clave": "proyecto", "titulo": "Proyecto", "ancho": 170},
            {"clave": "retiro", "titulo": "Retiro", "ancho": 95, "anchor": "center"},
            {"clave": "entrega", "titulo": "Entrega", "ancho": 95, "anchor": "center"},
            {"clave": "devuelto", "titulo": "Devuelto", "ancho": 95, "anchor": "center"},
            {"clave": "obs", "titulo": "Observaciones", "ancho": 200},
        ], altura=11)
        self.tabla.grid(row=self._fila, column=0, columnspan=2, sticky="nsew",
                        padx=10, pady=10)
        self._fila += 1
        self._resumen = ctk.CTkLabel(self.form, text="", font=FUENTE_NORMAL,
                                     text_color=GRIS_TEXTO, anchor="w")
        self._resumen.grid(row=self._fila, column=0, columnspan=2, sticky="w", padx=10)
        self._fila += 1
        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")
        self._refrescar()

    @staticmethod
    def _opciones(todos: str, objetos: Sequence[Any], etiquetador) -> dict[str, Any]:
        """``etiqueta ➜ objeto``; la primera opción (``todos``) no filtra."""
        mapa: dict[str, Any] = {todos: None}
        for objeto in objetos:
            base = etiquetador(objeto)
            texto, n = base, 2
            while texto in mapa:
                texto = f"{base} ({n})"
                n += 1
            mapa[texto] = objeto
        return mapa

    def _limpiar(self) -> None:
        self._equipo.set("Todos los equipos")
        self._fotografo.set("Todos los fotógrafos")
        self._desde.set(None)
        self._hasta.set(None)
        self._refrescar()

    def _refrescar(self) -> None:
        if not hasattr(self, "tabla"):  # un filtro avisó antes de armar la tabla
            return
        equipo = self._equipos.get(self._equipo.get())
        fotografo = self._fotografos.get(self._fotografo.get())
        movimientos = self._cargar(
            equipo.id if equipo else None, fotografo.id if fotografo else None,
            self._desde.fecha(), self._hasta.fecha())
        self.tabla.actualizar(
            [[
                f"{r['marca']} {r['modelo']}"
                + (f" ({r['numero_serie']})" if r["numero_serie"] else ""),
                f"{r['f_nombre'] or ''} {r['f_apellido'] or ''}".strip() or "—",
                r["p_titulo"] or "—",
                fecha_legible(r["fecha_asignacion"]) or "—",
                fecha_legible(r["fecha_prevista"]) or "—",
                fecha_legible(r["fecha_devolucion"]) or "En uso",
                r["observaciones"] or "",
            ] for r in movimientos],
            movimientos,
            ["" if r["fecha_devolucion"] else "vencido" for r in movimientos])
        en_uso = sum(1 for r in movimientos if not r["fecha_devolucion"])
        self._resumen.configure(
            text=f"{len(movimientos)} movimiento(s) · {en_uso} sin devolver"
            + ("" if movimientos else " · ningún movimiento coincide con los filtros"))


class DialogoFichaEquipo(Dialogo):
    """Ficha completa: datos + historial de uso."""

    def __init__(self, master: Any, equipo: Equipo, historial: Sequence[dict]):
        super().__init__(master, f"Ficha: {equipo.descripcion}", ancho=820, alto=560)
        self.separador("Datos del equipo")
        for etiqueta, valor in (
            ("Número de serie", equipo.numero_serie or "—"),
            ("Marca / Modelo", equipo.descripcion),
            ("Estado", str(equipo.estado)),
            ("Fotógrafo responsable",
             equipo.fotografo_actual.nombre_completo if equipo.fotografo_actual else "—"),
            ("Fecha de adquisición", fecha_legible(equipo.fecha_adquisicion) or "—"),
            ("Último service", fecha_legible(equipo.fecha_service_ultimo) or "—"),
            ("Próximo service", fecha_legible(equipo.fecha_service_proximo) or "—"),
            ("Notas", equipo.notas or "—"),
        ):
            self.campo_texto(etiqueta, etiqueta, valor)
            self._campos[etiqueta].configure(state="disabled")
        self.separador("Historial de uso")
        columnas = [
            {"clave": "equipo", "titulo": "Equipo", "ancho": 200},
            {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 170},
            {"clave": "salida", "titulo": "Asignado", "ancho": 110},
            {"clave": "entrada", "titulo": "Devuelto", "ancho": 110},
            {"clave": "obs", "titulo": "Observaciones", "ancho": 260},
        ]
        filas = [
            [
                f"{r['marca']} {r['modelo']}",
                f"{r['f_nombre'] or ''} {r['f_apellido'] or ''}".strip() or "—",
                fecha_legible(r["fecha_asignacion"]),
                fecha_legible(r["fecha_devolucion"]) or "En uso",
                r["observaciones"] or "",
            ]
            for r in historial
        ]
        self.tabla = Tabla(self.form, columnas,
                           altura=max(6, min(18, len(historial) + 2)))
        self.tabla.grid(row=self._fila, column=0, columnspan=2, sticky="nsew",
                        padx=10, pady=(4, 10))
        self.form.grid_rowconfigure(self._fila, weight=1)
        self._fila += 1
        self.tabla.actualizar(filas, list(historial))
        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")


# --------------------------------------------------------------------------- #
# Módulo B — Fotógrafos y trabajos
# --------------------------------------------------------------------------- #


class DialogoFotografo(Dialogo):
    """``elegir_rol`` agrega el rol de la cuenta de acceso (sólo administradores,
    sólo en el alta); queda en ``self.rol`` al aceptar."""

    def __init__(self, master: Any, fotografo: Optional[Fotografo] = None, *,
                 elegir_rol: bool = False):
        super().__init__(master, "Editar fotógrafo" if fotografo else "Nuevo fotógrafo",
                         ancho=580, alto=440)
        f = fotografo
        self._fotografo = f
        self._elegir_rol = elegir_rol and f is None
        self.rol: Optional[RolUsuario] = None
        self.campo_texto("nombre", "Nombre *", f.nombre if f else "")
        self.campo_texto("apellido", "Apellido", f.apellido if f else "")
        self.campo_texto("telefono", "Teléfono", f.telefono if f else "",
                         "+54 9 …")
        self.campo_texto("email", "Email", f.email if f else "", "nombre@estudio.com")
        if self._elegir_rol:
            self.campo_selector("rol", "Rol en el sistema",
                                [str(RolUsuario.USUARIO), str(RolUsuario.ADMINISTRADOR)])
            self.nota("Se crea su cuenta de acceso con una contraseña provisoria, "
                      "que deberá cambiar la primera vez que ingrese.")
        self.botones("Guardar", self._guardar)

    def _guardar(self) -> Fotografo:
        nombre = self.texto("nombre")
        if not nombre:
            raise DatosInvalidosError("El nombre del fotógrafo es obligatorio.")
        f = self._fotografo or Fotografo(nombre=nombre)
        f.nombre = nombre
        f.apellido = self.texto("apellido")
        f.telefono = self.texto("telefono")
        f.email = self.texto("email")
        f.activo = True
        if self._elegir_rol:
            self.rol = RolUsuario(self.valor_selector("rol"))
        return f


# --------------------------------------------------------------------------- #
# Módulo C — Clientes, proyectos y cobros
# --------------------------------------------------------------------------- #


class DialogoCliente(Dialogo):
    def __init__(self, master: Any, cliente: Optional[Cliente] = None):
        super().__init__(master, "Editar cliente" if cliente else "Nuevo cliente",
                         ancho=580, alto=440)
        self._cliente = cliente
        c = cliente
        self.campo_texto("nombre", "Nombre y apellido / Razón social *",
                         c.nombre if c else "")
        self.campo_texto("responsable", "Responsable / contacto principal",
                         c.responsable if c else "")
        self.campo_texto("telefono", "Celular / teléfono", c.telefono if c else "")
        self.campo_texto("email", "Email", c.email if c else "")
        self.campo_texto("direccion", "Dirección (cliente o locación)",
                         c.direccion if c else "")
        self.botones("Guardar", self._guardar)

    def _guardar(self) -> Cliente:
        nombre = self.texto("nombre")
        if not nombre:
            raise DatosInvalidosError("El nombre del cliente es obligatorio.")
        cliente = self._cliente or Cliente(nombre=nombre)
        cliente.nombre = nombre
        cliente.responsable = self.texto("responsable")
        cliente.telefono = self.texto("telefono")
        cliente.email = self.texto("email")
        cliente.direccion = self.texto("direccion")
        return cliente


class DialogoProyecto(Dialogo):
    def __init__(
        self,
        master: Any,
        clientes: Sequence[Cliente],
        fotografos: Sequence[Fotografo],
        proyecto: Optional[Proyecto] = None,
        tipos: Sequence[str] = (),
    ):
        super().__init__(master, "Editar proyecto" if proyecto else "Nuevo proyecto",
                         ancho=640, alto=760)
        p = proyecto
        self._proyecto = p
        self.campo_selector_objetos(
            "cliente", "Cliente", clientes, _etiqueta_cliente,
            seleccion=next((c for c in clientes if c.id == (p.cliente_id if p else None)),
                           None),
            vacio="— Sin cliente —", opcional=True,
        )
        self.campo_texto("titulo", "Título del proyecto *", p.titulo if p else "",
                         "Casamiento López & Paz")
        self.campo_combo("tipo", "Tipo de proyecto", tipos, p.tipo if p else "")
        self.nota("Elija un tipo de la lista o escriba uno nuevo según su rubro.")
        self.campo_selector_objetos(
            "fotografo", "Fotógrafo responsable", fotografos, _etiqueta_fotografo,
            seleccion=(p.fotografo if p else None),
        )
        self.campo_fecha("evento", "Fecha del evento", p.fecha_evento if p else None)
        self.campo_selector(
            "estado", "Estado", [str(e) for e in EstadoProyecto],
            str(p.estado) if p else str(EstadoProyecto.PRESUPUESTO),
        )
        self.campo_texto("direccion", "Dirección / locación", p.direccion if p else "")
        self.separador("Cobro")
        self.campo_monto("cobro", "Cobro total", p.cobro_total if p else 0.0)
        self.campo_monto("sena", "Seña", p.sena if p else 0.0)
        self.campo_fecha("sena_fecha", "Fecha de la seña", p.sena_fecha if p else None)
        self.campo_selector(
            "sena_medio", "Medio de pago",
            ["—", "Efectivo", "Transferencia", "Mercado Pago", "Tarjeta", "Otro"],
            (p.sena_medio if p and p.sena_medio else "—"),
        )
        self.separador("Notas")
        self.campo_area("notas", "Notas", p.notas if p else "", altura=90)
        self.nota("Saldo = Cobro total − Seña − pagos parciales (cálculo automático).")
        self.botones("Guardar", self._guardar)

    def _guardar(self) -> Proyecto:
        if not self.texto("titulo"):
            raise DatosInvalidosError("El título del proyecto es obligatorio.")
        cliente = self.objeto("cliente")  # None: proyecto sin cliente
        fotografo = self.objeto("fotografo")
        proyecto = self._proyecto or Proyecto()
        proyecto.cliente = cliente.nombre if cliente else ""
        proyecto.cliente_id = cliente.id if cliente else None
        proyecto.titulo = self.texto("titulo")
        proyecto.tipo = self.texto("tipo")
        proyecto.fotografo = fotografo
        proyecto.fotografo_id = fotografo.id if fotografo else None
        proyecto.fecha_evento = self.fecha("evento")
        proyecto.estado = EstadoProyecto(self.valor_selector("estado"))
        proyecto.direccion = self.texto("direccion")
        proyecto.cobro_total = self.monto("cobro")
        proyecto.sena = self.monto("sena")
        proyecto.sena_fecha = self.fecha("sena_fecha")
        medio = self.valor_selector("sena_medio")
        proyecto.sena_medio = "" if medio == "—" else medio
        proyecto.notas = self.texto("notas")
        return proyecto


class DialogoPago(Dialogo):
    def __init__(self, master: Any, proyecto: Optional[Proyecto] = None,
                 solo_sena: bool = False):
        titulo = ("Registrar seña" if solo_sena else "Registrar pago")
        super().__init__(master, titulo, ancho=560, alto=400)
        self._sena = solo_sena
        if proyecto is not None:
            self.nota(
                f"{proyecto.nombre} — total {moneda(proyecto.cobro_total)} · "
                f"señado {moneda(proyecto.sena)} · saldo {moneda(proyecto.saldo)}"
            )
        self._proyecto = proyecto
        self.campo_monto("monto", "Monto *")
        self.campo_fecha("fecha", "Fecha", date.today(), opcional=False)
        self.campo_selector(
            "medio", "Medio de pago",
            ["Efectivo", "Transferencia", "Mercado Pago", "Tarjeta", "Otro"],
        )
        self.campo_texto("notas", "Concepto / notas", "",
                         "Cuota 2, entregable, viáticos…")
        self.botones("Registrar", self._guardar)

    def _guardar(self) -> dict:
        monto = self.monto("monto")
        if monto <= 0:
            raise DatosInvalidosError("El monto debe ser mayor a cero.")
        if self._proyecto is not None:
            self._proyecto.validar_pago(monto)
        return {
            "monto": monto,
            "fecha": self.fecha("fecha") or date.today(),
            "medio": self.valor_selector("medio"),
            "notas": self.texto("notas"),
        }


# --------------------------------------------------------------------------- #
# Módulo B/D — Trabajos, eventos, servicios y contratos
# --------------------------------------------------------------------------- #


class DialogoTrabajo(Dialogo):
    def __init__(self, master: Any, fotografos: Sequence[Fotografo],
                 proyectos: Sequence[Proyecto],
                 trabajo: Optional[TrabajoPendiente] = None,
                 fotografo_inicial: Optional[Fotografo] = None,
                 roles: Sequence[str] = ()):
        super().__init__(master, "Editar trabajo" if trabajo else "Nuevo trabajo",
                         ancho=620, alto=600)
        t = trabajo
        self._trabajo = t
        fotografo_actual = fotografo_inicial
        if fotografo_actual is None and t is not None:
            fotografo_actual = next(
                (f for f in fotografos if f.id == t.fotografo_id), None
            )
        proyecto_actual = None
        if t is not None:
            proyecto_actual = next(
                (p for p in proyectos if p.id == t.proyecto_id), None
            )
        self.campo_texto("titulo", "Trabajo / entrega *", t.titulo if t else "",
                         "Edición selección casamiento")
        self.campo_selector_objetos(
            "fotografo", "Fotógrafo *", fotografos, _etiqueta_fotografo,
            seleccion=fotografo_actual,
        )
        self.campo_combo("rol", "Rol en este trabajo", roles, t.rol if t else "")
        self.nota("El rol es propio de cada trabajo: elija uno o escriba uno nuevo.")
        self.campo_selector_objetos(
            "proyecto", "Proyecto asociado", proyectos, _etiqueta_proyecto,
            seleccion=proyecto_actual, vacio="— Sin proyecto —", opcional=True,
        )
        self.campo_fecha("entrega", "Fecha de entrega", t.fecha_entrega if t else None)
        self.campo_selector("estado", "Estado", [str(e) for e in EstadoTrabajo],
                            str(t.estado) if t else str(EstadoTrabajo.PENDIENTE))
        self.campo_area("descripcion", "Descripción", t.descripcion if t else "",
                        altura=100)
        self.botones("Guardar", self._guardar)

    def _guardar(self) -> TrabajoPendiente:
        titulo = self.texto("titulo")
        if not titulo:
            raise DatosInvalidosError("El título del trabajo es obligatorio.")
        fotografo = self.objeto("fotografo")
        if fotografo is None:
            raise DatosInvalidosError("Debe asignar un fotógrafo al trabajo.")
        proyecto = self.objeto("proyecto")
        trabajo = self._trabajo or TrabajoPendiente(titulo=titulo)
        trabajo.titulo = titulo
        trabajo.rol = self.texto("rol")
        trabajo.fotografo = fotografo
        trabajo.fotografo_id = fotografo.id
        trabajo.proyecto = proyecto
        trabajo.proyecto_id = proyecto.id if proyecto else None
        trabajo.fecha_entrega = self.fecha("entrega")
        trabajo.estado = EstadoTrabajo(self.valor_selector("estado"))
        trabajo.descripcion = self.texto("descripcion")
        return trabajo


class DialogoEvento(Dialogo):
    def __init__(self, master: Any, fotografos: Sequence[Fotografo],
                 proyectos: Sequence[Proyecto], fecha: date,
                 evento: Optional[Evento] = None):
        super().__init__(master, "Editar evento" if evento else "Nuevo evento",
                         ancho=620, alto=560)
        e = evento
        self._evento = e
        self.campo_texto("titulo", "Título *", e.titulo if e else "", "Previa sesión")
        self.campo_fecha("fecha", "Fecha *", e.fecha if e else fecha, opcional=False)
        self.campo_texto("hora", "Hora", e.hora if e else "", "16:00")
        self.campo_selector(
            "tipo", "Tipo",
            ["Sesión", "Entrega", "Service", "Reunión", "Otro"],
            e.tipo if e else "Sesión",
        )
        self.campo_selector_objetos(
            "fotografo", "Fotógrafo", fotografos, _etiqueta_fotografo,
            seleccion=next((f for f in fotografos if f.id == (e.fotografo_id if e else None)),
                           None),
        )
        self.campo_selector_objetos(
            "proyecto", "Proyecto", proyectos, _etiqueta_proyecto,
            seleccion=next((p for p in proyectos if p.id == (e.proyecto_id if e else None)),
                           None),
        )
        self.campo_area("notas", "Notas", e.notas if e else "", altura=90)
        self.botones("Guardar", self._guardar)

    def _guardar(self) -> Evento:
        titulo = self.texto("titulo")
        if not titulo:
            raise DatosInvalidosError("El título del evento es obligatorio.")
        fecha = self.fecha("fecha")
        if fecha is None:
            raise DatosInvalidosError("La fecha del evento es obligatoria.")
        fotografo = self.objeto("fotografo")
        proyecto = self.objeto("proyecto")
        evento = self._evento or Evento(titulo=titulo, fecha=fecha)
        evento.titulo = titulo
        evento.fecha = fecha
        evento.hora = self.texto("hora")
        evento.tipo = self.valor_selector("tipo")
        evento.fotografo = fotografo
        evento.fotografo_id = fotografo.id if fotografo else None
        evento.proyecto_id = proyecto.id if proyecto else None
        evento.notas = self.texto("notas")
        return evento


class DialogoServicio(Dialogo):
    def __init__(self, master: Any, categorias: Sequence[str],
                 servicio: Optional[Servicio] = None):
        super().__init__(master, "Editar servicio" if servicio else "Nuevo servicio",
                         ancho=580, alto=520)
        s = servicio
        self._servicio = s
        self.campo_texto("nombre", "Nombre del servicio *", s.nombre if s else "",
                         "Cobertura boda (8 hs)")
        categorias = list(categorias)
        if s is not None and s.categoria not in categorias:
            categorias.append(s.categoria)
        self.campo_selector("categoria", "Categoría", categorias or ["Otros"],
                            s.categoria if s else None)
        self.campo_monto("precio", "Precio", s.precio if s else 0.0)
        self.campo_texto("unidad", "Unidad", s.unidad if s else "servicio",
                         "servicio, evento, foto, jornada…")
        self.campo_area("notas", "Notas", s.notas if s else "", altura=90)
        self.nota("Las categorías se agregan o quitan con el botón «Categorías» "
                  "del tarifario.")
        self.botones("Guardar", self._guardar)

    def _guardar(self) -> Servicio:
        nombre = self.texto("nombre")
        if not nombre:
            raise DatosInvalidosError("El nombre del servicio es obligatorio.")
        precio = self.monto("precio")
        if precio < 0:
            raise DatosInvalidosError("El precio no puede ser negativo.")
        servicio = self._servicio or Servicio(nombre=nombre)
        servicio.nombre = nombre
        servicio.categoria = self.texto("categoria") or "Otros"
        servicio.precio = precio
        servicio.unidad = self.texto("unidad") or "servicio"
        servicio.activo = True
        servicio.notas = self.texto("notas")
        return servicio


class DialogoPlantilla(Dialogo):
    def __init__(self, master: Any, plantilla: Optional[PlantillaContrato] = None):
        super().__init__(master, "Editar plantilla" if plantilla else "Nueva plantilla",
                         ancho=720, alto=700)
        p = plantilla
        self._plantilla = p
        self.campo_texto("nombre", "Nombre de la plantilla *",
                         p.nombre if p else "", "Contrato estándar")
        self.nota(
            "Variables disponibles: {{estudio}}, {{cliente}}, {{titulo}}, "
            "{{fecha_evento}}, {{direccion}}, {{fotografo}}, {{cobro_total}}, "
            "{{sena}}, {{saldo}}, {{contenido_extra}}."
        )
        self.campo_area("contenido", "Contenido", p.contenido if p else "", altura=340)
        self.botones("Guardar", self._guardar)

    def _guardar(self) -> PlantillaContrato:
        nombre = self.texto("nombre")
        if not nombre:
            raise DatosInvalidosError("La plantilla necesita un nombre.")
        plantilla = self._plantilla or PlantillaContrato(nombre=nombre)
        plantilla.nombre = nombre
        plantilla.contenido = self.texto("contenido")
        return plantilla


class DialogoContrato(Dialogo):
    def __init__(self, master: Any, proyectos: Sequence[Proyecto],
                 plantillas: Sequence[PlantillaContrato],
                 contrato: Optional[Contrato] = None,
                 estudio: str = "Estudio Fotique"):
        super().__init__(master, "Editar contrato" if contrato else "Nuevo contrato",
                         ancho=760, alto=760)
        c = contrato
        self._contrato = c
        self._proyectos = proyectos
        self._plantillas = plantillas
        self._estudio = estudio
        self.campo_texto("nombre", "Nombre del contrato *",
                         c.nombre if c else "", "Contrato Casamiento López")
        self.campo_selector_objetos(
            "proyecto", "Proyecto vinculado", proyectos, _etiqueta_proyecto,
            seleccion=next((p for p in proyectos
                            if p.id == (c.proyecto_id if c else None)), None),
        )
        self.campo_selector_objetos(
            "plantilla", "Plantilla", plantillas, lambda p: p.nombre,
            seleccion=next((pl for pl in plantillas
                            if pl.id == (c.plantilla_id if c else None)), None),
        )
        self.campo_selector("estado", "Estado",
                            ["Borrador", "Enviado", "Firmado", "Anulado"],
                            c.estado if c else "Borrador")
        self.campo_fecha("fecha", "Fecha", c.fecha if c else date.today())
        area = self.campo_area("contenido", "Contenido",
                               c.contenido if c else "", altura=300)
        self._generar = boton(self.form, "Generar desde la plantilla",
                              self._generar_contenido, ancho=230)
        self._generar.grid(row=self._fila, column=1, sticky="w", padx=10, pady=(0, 8))
        self._fila += 1
        self.botones("Guardar", self._guardar)
        del area

    def _generar_contenido(self) -> None:
        proyecto = self.objeto("proyecto")
        plantilla = self.objeto("plantilla")
        if proyecto is None or plantilla is None:
            DialogoMensaje_error(self, "Faltan datos",
                                 "Seleccione proyecto y plantilla para generar.")
            return
        texto = generar_texto_contrato(plantilla.contenido, proyecto,
                                       estudio=self._estudio)
        widget = self._campos["contenido"]
        widget.delete("1.0", "end")
        widget.insert("1.0", texto)

    def _guardar(self) -> Contrato:
        nombre = self.texto("nombre")
        if not nombre:
            raise DatosInvalidosError("El contrato necesita un nombre.")
        proyecto = self.objeto("proyecto")
        plantilla = self.objeto("plantilla")
        contrato = self._contrato or Contrato(nombre=nombre)
        contrato.nombre = nombre
        contrato.proyecto_id = proyecto.id if proyecto else None
        contrato.plantilla_id = plantilla.id if plantilla else None
        contrato.estado = self.valor_selector("estado")
        contrato.fecha = self.fecha("fecha")
        contrato.contenido = self.texto("contenido")
        return contrato


def DialogoMensaje_error(master: Any, titulo: str, mensaje: str) -> None:
    from .widgets import DialogoMensaje

    DialogoMensaje.error(master, titulo, mensaje)


# --------------------------------------------------------------------------- #
# Ficha del fotógrafo
# --------------------------------------------------------------------------- #


class DialogoFichaFotografo(Dialogo):
    def __init__(self, master: Any, fotografo: Fotografo, equipos: Sequence[Equipo],
                 trabajos: Sequence[TrabajoPendiente]):
        super().__init__(master, f"Ficha: {fotografo.nombre_completo}",
                         ancho=900, alto=760)
        self.separador("Datos personales")
        for etiqueta, valor in (
            ("Nombre", fotografo.nombre_completo),
            ("Teléfono", fotografo.telefono or "—"),
            ("Email", fotografo.email or "—"),
        ):
            self.campo_texto(etiqueta, etiqueta, valor)
            self._campos[etiqueta].configure(state="disabled")

        self.separador(f"Equipos tomados del stock ({len(equipos)})")
        columnas_equipos = [
            {"clave": "serie", "titulo": "N° de serie", "ancho": 130},
            {"clave": "equipo", "titulo": "Marca / Modelo", "ancho": 170},
            {"clave": "service", "titulo": "Próximo service", "ancho": 130, "anchor": "center"},
            {"clave": "notas", "titulo": "Notas", "ancho": 300},
        ]
        filas_equipos = [
            [e.numero_serie or "—", e.descripcion,
             fecha_legible(e.fecha_service_proximo) or "—", e.notas or ""]
            for e in equipos
        ]
        tabla_equipos = Tabla(self.form, columnas_equipos, altura=max(4, len(equipos) + 1))
        tabla_equipos.grid(row=self._fila, column=0, columnspan=2, sticky="ew",
                           padx=10, pady=(2, 6))
        tabla_equipos.actualizar(filas_equipos, list(equipos))
        if not filas_equipos:
            self.nota("No tiene equipos tomados del stock.")
        self._fila += 1

        self.separador(f"Entregas y trabajos ({len(trabajos)})")
        columnas_trabajos = [
            {"clave": "titulo", "titulo": "Trabajo", "ancho": 220},
            {"clave": "rol", "titulo": "Rol", "ancho": 130},
            {"clave": "proyecto", "titulo": "Proyecto", "ancho": 170},
            {"clave": "entrega", "titulo": "Entrega", "ancho": 100, "anchor": "center"},
            {"clave": "estado", "titulo": "Estado", "ancho": 100, "anchor": "center"},
            {"clave": "desc", "titulo": "Descripción", "ancho": 160},
        ]
        filas_trabajos = [
            [t.titulo,
             t.rol or "—",
             (t.proyecto.titulo if t.proyecto else "—") or "—",
             fecha_legible(t.fecha_entrega) or "—",
             str(t.estado),
             t.descripcion or ""]
            for t in trabajos
        ]
        etiquetas = [_tag_trabajo(t) for t in trabajos]
        tabla_trabajos = Tabla(self.form, columnas_trabajos,
                               altura=max(4, len(trabajos) + 1))
        tabla_trabajos.grid(row=self._fila, column=0, columnspan=2, sticky="ew",
                            padx=10, pady=(2, 6))
        tabla_trabajos.actualizar(filas_trabajos, list(trabajos), etiquetas)
        if not filas_trabajos:
            self.nota("Sin trabajos registrados.")
        self._fila += 1

        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")


class DialogoDetalleProyecto(Dialogo):
    """Ficha del proyecto con el desglose de seña, pagos y saldo."""

    def __init__(self, master: Any, proyecto: Proyecto):
        super().__init__(master, f"Proyecto: {proyecto.nombre}",
                         ancho=840, alto=700)
        p = proyecto

        def solo(etiqueta: str, valor: str) -> None:
            self.campo_texto(etiqueta, etiqueta, valor)
            self._campos[etiqueta].configure(state="disabled")

        self.separador("Datos del proyecto")
        solo("Título", p.titulo or "—")
        solo("Tipo", p.tipo or "—")
        solo("Cliente", p.cliente or "—")
        solo("Fecha del evento", fecha_legible(p.fecha_evento) or "—")
        solo("Estado", str(p.estado))
        solo("Fotógrafo responsable",
             p.fotografo.nombre_completo if p.fotografo else "—")
        solo("Dirección / locación", p.direccion or "—")
        if p.notas:
            solo("Notas", p.notas)

        self.separador("Resumen de cobro")
        solo("Cobro total", moneda(p.cobro_total))
        solo("Seña", f"{moneda(p.sena)}"
             + (f"  ·  {fecha_legible(p.sena_fecha)}  ·  {p.sena_medio}"
                if p.sena else ""))
        solo("Pagos parciales", moneda(p.total_pagos_parciales))
        solo("Total abonado", moneda(p.total_pagado))
        saldo = p.obtener_saldo_pendiente()
        self.campo_texto("saldo", "Saldo pendiente", moneda(saldo))
        self._campos["saldo"].configure(state="disabled")

        self.separador(f"Pagos registrados ({len(p.pagos)})")
        columnas = [
            {"clave": "fecha", "titulo": "Fecha", "ancho": 110, "anchor": "center"},
            {"clave": "monto", "titulo": "Monto", "ancho": 130, "anchor": "e"},
            {"clave": "medio", "titulo": "Medio de pago", "ancho": 150},
            {"clave": "notas", "titulo": "Concepto", "ancho": 300},
        ]
        filas = [[fecha_legible(pg.fecha), moneda(pg.monto), pg.medio, pg.notas or ""]
                 for pg in p.pagos]
        tabla = Tabla(self.form, columnas, altura=max(4, len(p.pagos) + 1))
        tabla.grid(row=self._fila, column=0, columnspan=2, sticky="ew",
                   padx=10, pady=(2, 8))
        tabla.actualizar(filas, list(p.pagos))
        if not filas:
            self.nota("Todavía no hay pagos parciales registrados.")
        self._fila += 1

        if saldo > 0:
            self.nota(f"Saldo a cobrar: {moneda(saldo)}. Use «Registrar pago».")
        else:
            self.nota("Proyecto saldado.")
        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")


# --------------------------------------------------------------------------- #
# Acceso — usuarios y contraseñas
# --------------------------------------------------------------------------- #


def _passwords_iguales(dialogo: Dialogo) -> str:
    nueva = dialogo._campos["password"].get()
    if nueva != dialogo._campos["repetir"].get():
        raise DatosInvalidosError("Las contraseñas no coinciden.")
    return nueva


class DialogoUsuario(Dialogo):
    """Alta (devuelve ``(usuario, contraseña)``) o edición (devuelve el usuario)."""

    def __init__(self, master: Any, usuario: Optional[Usuario] = None):
        super().__init__(master, "Editar usuario" if usuario else "Nuevo usuario",
                         ancho=600, alto=480)
        u = usuario
        self._usuario = u
        entrada = self.campo_texto("usuario", "Usuario *", u.usuario if u else "")
        if u is not None:
            entrada.configure(state="disabled")
        self.campo_texto("nombre", "Nombre y apellido", u.nombre if u else "")
        self.campo_texto("email", "Email", u.email if u else "")
        self.campo_selector("rol", "Rol", [str(r) for r in RolUsuario],
                            str(u.rol) if u else str(RolUsuario.USUARIO))
        if u is None:
            self.campo_password("password", "Contraseña *")
            self.campo_password("repetir", "Repetir contraseña *")
            self.nota("Mínimo 8 caracteres, con letras y números. Los administradores "
                      "además gestionan usuarios.")
        else:
            self.campo_check("activo", "Cuenta activa (puede ingresar)", u.activo)
        self.botones("Guardar", self._guardar)

    def _guardar(self):
        if self._usuario is None:
            nuevo = Usuario(usuario=self.texto("usuario"), nombre=self.texto("nombre"),
                            email=self.texto("email"),
                            rol=RolUsuario(self.valor_selector("rol")))
            nuevo.validar()
            return nuevo, _passwords_iguales(self)
        u = self._usuario
        return Usuario(usuario=u.usuario, nombre=self.texto("nombre"),
                       email=self.texto("email"),
                       rol=RolUsuario(self.valor_selector("rol")),
                       activo=self.es_verdadero("activo"), id=u.id,
                       debe_cambiar_password=u.debe_cambiar_password,
                       ultimo_acceso=u.ultimo_acceso, fotografo_id=u.fotografo_id)


class DialogoCambiarPassword(Dialogo):
    """Devuelve ``(actual, nueva)``."""

    def __init__(self, master: Any):
        super().__init__(master, "Cambiar contraseña", ancho=560, alto=340)
        self.campo_password("actual", "Contraseña actual *")
        self.campo_password("password", "Nueva contraseña *")
        self.campo_password("repetir", "Repetir contraseña *")
        self.nota("Mínimo 8 caracteres, con letras y números.")
        self.botones("Cambiar", self._guardar)

    def _guardar(self) -> tuple[str, str]:
        return self._campos["actual"].get(), _passwords_iguales(self)


class DialogoPassword(Dialogo):
    """Pide la contraseña actual para confirmar una operación sensible."""

    def __init__(self, master: Any, titulo: str, nota: str):
        super().__init__(master, titulo, ancho=560, alto=270)
        self.nota(nota)
        self.campo_password("actual", "Contraseña *")
        self.botones("Continuar", lambda: self._campos["actual"].get())


class DialogoSecreto(Dialogo):
    """Muestra una sola vez un código o contraseña provisoria, con botón de copia."""

    def __init__(self, master: Any, titulo: str, nota: str, secreto: str):
        super().__init__(master, titulo, ancho=560, alto=300)
        self.nota(nota)
        entrada = ctk.CTkEntry(self.form, justify="center", height=42,
                               font=("Consolas", 16, "bold"))
        entrada.insert(0, secreto)
        entrada.configure(state="readonly")
        entrada.grid(row=self._fila, column=0, columnspan=2, sticky="ew",
                     padx=10, pady=6)
        self._fila += 1

        def copiar() -> None:
            self.clipboard_clear()
            self.clipboard_append(secreto)
            copia.configure(text="Copiado")

        copia = boton_secundario(self._pie, "Copiar", copiar, ancho=110)
        copia.pack(side="left")
        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")


class DialogoMiCuenta(Dialogo):
    """Datos propios. Devuelve ``(nombre, email)``; la contraseña va aparte."""

    def __init__(self, master: Any, usuario: Usuario, al_cambiar_password,
                 al_regenerar_codigo):
        super().__init__(master, "Mi cuenta", ancho=580, alto=440)
        entrada = self.campo_texto("usuario", "Usuario", usuario.usuario)
        entrada.configure(state="disabled")
        rol = self.campo_texto("rol", "Rol", str(usuario.rol))
        rol.configure(state="disabled")
        self.campo_texto("nombre", "Nombre y apellido", usuario.nombre)
        self.campo_texto("email", "Email", usuario.email)
        self.separador("Seguridad")
        acciones = ctk.CTkFrame(self.form, fg_color="transparent")
        acciones.grid(row=self._fila, column=0, columnspan=2, sticky="w",
                      padx=10, pady=6)
        self._fila += 1
        boton_secundario(acciones, "Cambiar contraseña…",
                         lambda: al_cambiar_password(self), ancho=180).pack(
            side="left", padx=(0, 8))
        boton_secundario(acciones, "Nuevo código de recuperación…",
                         lambda: al_regenerar_codigo(self), ancho=240).pack(side="left")
        self.botones("Guardar", lambda: (self.texto("nombre"), self.texto("email")))



# --------------------------------------------------------------------------- #
# Historial de entregas y egresos
# --------------------------------------------------------------------------- #


def _tag_trabajo(trabajo: TrabajoPendiente) -> str:
    if trabajo.estado == EstadoTrabajo.CANCELADO:
        return "vencido"
    return "pendiente" if trabajo.estado.esta_abierto else "entregado"


class DialogoHistorialEntregas(Dialogo):
    """Entregas de un fotógrafo (o de todos) filtradas por situación.

    ``cargar()`` devuelve los trabajos actuales; ``al_cambiar(trabajo, estado)``
    persiste el nuevo estado.
    """

    FILTROS = {
        "Todas": lambda t: True,
        "Activas": lambda t: t.estado.esta_abierto,
        "Cerradas": lambda t: t.estado == EstadoTrabajo.ENTREGADO,
        "Canceladas": lambda t: t.estado == EstadoTrabajo.CANCELADO,
    }

    def __init__(self, master: Any, titulo: str, cargar, al_cambiar):
        super().__init__(master, titulo, ancho=980, alto=560)
        self._cargar = cargar
        self._al_cambiar = al_cambiar
        self._filtro = ctk.StringVar(value="Todas")
        barra = ctk.CTkFrame(self.form, fg_color="transparent")
        barra.grid(row=self._fila, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 0))
        self._fila += 1
        ctk.CTkSegmentedButton(barra, values=list(self.FILTROS), variable=self._filtro,
                               command=lambda _v: self._refrescar()).pack(side="left")
        boton(barra, "Cancelar entrega",
              lambda: self._cambiar(EstadoTrabajo.CANCELADO), color="peligro",
              ancho=140).pack(side="right")
        boton(barra, "Marcar entregada",
              lambda: self._cambiar(EstadoTrabajo.ENTREGADO), color="exito",
              ancho=140).pack(side="right", padx=6)
        boton_secundario(barra, "Reabrir",
                         lambda: self._cambiar(EstadoTrabajo.PENDIENTE),
                         ancho=90).pack(side="right")
        self.tabla = Tabla(self.form, [
            {"clave": "titulo", "titulo": "Trabajo", "ancho": 210},
            {"clave": "fotografo", "titulo": "Fotógrafo", "ancho": 140},
            {"clave": "rol", "titulo": "Rol", "ancho": 120},
            {"clave": "proyecto", "titulo": "Proyecto", "ancho": 170},
            {"clave": "entrega", "titulo": "Entrega", "ancho": 95, "anchor": "center"},
            {"clave": "estado", "titulo": "Estado", "ancho": 95, "anchor": "center"},
        ], altura=11)
        self.tabla.grid(row=self._fila, column=0, columnspan=2, sticky="nsew",
                        padx=10, pady=10)
        self._fila += 1
        self._resumen = ctk.CTkLabel(self.form, text="", font=FUENTE_NORMAL,
                                     text_color=GRIS_TEXTO, anchor="w")
        self._resumen.grid(row=self._fila, column=0, columnspan=2, sticky="w", padx=10)
        self._fila += 1
        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")
        self._refrescar()

    def _refrescar(self) -> None:
        trabajos = list(self._cargar())
        visibles = [t for t in trabajos if self.FILTROS[self._filtro.get()](t)]
        self.tabla.actualizar(
            [[t.titulo,
              t.fotografo.nombre_completo if t.fotografo else "—",
              t.rol or "—",
              (t.proyecto.titulo if t.proyecto else "") or "—",
              fecha_legible(t.fecha_entrega) or "—",
              str(t.estado)] for t in visibles],
            visibles, [_tag_trabajo(t) for t in visibles])
        cuenta = {n: sum(1 for t in trabajos if f(t)) for n, f in self.FILTROS.items()}
        self._resumen.configure(
            text=f"{cuenta['Todas']} en total · {cuenta['Activas']} activas · "
            f"{cuenta['Cerradas']} cerradas · {cuenta['Canceladas']} canceladas")

    def _cambiar(self, estado: EstadoTrabajo) -> None:
        trabajo = self.tabla.seleccionado()
        if trabajo is None:
            DialogoMensaje.error(self, "Sin selección", "Elija una entrega de la tabla.")
            return
        self._al_cambiar(trabajo, estado)
        self._refrescar()


class DialogoEgreso(Dialogo):
    def __init__(self, master: Any, categorias: Sequence[str],
                 proyectos: Sequence[Proyecto] = ()):
        super().__init__(master, "Registrar egreso", ancho=580, alto=470)
        self.campo_texto("concepto", "Concepto *", "", "Alquiler de luces, viáticos…")
        self.campo_monto("monto", "Monto *")
        self.campo_fecha("fecha", "Fecha", date.today(), opcional=False)
        self.campo_combo("categoria", "Categoría", categorias,
                         categorias[0] if categorias else "Otros")
        self.campo_selector_objetos(
            "proyecto", "Proyecto", proyectos, _etiqueta_proyecto,
            vacio="— Gasto general —", opcional=True,
        )
        self.campo_texto("notas", "Notas")
        self.botones("Registrar", self._guardar)

    def _guardar(self) -> Egreso:
        proyecto = self.objeto("proyecto")
        egreso = Egreso(
            concepto=self.texto("concepto"),
            monto=self.monto("monto"),
            fecha=self.fecha("fecha") or date.today(),
            categoria=self.texto("categoria") or "Otros",
            proyecto_id=proyecto.id if proyecto else None,
            notas=self.texto("notas"),
        )
        egreso.validar()
        return egreso


class DialogoCategorias(Dialogo):
    """Alta y baja de categorías (tarifario o equipos). Opera directo sobre el repositorio."""

    def __init__(self, master: Any, repo: Any, *,
                 titulo: str = "Categorías del tarifario", elementos: str = "servicios"):
        super().__init__(master, titulo, ancho=560, alto=520)
        self._repo = repo
        alta = ctk.CTkFrame(self.form, fg_color="transparent")
        alta.grid(row=self._fila, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 6))
        self._fila += 1
        self._nueva = ctk.CTkEntry(alta, width=300, font=FUENTE_NORMAL,
                                   placeholder_text="Nueva categoría…")
        self._nueva.pack(side="left")
        boton(alta, "Agregar", self._agregar, ancho=100).pack(side="left", padx=8)
        self._nueva.bind("<Return>", lambda _e: (self._agregar(), "break")[1])

        self.tabla = Tabla(self.form, [
            {"clave": "nombre", "titulo": "Categoría", "ancho": 300},
            {"clave": "uso", "titulo": elementos.capitalize(), "ancho": 110,
             "anchor": "center"},
        ], altura=8)
        self.tabla.grid(row=self._fila, column=0, columnspan=2, sticky="nsew",
                        padx=10, pady=6)
        self._fila += 1
        self.nota(f"Sólo se puede quitar una categoría que no tenga {elementos}.")
        boton(self._pie, "Quitar seleccionada", self._quitar, color="peligro",
              ancho=170).pack(side="left")
        boton(self._pie, "Cerrar", self.cancelar, ancho=120).pack(side="right")
        self.bind("<Escape>", lambda _e: self.cancelar())
        self._refrescar()

    def _refrescar(self) -> None:
        filas = self._repo.categorias_con_uso()
        self.tabla.actualizar([[nombre, str(n)] for nombre, n in filas],
                              [nombre for nombre, _n in filas])

    def _intentar(self, accion) -> None:
        try:
            accion()
        except Exception as exc:  # noqa: BLE001 - se muestra al usuario
            DialogoMensaje.error(self, "No se pudo", str(exc))
        self._refrescar()

    def _agregar(self) -> None:
        nombre = self._nueva.get()
        self._intentar(lambda: self._repo.crear_categoria(nombre))
        self._nueva.delete(0, "end")

    def _quitar(self) -> None:
        nombre = self.tabla.seleccionado()
        if nombre is None:
            DialogoMensaje.error(self, "Sin selección", "Elija una categoría de la tabla.")
            return
        self._intentar(lambda: self._repo.eliminar_categoria(nombre))
