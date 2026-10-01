"""Modelos de dominio de Fotia.

Puros dataclasses: sin SQLite y sin Qt. Toda la regla de negocio que puede
expresarse sobre un objeto vive aquí para poder testearla con ``pytest``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Optional

from .errors import (
    AsignacionInvalidaError,
    DatosInvalidosError,
    EliminacionRestringidaError,
    EquipoNoDisponibleException,
    EstadoInvalidoError,
)


class EstadoEquipo(StrEnum):
    EN_STOCK = "En stock"
    EN_USO = "En uso"


class EstadoTrabajo(StrEnum):
    PENDIENTE = "Pendiente"
    EN_EDICION = "En edición"
    ENTREGADO = "Entregado"


class EstadoProyecto(StrEnum):
    PRESUPUESTO = "Presupuesto"
    CONFIRMADO = "Confirmado"
    EN_CURSO = "En curso"
    CERRADO = "Cerrado"


class EstadoService(StrEnum):
    VENCIDO = "Vencido"
    PROXIMO = "Próximo"
    EN_REGLA = "En regla"
    SIN_FECHA = "Sin fecha"


@dataclass
class Fotografo:
    nombre: str
    apellido: str = ""
    telefono: str = ""
    email: str = ""
    activo: bool = True
    id: Optional[int] = None
    equipos_tomados: list["Equipo"] = field(default_factory=list)
    trabajos: list["TrabajoPendiente"] = field(default_factory=list)

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.nombre_completo or "Sin nombre"

    @property
    def entregas_activas(self) -> list["TrabajoPendiente"]:
        """Trabajos que todavía no fueron entregados (RF-04)."""
        return [t for t in self.trabajos if t.estado != EstadoTrabajo.ENTREGADO]

    def validar(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise DatosInvalidosError("El nombre del fotógrafo es obligatorio.")


@dataclass
class Equipo:
    numero_serie: str
    marca: str
    modelo: str
    estado: EstadoEquipo = EstadoEquipo.EN_STOCK
    id: Optional[int] = None
    fecha_adquisicion: Optional[date] = None
    fecha_service_ultimo: Optional[date] = None
    fecha_service_proximo: Optional[date] = None
    fotografo_actual: Optional[Fotografo] = None
    notas: str = ""

    def __post_init__(self) -> None:
        self.estado = EstadoEquipo(self.estado)
        if not self.numero_serie or not self.numero_serie.strip():
            raise DatosInvalidosError("El número de serie es obligatorio.")
        if self.estado == EstadoEquipo.EN_USO and self.fotografo_actual is None:
            raise AsignacionInvalidaError(
                "Un equipo en uso debe tener un fotógrafo responsable (RF-01)."
            )

    @property
    def descripcion(self) -> str:
        return f"{self.marca} {self.modelo}".strip()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.descripcion} ({self.numero_serie})"

    def asignar_a_fotografo(self, fotografo: Optional[Fotografo]) -> None:
        """Pasa el equipo a ``En uso`` registrando al responsable (RF-02)."""
        if fotografo is None:
            raise AsignacionInvalidaError(
                "Debe seleccionar el fotógrafo responsable del equipo."
            )
        if self.estado == EstadoEquipo.EN_USO:
            raise EquipoNoDisponibleException(
                f"El equipo {self} ya está en uso de "
                f"{self.fotografo_actual.nombre_completo}."
            )
        self.estado = EstadoEquipo.EN_USO
        self.fotografo_actual = fotografo
        if self not in fotografo.equipos_tomados:
            fotografo.equipos_tomados.append(self)

    def devolver(self) -> Optional[Fotografo]:
        """Devuelve el equipo al stock y limpia la asignación actual."""
        if self.estado == EstadoEquipo.EN_STOCK:
            raise EstadoInvalidoError(f"El equipo {self} ya está en stock.")
        anterior = self.fotografo_actual
        if anterior is not None and self in anterior.equipos_tomados:
            anterior.equipos_tomados.remove(self)
        self.fotografo_actual = None
        self.estado = EstadoEquipo.EN_STOCK
        return anterior

    def estado_service(
        self, hoy: Optional[date] = None, dias_aviso: int = 30
    ) -> EstadoService:
        """RF-03: clasifica la próxima fecha de service."""
        if self.fecha_service_proximo is None:
            return EstadoService.SIN_FECHA
        hoy = hoy or date.today()
        if self.fecha_service_proximo < hoy:
            return EstadoService.VENCIDO
        if (self.fecha_service_proximo - hoy).days <= dias_aviso:
            return EstadoService.PROXIMO
        return EstadoService.EN_REGLA


@dataclass
class Cliente:
    nombre: str
    responsable: str = ""
    telefono: str = ""
    direccion: str = ""
    email: str = ""
    id: Optional[int] = None

    def validar(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise DatosInvalidosError("El nombre del cliente es obligatorio.")


@dataclass
class Pago:
    monto: float
    fecha: date
    medio: str = "Efectivo"
    notas: str = ""
    proyecto_id: Optional[int] = None
    id: Optional[int] = None

    def validar(self) -> None:
        if self.monto <= 0:
            raise DatosInvalidosError("El monto del pago debe ser mayor a cero.")


@dataclass
class Proyecto:
    cliente: str = ""
    cobro_total: float = 0.0
    sena: float = 0.0
    titulo: str = ""
    id: Optional[int] = None
    cliente_id: Optional[int] = None
    fotografo: Optional[Fotografo] = None
    fotografo_id: Optional[int] = None
    fecha_evento: Optional[date] = None
    estado: EstadoProyecto = EstadoProyecto.PRESUPUESTO
    sena_fecha: Optional[date] = None
    sena_medio: str = ""
    direccion: str = ""
    notas: str = ""
    pagos: list[Pago] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.estado = EstadoProyecto(self.estado)
        self.cobro_total = float(self.cobro_total or 0.0)
        self.sena = float(self.sena or 0.0)

    @property
    def nombre(self) -> str:
        return self.titulo or f"Proyecto {self.id or ''}".strip()

    @property
    def total_pagos_parciales(self) -> float:
        return round(sum(p.monto for p in self.pagos), 2)

    @property
    def total_pagado(self) -> float:
        return round(self.sena + self.total_pagos_parciales, 2)

    def obtener_saldo_pendiente(self) -> float:
        """RF-05: Cobro Total - Seña - Pagos parciales."""
        return round(self.cobro_total - self.total_pagado, 2)

    @property
    def saldo(self) -> float:
        return self.obtener_saldo_pendiente()

    def validar(self) -> None:
        # En la base el nombre del cliente se resuelve por JOIN: basta el vínculo.
        if not (self.cliente or "").strip() and self.cliente_id is None:
            raise DatosInvalidosError("El cliente del proyecto es obligatorio.")
        if self.cobro_total < 0 or self.sena < 0:
            raise DatosInvalidosError("Los importes no pueden ser negativos.")
        if self.sena > self.cobro_total > 0:
            raise DatosInvalidosError("La seña no puede superar el cobro total.")


@dataclass
class TrabajoPendiente:
    titulo: str
    fotografo_id: Optional[int] = None
    proyecto_id: Optional[int] = None
    fecha_entrega: Optional[date] = None
    estado: EstadoTrabajo = EstadoTrabajo.PENDIENTE
    descripcion: str = ""
    id: Optional[int] = None
    fotografo: Optional[Fotografo] = None
    proyecto: Optional[Proyecto] = None

    def __post_init__(self) -> None:
        self.estado = EstadoTrabajo(self.estado)

    @property
    def esta_activo(self) -> bool:
        return self.estado != EstadoTrabajo.ENTREGADO

    def validar(self) -> None:
        if not self.titulo or not self.titulo.strip():
            raise DatosInvalidosError("El título del trabajo es obligatorio.")
        if self.fotografo_id is None:
            raise DatosInvalidosError("Debe asignar un fotógrafo al trabajo.")


@dataclass
class Servicio:
    nombre: str
    categoria: str = "Otros"
    precio: float = 0.0
    unidad: str = "servicio"
    activo: bool = True
    notas: str = ""
    id: Optional[int] = None

    def validar(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise DatosInvalidosError("El nombre del servicio es obligatorio.")
        if self.precio < 0:
            raise DatosInvalidosError("El precio no puede ser negativo.")


@dataclass
class PlantillaContrato:
    nombre: str
    contenido: str = ""
    id: Optional[int] = None


@dataclass
class Contrato:
    nombre: str
    proyecto_id: Optional[int] = None
    plantilla_id: Optional[int] = None
    contenido: str = ""
    estado: str = "Borrador"
    fecha: Optional[date] = None
    id: Optional[int] = None
    proyecto: Optional[Proyecto] = None


@dataclass
class Evento:
    titulo: str
    fecha: date
    hora: str = ""
    tipo: str = "Sesión"
    fotografo_id: Optional[int] = None
    proyecto_id: Optional[int] = None
    notas: str = ""
    id: Optional[int] = None

    def validar(self) -> None:
        if not self.titulo or not self.titulo.strip():
            raise DatosInvalidosError("El título del evento es obligatorio.")
        if self.fecha is None:
            raise DatosInvalidosError("La fecha del evento es obligatoria.")
