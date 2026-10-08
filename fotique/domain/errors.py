"""Excepciones del dominio Fotique.

Todas derivan de :class:`FotiqueError` para que la capa de UI pueda atrapar
cualquier error de negocio con un único ``except``.
"""

from __future__ import annotations


class FotiqueError(Exception):
    """Error base de negocio de Fotique."""


class DatosInvalidosError(FotiqueError):
    """Datos de entrada incompletos o inválidos (validación de formularios)."""


class EquipoNoDisponibleException(FotiqueError):
    """Se intentó asignar un equipo que ya está ``En uso``."""


class AsignacionInvalidaError(FotiqueError):
    """Un equipo ``En uso`` requiere fotógrafo responsable."""


class EstadoInvalidoError(FotiqueError):
    """Transición de estado no permitida (p. ej. devolver un equipo en stock)."""


class EliminacionRestringidaError(FotiqueError):
    """Violación de integridad referencial de alto nivel."""


class CredencialesInvalidasError(FotiqueError):
    """Usuario, contraseña o código de recuperación incorrectos."""


class CuentaBloqueadaError(FotiqueError):
    """Demasiados intentos fallidos: la cuenta queda bloqueada unos minutos."""


class ErrorBackups(FotiqueError):
    """Falló la exportación/importación de la base de datos."""
