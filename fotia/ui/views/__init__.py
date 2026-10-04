"""Vistas (pantallas) de Fotia."""

from .base import VistaBase
from .calendario import VistaCalendario
from .contratos import VistaContratos
from .equipos import VistaEquipos
from .fotografos import VistaFotografos
from .panel import VistaPanel
from .proyectos import VistaProyectos
from .respaldos import VistaRespaldos
from .resumen import VistaResumen
from .servicios import VistaServicios
from .usuarios import VistaUsuarios

TODAS = [
    VistaPanel,
    VistaEquipos,
    VistaFotografos,
    VistaProyectos,
    VistaCalendario,
    VistaServicios,
    VistaContratos,
    VistaRespaldos,
    VistaResumen,
    VistaUsuarios,
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
    "VistaResumen",
    "VistaServicios",
    "VistaUsuarios",
]
