"""Vistas (pantallas) de Fotia."""

from .base import VistaBase
from .calendario import VistaCalendario
from .contratos import VistaContratos
from .equipos import VistaEquipos
from .fotografos import VistaFotografos
from .panel import VistaPanel
from .proyectos import VistaProyectos
from .respaldos import VistaRespaldos
from .servicios import VistaServicios

TODAS = [
    VistaPanel,
    VistaEquipos,
    VistaFotografos,
    VistaProyectos,
    VistaCalendario,
    VistaServicios,
    VistaContratos,
    VistaRespaldos,
]

__all__ = [
    "TODAS",
    "VistaBase",
    "VistaCalendario",
    "VistaContratos",
    "VistaEquipos",
    "VistaFotografos",
    "VistaPanel",
    "VistaProyectos",
    "VistaRespaldos",
    "VistaServicios",
]
