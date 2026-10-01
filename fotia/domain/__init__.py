"""Capa de dominio: modelos de negocio sin dependencias de UI ni base de datos."""

from .errors import (
    AsignacionInvalidaError,
    DatosInvalidosError,
    EliminacionRestringidaError,
    EquipoNoDisponibleException,
    EstadoInvalidoError,
    FotiaError,
)
from .models import (
    Cliente,
    Contrato,
    Equipo,
    EstadoEquipo,
    EstadoProyecto,
    EstadoService,
    EstadoTrabajo,
    Evento,
    Fotografo,
    Pago,
    PlantillaContrato,
    Proyecto,
    Servicio,
    TrabajoPendiente,
)

__all__ = [
    "AsignacionInvalidaError",
    "Cliente",
    "Contrato",
    "DatosInvalidosError",
    "EliminacionRestringidaError",
    "Equipo",
    "EquipoNoDisponibleException",
    "EstadoEquipo",
    "EstadoInvalidoError",
    "EstadoProyecto",
    "EstadoService",
    "EstadoTrabajo",
    "Evento",
    "FotiaError",
    "Fotografo",
    "Pago",
    "PlantillaContrato",
    "Proyecto",
    "Servicio",
    "TrabajoPendiente",
]
