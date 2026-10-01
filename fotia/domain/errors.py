"""Excepciones del dominio Fotia.

Todas derivan de :class:`FotiaError` para que la capa de UI pueda atrapar
cualquier error de negocio con un único ``except``.
"""

from __future__ import annotations


class FotiaError(Exception):
    """Error base de negocio de Fotia."""


class DatosInvalidosError(FotiaError):
    """Datos de entrada incompletos o inválidos (validación de formularios)."""


class EquipoNoDisponibleException(FotiaError):
    """Se intentó asignar un equipo que ya está ``En uso``."""


class AsignacionInvalidaError(FotiaError):
    """Un equipo ``En uso`` requiere fotógrafo responsable (RF-01)."""


class EstadoInvalidoError(FotiaError):
    """Transición de estado no permitida (p. ej. devolver un equipo en stock)."""


class EliminacionRestringidaError(FotiaError):
    """Violación de integridad referencial de alto nivel (RNF-04)."""


class ErrorBackups(FotiaError):
    """Falló la exportación/importación de la base de datos."""
