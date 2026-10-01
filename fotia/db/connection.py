"""Conexión y ciclo de vida de la base de datos de Fotia."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

from ..domain.errors import ErrorBackups
from ..util import dir_respaldos, ruta_base_datos

ESQUEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")


def conectar(ruta: Union[str, Path, None] = None) -> sqlite3.Connection:
    """Abre (creando si hace falta) la base y aplica el esquema."""
    destino = str(ruta) if ruta is not None else str(ruta_base_datos())
    if destino != ":memory:":
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(destino)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(ESQUEMA)
    conn.commit()
    return conn


class BaseDatos:
    """Administra la conexión, los repositorios y los respaldos (RNF-05)."""

    def __init__(self, ruta: Union[str, Path, None] = None):
        self.ruta = str(ruta) if ruta is not None else str(ruta_base_datos())
        self.connection: Optional[sqlite3.Connection] = None
        self.repos = None
        self.conectar()

    # -- conexión ---------------------------------------------------------- #
    def conectar(self) -> None:
        from .repositories import Repositorios

        self.connection = conectar(self.ruta)
        self.repos = Repositorios(self.connection)

    @property
    def conn(self) -> sqlite3.Connection:
        if self.connection is None:
            raise ErrorBackups("La base de datos está cerrada.")
        return self.connection

    def cerrar(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            self.repos = None

    # -- integridad y respaldos -------------------------------------------- #
    def verificar_integridad(self, ruta: Optional[Union[str, Path]] = None) -> bool:
        """Comprueba ``PRAGMA integrity_check`` (usado antes de restaurar)."""
        destino = str(ruta) if ruta is not None else self.ruta
        if destino == ":memory:":
            return True
        if not Path(destino).exists():
            raise ErrorBackups(f"No existe el archivo: {destino}")
        otra = sqlite3.connect(destino)
        try:
            resultado = otra.execute("PRAGMA integrity_check").fetchone()[0]
            return str(resultado).lower() == "ok"
        except sqlite3.DatabaseError as exc:
            raise ErrorBackups(f"El archivo no es una base SQLite válida: {destino}") from exc
        finally:
            otra.close()

    def respaldar(self, destino: Union[str, Path, None] = None) -> Path:
        """RNF-05: exporta la base completa a un archivo ``.db``/``.sqlite``."""
        if destino is None:
            from ..util import a_texto

            nombre = f"fotia_respaldo_{a_texto(__import__('datetime').date.today())}.db"
            destino = dir_respaldos() / nombre
        destino = Path(destino)
        if destino.suffix.lower() not in (".db", ".sqlite", ".sqlite3"):
            destino = destino.with_suffix(".db")
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.resolve() == Path(self.ruta).resolve():
            raise ErrorBackups("El respaldo no puede pisar la base activa.")
        destino_db = sqlite3.connect(destino)
        try:
            self.conn.backup(destino_db)
            destino_db.execute("PRAGMA foreign_keys = ON")
            ok = destino_db.execute("PRAGMA integrity_check").fetchone()[0]
            if str(ok).lower() != "ok":
                raise ErrorBackups(f"El respaldo quedó inconsistente: {ok}")
        finally:
            destino_db.close()
        return destino

    def restaurar(self, origen: Union[str, Path]) -> None:
        """RNF-05: reemplaza la base activa por un respaldo válido."""
        origen = Path(origen)
        if not self.verificar_integridad(origen):
            raise ErrorBackups(f"El archivo dañado o no es una base válida: {origen}")
        if self.ruta == ":memory:":
            raise ErrorBackups("No se puede restaurar sobre una base en memoria.")
        destino = Path(self.ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        self.cerrar()
        try:
            respaldo = destino.with_suffix(destino.suffix + ".anterior")
            if destino.exists():
                respaldo.write_bytes(destino.read_bytes())
            destino.write_bytes(origen.read_bytes())
        except OSError as exc:
            raise ErrorBackups(f"No se pudo restaurar: {exc}") from exc
        finally:
            self.conectar()
