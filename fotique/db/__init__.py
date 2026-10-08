"""Capa de datos: SQLite embebido y repositorios."""

from .connection import BaseDatos, conectar
from .repositories import Repositorios

__all__ = [
    "BaseDatos",
    "Repositorios",
    "conectar",
]
