"""Capa de datos: SQLite embebido (RNF-02) y repositorios."""

from .connection import BaseDatos, conectar
from .repositories import Repositorios
from .seed import datos_demo_cargados, cargar_datos_demo

__all__ = [
    "BaseDatos",
    "Repositorios",
    "cargar_datos_demo",
    "conectar",
    "datos_demo_cargados",
]
