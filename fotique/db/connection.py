"""Conexión y ciclo de vida de la base de datos de Fotique."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

from ..domain.errors import ErrorBackups
from ..util import dir_respaldos, ruta_base_datos

ESQUEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")

# Versión del esquema (PRAGMA user_version). 1 = Fotique 1.0/1.1, 2 = Fotique 1.2.
VERSION_ESQUEMA = 2

# Tablas cuya definición cambió en la v2 (CHECK o NOT NULL: SQLite exige
# reconstruirlas) y cómo se copia cada columna que necesita conversión.
_RECONSTRUIR_V2 = {
    "equipos": {"numero_serie": "NULLIF(TRIM(numero_serie), '')"},
    "trabajos_pendientes": {},
    "usuarios": {"rol": "CASE rol WHEN 'Operador' THEN 'Usuario' ELSE rol END"},
}
# Categorías de equipos con las que arranca una base (después se editan a mano).
CATEGORIAS_EQUIPO_INICIALES = ("Cámara", "Iluminación", "Accesorio", "Mantenimiento", "Filtros")

_COLUMNAS_NUEVAS_V2 = {
    "historial_asignaciones": [
        ("proyecto_id", "INTEGER REFERENCES proyectos (id) ON DELETE SET NULL"),
        ("fecha_prevista", "TEXT"),
    ],
    "proyectos": [("tipo", "TEXT NOT NULL DEFAULT ''")],
}


def _columnas(conn: sqlite3.Connection, tabla: str) -> list[str]:
    return [fila[1] for fila in conn.execute(f"PRAGMA table_info({tabla})")]


def _migrar_a_v2(conn: sqlite3.Connection) -> None:
    """Lleva una base de Fotique 1.0/1.1 al esquema de la 1.2 sin perder datos."""
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    # Sin esto, RENAME reescribiría las referencias de las demás tablas hacia
    # la copia vieja que después se borra.
    conn.execute("PRAGMA legacy_alter_table = ON")
    try:
        for tabla, columnas in _COLUMNAS_NUEVAS_V2.items():
            existentes = _columnas(conn, tabla)
            for nombre, definicion in columnas:
                if nombre not in existentes:
                    conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}")
        viejas = [t for t in _RECONSTRUIR_V2 if _columnas(conn, t)]
        for tabla in viejas:
            conn.execute(f"ALTER TABLE {tabla} RENAME TO {tabla}_v1")
        conn.executescript(ESQUEMA)  # crea las tablas con la definición nueva
        conn.execute("PRAGMA foreign_keys = OFF")  # el script lo vuelve a activar
        for tabla in viejas:
            comunes = [c for c in _columnas(conn, f"{tabla}_v1")
                       if c in _columnas(conn, tabla)]
            origen = [_RECONSTRUIR_V2[tabla].get(c, c) for c in comunes]
            conn.execute(
                f"INSERT INTO {tabla} ({', '.join(comunes)}) "
                f"SELECT {', '.join(origen)} FROM {tabla}_v1"
            )
            conn.execute(f"DROP TABLE {tabla}_v1")  # se lleva sus índices
        conn.commit()
    finally:
        conn.execute("PRAGMA legacy_alter_table = OFF")
        conn.execute("PRAGMA foreign_keys = ON")


def _preparar_esquema(conn: sqlite3.Connection, destino: str) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    es_base_existente = bool(_columnas(conn, "equipos"))
    sin_categorias_equipo = not _columnas(conn, "categorias_equipo")
    if es_base_existente and version < VERSION_ESQUEMA:
        if destino != ":memory:":  # copia de seguridad antes de tocar tablas
            copia = Path(destino).with_suffix(Path(destino).suffix + ".antes-de-v2")
            if not copia.exists():
                respaldo = sqlite3.connect(copia)
                try:
                    conn.backup(respaldo)
                finally:
                    respaldo.close()
        _migrar_a_v2(conn)
    conn.executescript(ESQUEMA)
    # La categoría de los equipos llegó en la 1.4: se agrega a las bases previas
    # y la lista se carga una sola vez (lo que se quite después no vuelve).
    if "categoria" not in _columnas(conn, "equipos"):
        conn.execute("ALTER TABLE equipos ADD COLUMN categoria TEXT NOT NULL DEFAULT ''")
    # El producto (qué es el equipo: cámara, lente, flash…) llegó en la 1.5.
    if "producto" not in _columnas(conn, "equipos"):
        conn.execute("ALTER TABLE equipos ADD COLUMN producto TEXT NOT NULL DEFAULT ''")
    if sin_categorias_equipo:
        conn.executemany(
            "INSERT OR IGNORE INTO categorias_equipo (nombre) VALUES (?)",
            [(nombre,) for nombre in CATEGORIAS_EQUIPO_INICIALES],
        )
    # Las categorías del tarifario pasaron a tener lista propia: se completa
    # con las que ya usan los servicios (no hace nada si ya están).
    conn.execute(
        "INSERT OR IGNORE INTO categorias_servicio (nombre) "
        "SELECT DISTINCT categoria FROM servicios WHERE categoria <> ''"
    )
    conn.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
    conn.commit()


def conectar(ruta: Union[str, Path, None] = None) -> sqlite3.Connection:
    """Abre (creando si hace falta) la base y aplica el esquema."""
    destino = str(ruta) if ruta is not None else str(ruta_base_datos())
    if destino != ":memory:":
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(destino)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _preparar_esquema(conn, destino)
    return conn


class BaseDatos:
    """Administra la conexión, los repositorios y los respaldos."""

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
        """Exporta la base completa a un archivo ``.db``/``.sqlite``."""
        if destino is None:
            from ..util import a_texto

            nombre = f"fotique_respaldo_{a_texto(__import__('datetime').date.today())}.db"
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
        """Reemplaza la base activa por un respaldo válido."""
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
