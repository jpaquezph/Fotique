"""Utilidades comunes (fechas, moneda, rutas de datos)."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union

APP_NAME = "Fotia"

__all__ = [
    "APP_NAME",
    "a_fecha",
    "a_texto",
    "dir_datos",
    "dir_respaldos",
    "es_frozen",
    "fecha_legible",
    "moneda",
    "ruta_base_datos",
    "ruta_recursos",
]


def a_fecha(valor: Optional[Union[str, date, datetime]]) -> Optional[date]:
    """Convierte ISO (``YYYY-MM-DD``), ``date`` o ``datetime`` ➜ ``date``."""
    from .domain.errors import DatosInvalidosError

    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if "T" in texto:
        texto = texto.split("T", 1)[0]
    try:
        return datetime.strptime(texto[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise DatosInvalidosError(f"Fecha inválida: {valor!r}") from exc


def a_texto(valor: Optional[Union[str, date, datetime]]) -> str:
    """Normaliza a ISO para guardar en SQLite (``""`` cuando no hay fecha)."""
    if valor is None or valor == "":
        return ""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)[:10]


def fecha_legible(valor: Optional[Union[str, date, datetime]]) -> str:
    """``2026-09-30`` ➜ ``30/09/2026`` (``""`` si no hay fecha)."""
    f = a_fecha(valor)
    return f.strftime("%d/%m/%Y") if f else ""


def moneda(valor: Optional[float]) -> str:
    """Formatea importes en estilo local: ``150000`` ➜ ``$ 150.000,00``."""
    if valor is None:
        valor = 0.0
    signo = "-" if valor < 0 else ""
    texto = f"{abs(float(valor)):,.2f}"
    texto = texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{signo}$ {texto}"


def es_frozen() -> bool:
    """``True`` cuando corre empaquetado con PyInstaller."""
    return getattr(sys, "frozen", False)


def dir_datos() -> Path:
    """Carpeta de datos de la aplicación (base de datos y respaldos)."""
    if override := os.environ.get("FOTIA_DATA_DIR"):
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME.lower()
    base.mkdir(parents=True, exist_ok=True)
    return base


def ruta_base_datos() -> Path:
    """Ruta de la base SQLite (sobrescribible con ``FOTIA_DB``)."""
    if override := os.environ.get("FOTIA_DB"):
        return Path(override)
    return dir_datos() / "fotia.db"


def dir_respaldos() -> Path:
    carpeta = dir_datos() / "respaldos"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def ruta_recursos() -> Path:
    """Rutas de assets empaquetados (compatible con PyInstaller)."""
    if es_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return Path(__file__).parent
