"""Repositorios de Fotia: CRUD + consultas sobre SQLite.

Cada repositorio traduce filas ➜ objetos de dominio y viceversa; las reglas de
negocio (asignaciones, saldos, eliminaciones restringidas) viven en
``fotia.domain`` y aquí sólo se invocan y persisten.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional, Sequence, Union

from ..domain import auth
from ..domain.errors import (
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    DatosInvalidosError,
    EliminacionRestringidaError,
)
from ..domain.models import (
    CATEGORIAS_EGRESO,
    ROLES_TRABAJO,
    TIPOS_PROYECTO,
    Cliente,
    Contrato,
    Egreso,
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
    RolUsuario,
    Servicio,
    TrabajoPendiente,
    Usuario,
)
from ..domain.services import a_fecha, a_texto, equipos_en_alerta, validar_eliminacion_fotografo

Fecha = Optional[Union[str, date]]


# --------------------------------------------------------------------------- #
# Helpers de mapeo
# --------------------------------------------------------------------------- #


def _f(valor: Fecha) -> Optional[str]:
    """ISO para SQLite (``None`` cuando no hay fecha)."""
    return a_texto(valor) or None


def _map_fotografo(row: sqlite3.Row) -> Fotografo:
    return Fotografo(
        nombre=row["nombre"],
        apellido=row["apellido"],
        telefono=row["telefono"],
        email=row["email"],
        activo=bool(row["activo"]),
        id=row["id"],
    )


_EQUIPO_SQL = """
    SELECT e.*,
           f.id        AS f_id,
           f.nombre    AS f_nombre,
           f.apellido  AS f_apellido,
           f.telefono  AS f_telefono,
           f.email     AS f_email,
           f.activo    AS f_activo
      FROM equipos e
      LEFT JOIN fotografos f ON f.id = e.fotografo_id
"""


def _map_equipo(row: sqlite3.Row) -> Equipo:
    fotografo = None
    if row["f_id"] is not None:
        fotografo = Fotografo(
            nombre=row["f_nombre"],
            apellido=row["f_apellido"],
            telefono=row["f_telefono"],
            email=row["f_email"],
            activo=bool(row["f_activo"]),
            id=row["f_id"],
        )
    return Equipo(
        numero_serie=row["numero_serie"] or "",
        marca=row["marca"],
        modelo=row["modelo"],
        estado=EstadoEquipo(row["estado"]),
        id=row["id"],
        fecha_adquisicion=a_fecha(row["fecha_adquisicion"]),
        fecha_service_ultimo=a_fecha(row["fecha_service_ultimo"]),
        fecha_service_proximo=a_fecha(row["fecha_service_proximo"]),
        fotografo_actual=fotografo,
        notas=row["notas"] or "",
    )


_PROYECTO_SQL = """
    SELECT p.*,
           c.nombre           AS cliente_nombre,
           c.telefono         AS cliente_telefono,
           f.id               AS f_id,
           f.nombre           AS f_nombre,
           f.apellido         AS f_apellido,
           f.telefono         AS f_telefono,
           f.email            AS f_email,
           f.activo           AS f_activo
      FROM proyectos p
      JOIN clientes c   ON c.id = p.cliente_id
      LEFT JOIN fotografos f ON f.id = p.fotografo_id
"""


def _map_proyecto(row: sqlite3.Row, pagos: Sequence[Pago] = ()) -> Proyecto:
    fotografo = None
    if row["f_id"] is not None:
        fotografo = Fotografo(
            nombre=row["f_nombre"],
            apellido=row["f_apellido"],
            telefono=row["f_telefono"],
            email=row["f_email"],
            activo=bool(row["f_activo"]),
            id=row["f_id"],
        )
    proyecto = Proyecto(
        cliente=row["cliente_nombre"],
        cobro_total=row["cobro_total"],
        sena=row["sena_monto"],
        titulo=row["titulo"] or "",
        id=row["id"],
        cliente_id=row["cliente_id"],
        fotografo=fotografo,
        fotografo_id=row["fotografo_id"],
        fecha_evento=a_fecha(row["fecha_evento"]),
        estado=EstadoProyecto(row["estado"]),
        sena_fecha=a_fecha(row["sena_fecha"]),
        sena_medio=row["sena_medio"] or "",
        direccion=row["direccion"] or "",
        notas=row["notas"] or "",
        pagos=list(pagos),
        tipo=row["tipo"] or "",
    )
    proyecto.telefono_cliente = row["cliente_telefono"] or ""  # type: ignore[attr-defined]
    return proyecto


# --------------------------------------------------------------------------- #
# Módulo B — Fotógrafos
# --------------------------------------------------------------------------- #


class FotografoRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def listar(self, incluir_inactivos: bool = True) -> list[Fotografo]:
        where = "" if incluir_inactivos else "WHERE activo = 1"
        filas = self.conn.execute(
            f"SELECT * FROM fotografos {where} ORDER BY nombre, apellido"
        ).fetchall()
        return [_map_fotografo(r) for r in filas]

    def obtener(self, fotografo_id: int) -> Optional[Fotografo]:
        fila = self.conn.execute(
            "SELECT * FROM fotografos WHERE id = ?", (fotografo_id,)
        ).fetchone()
        return _map_fotografo(fila) if fila else None

    def detalle(self, fotografo_id: int) -> Optional[Fotografo]:
        """Fotógrafo con sus equipos tomados y sus trabajos."""
        fotografo = self.obtener(fotografo_id)
        if fotografo is None:
            return None
        fotografo.equipos_tomados = self.equipos_de(fotografo_id)
        fotografo.trabajos = self.trabajos_de(fotografo_id)
        return fotografo

    def listar_resumen(self) -> list[dict]:
        """Listado con contadores calculados en SQL (Una sola consulta)."""
        sql = (
            "SELECT f.*, "
            " (SELECT COUNT(*) FROM equipos e WHERE e.fotografo_id = f.id) AS n_equipos,"
            " (SELECT COUNT(*) FROM trabajos_pendientes t WHERE t.fotografo_id = f.id "
            "   AND t.estado IN ('Pendiente', 'En edición')) AS n_activos,"
            " (SELECT MIN(t.fecha_entrega) FROM trabajos_pendientes t "
            "   WHERE t.fotografo_id = f.id AND t.estado IN ('Pendiente', 'En edición')) "
            "   AS proxima, "
            " (SELECT u.rol FROM usuarios u WHERE u.fotografo_id = f.id LIMIT 1) AS rol "
            "FROM fotografos f ORDER BY f.nombre, f.apellido"
        )
        filas = self.conn.execute(sql).fetchall()
        return [
            {
                "fotografo": _map_fotografo(r),
                "n_equipos": int(r["n_equipos"]),
                "n_activos": int(r["n_activos"]),
                "proxima": a_fecha(r["proxima"]),
                "rol": r["rol"] or "",
            }
            for r in filas
        ]

    def equipos_de(self, fotografo_id: int) -> list[Equipo]:
        filas = self.conn.execute(
            _EQUIPO_SQL + " WHERE e.fotografo_id = ? ORDER BY e.marca, e.modelo",
            (fotografo_id,),
        ).fetchall()
        return [_map_equipo(r) for r in filas]

    def trabajos_de(
        self, fotografo_id: int, solo_activos: bool = False
    ) -> list[TrabajoPendiente]:
        sql = (
            "SELECT t.*, f.id AS f_id, f.nombre AS f_nombre, f.apellido AS f_apellido, "
            "p.id AS p_id, p.titulo AS p_titulo FROM trabajos_pendientes t "
            "JOIN fotografos f ON f.id = t.fotografo_id "
            "LEFT JOIN proyectos p ON p.id = t.proyecto_id "
            "WHERE t.fotografo_id = ?"
        )
        if solo_activos:
            sql += " AND t.estado IN ('Pendiente', 'En edición')"
        sql += " ORDER BY COALESCE(t.fecha_entrega, '9999-12-31'), t.id"
        filas = self.conn.execute(sql, (fotografo_id,)).fetchall()
        return [_map_trabajo(r) for r in filas]

    def crear(self, fotografo: Fotografo) -> Fotografo:
        fotografo.validar()
        cur = self.conn.execute(
            "INSERT INTO fotografos (nombre, apellido, telefono, email, activo) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                fotografo.nombre.strip(),
                fotografo.apellido.strip(),
                fotografo.telefono,
                fotografo.email,
                1 if fotografo.activo else 0,
            ),
        )
        fotografo.id = cur.lastrowid
        self.conn.commit()
        return fotografo

    def actualizar(self, fotografo: Fotografo) -> Fotografo:
        if fotografo.id is None:
            raise DatosInvalidosError("Fotógrafo sin id: no se puede actualizar.")
        fotografo.validar()
        self.conn.execute(
            "UPDATE fotografos SET nombre=?, apellido=?, telefono=?, email=?, activo=? "
            "WHERE id=?",
            (
                fotografo.nombre.strip(),
                fotografo.apellido.strip(),
                fotografo.telefono,
                fotografo.email,
                1 if fotografo.activo else 0,
                fotografo.id,
            ),
        )
        self.conn.commit()
        return fotografo

    def eliminar(self, fotografo_id: int) -> None:
        """Bloquea borrar fotógrafos con entregas o equipos activos."""
        fotografo = self.detalle(fotografo_id)
        if fotografo is None:
            return
        validar_eliminacion_fotografo(fotografo)
        try:
            self.conn.execute("DELETE FROM fotografos WHERE id = ?", (fotografo_id,))
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise EliminacionRestringidaError(
                "No se puede eliminar: el fotógrafo está referenciado por otros registros."
            ) from exc


# --------------------------------------------------------------------------- #
# Módulo A — Equipos
# --------------------------------------------------------------------------- #


class EquipoRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def listar(
        self, estado: Optional[EstadoEquipo] = None, texto: str = ""
    ) -> list[Equipo]:
        sql = _EQUIPO_SQL
        condiciones, params = [], []
        if estado is not None:
            condiciones.append("e.estado = ?")
            params.append(str(estado))
        if texto.strip():
            condiciones.append(
                "(COALESCE(e.numero_serie, '') LIKE ? OR e.marca LIKE ? OR e.modelo LIKE ? "
                "OR COALESCE(f.nombre, '') LIKE ? OR COALESCE(f.apellido, '') LIKE ?)"
            )
            patron = f"%{texto.strip()}%"
            params.extend([patron] * 5)
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY e.estado DESC, e.marca, e.modelo"
        filas = self.conn.execute(sql, params).fetchall()
        return [_map_equipo(r) for r in filas]

    def obtener(self, equipo_id: int) -> Optional[Equipo]:
        fila = self.conn.execute(_EQUIPO_SQL + " WHERE e.id = ?", (equipo_id,)).fetchone()
        return _map_equipo(fila) if fila else None

    def crear(self, equipo: Equipo) -> Equipo:
        if equipo.estado == EstadoEquipo.EN_USO:
            raise DatosInvalidosError(
                "Un equipo recién creado no puede estar 'En uso'. Asígnelo desde el stock."
            )
        if not equipo.marca.strip() or not equipo.modelo.strip():
            raise DatosInvalidosError("Marca y modelo son obligatorios.")
        try:
            cur = self.conn.execute(
                "INSERT INTO equipos (numero_serie, marca, modelo, fecha_adquisicion, "
                "fecha_service_ultimo, fecha_service_proximo, estado, fotografo_id, notas) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    equipo.numero_serie.strip() or None,
                    equipo.marca.strip(),
                    equipo.modelo.strip(),
                    _f(equipo.fecha_adquisicion),
                    _f(equipo.fecha_service_ultimo),
                    _f(equipo.fecha_service_proximo),
                    str(equipo.estado),
                    None,
                    equipo.notas or "",
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DatosInvalidosError(
                f"Ya existe un equipo con el número de serie {equipo.numero_serie}."
            ) from exc
        equipo.id = cur.lastrowid
        self.conn.commit()
        return equipo

    def actualizar(self, equipo: Equipo) -> Equipo:
        if equipo.id is None:
            raise DatosInvalidosError("Equipo sin id: no se puede actualizar.")
        if equipo.estado == EstadoEquipo.EN_USO and equipo.fotografo_actual is None:
            raise DatosInvalidosError("Un equipo 'En uso' requiere fotógrafo responsable.")
        if not equipo.marca.strip() or not equipo.modelo.strip():
            raise DatosInvalidosError("Marca y modelo son obligatorios.")
        try:
            self.conn.execute(
                "UPDATE equipos SET numero_serie=?, marca=?, modelo=?, "
                "fecha_adquisicion=?, fecha_service_ultimo=?, fecha_service_proximo=?, "
                "estado=?, fotografo_id=?, notas=? WHERE id=?",
                (
                    equipo.numero_serie.strip() or None,
                    equipo.marca.strip(),
                    equipo.modelo.strip(),
                    _f(equipo.fecha_adquisicion),
                    _f(equipo.fecha_service_ultimo),
                    _f(equipo.fecha_service_proximo),
                    str(equipo.estado),
                    equipo.fotografo_actual.id if equipo.fotografo_actual else None,
                    equipo.notas or "",
                    equipo.id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DatosInvalidosError(
                f"Ya existe un equipo con el número de serie {equipo.numero_serie}."
            ) from exc
        self.conn.commit()
        return equipo

    def eliminar(self, equipo_id: int) -> None:
        equipo = self.obtener(equipo_id)
        if equipo is None:
            return
        if equipo.estado == EstadoEquipo.EN_USO:
            raise EliminacionRestringidaError(
                "Devuelva el equipo al stock antes de eliminarlo."
            )
        self.conn.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
        self.conn.commit()

    def asignar(
        self,
        equipo_id: int,
        fotografo_id: int,
        fecha: Fecha = None,
        observaciones: str = "",
        *,
        proyecto_id: Optional[int] = None,
        fecha_prevista: Fecha = None,
    ) -> Equipo:
        """Transición a ``En uso`` + registro en el historial.

        ``fecha`` es el retiro; ``fecha_prevista``, cuándo se espera la entrega.
        """
        equipo = self.obtener(equipo_id)
        if equipo is None:
            raise DatosInvalidosError("El equipo seleccionado no existe.")
        fila = self.conn.execute(
            "SELECT * FROM fotografos WHERE id = ?", (fotografo_id,)
        ).fetchone()
        if fila is None:
            raise DatosInvalidosError("El fotógrafo seleccionado no existe.")
        retiro = a_fecha(fecha) or date.today()
        prevista = a_fecha(fecha_prevista)
        if prevista is not None and prevista < retiro:
            raise DatosInvalidosError(
                "La fecha de entrega no puede ser anterior a la de retiro."
            )
        fotografo = _map_fotografo(fila)
        equipo.asignar_a_fotografo(fotografo)  # lanza EquipoNoDisponibleException
        self.conn.execute(
            "UPDATE equipos SET estado = 'En uso', fotografo_id = ? WHERE id = ?",
            (fotografo_id, equipo_id),
        )
        self.conn.execute(
            "INSERT INTO historial_asignaciones "
            "(equipo_id, fotografo_id, fecha_asignacion, observaciones, proyecto_id, "
            "fecha_prevista) VALUES (?, ?, ?, ?, ?, ?)",
            (equipo_id, fotografo_id, a_texto(retiro), observaciones, proyecto_id,
             _f(prevista)),
        )
        self.conn.commit()
        return equipo

    def devolver(
        self, equipo_id: int, fecha: Fecha = None, observaciones: str = ""
    ) -> Equipo:
        equipo = self.obtener(equipo_id)
        if equipo is None:
            raise DatosInvalidosError("El equipo seleccionado no existe.")
        equipo.devolver()  # lanza EstadoInvalidoError si ya estaba en stock
        self.conn.execute(
            "UPDATE equipos SET estado = 'En stock', fotografo_id = NULL WHERE id = ?",
            (equipo_id,),
        )
        self.conn.execute(
            "UPDATE historial_asignaciones SET fecha_devolucion = ?, "
            "observaciones = CASE WHEN ? = '' THEN observaciones ELSE ? END "
            "WHERE equipo_id = ? AND fecha_devolucion IS NULL",
            (_f(fecha) or a_texto(date.today()), observaciones, observaciones, equipo_id),
        )
        self.conn.commit()
        return equipo

    def historial(
        self, equipo_id: Optional[int] = None, fotografo_id: Optional[int] = None
    ) -> list[dict]:
        sql = (
            "SELECT h.*, e.marca, e.modelo, e.numero_serie, "
            "f.nombre AS f_nombre, f.apellido AS f_apellido, p.titulo AS p_titulo "
            "FROM historial_asignaciones h "
            "JOIN equipos e ON e.id = h.equipo_id "
            "LEFT JOIN fotografos f ON f.id = h.fotografo_id "
            "LEFT JOIN proyectos p ON p.id = h.proyecto_id WHERE 1=1"
        )
        params: list = []
        if equipo_id is not None:
            sql += " AND h.equipo_id = ?"
            params.append(equipo_id)
        if fotografo_id is not None:
            sql += " AND h.fotografo_id = ?"
            params.append(fotografo_id)
        sql += " ORDER BY h.fecha_asignacion DESC, h.id DESC"
        filas = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in filas]

    def alertas_service(
        self, dias_aviso: int = 30, hoy: Optional[date] = None
    ) -> list[tuple[Equipo, EstadoService]]:
        """Service vencido o próximo a vencer."""
        return equipos_en_alerta(self.listar(), hoy=hoy, dias_aviso=dias_aviso)


# --------------------------------------------------------------------------- #
# Clientes
# --------------------------------------------------------------------------- #


class ClienteRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _map(row: sqlite3.Row) -> Cliente:
        return Cliente(
            nombre=row["nombre"],
            responsable=row["responsable"],
            telefono=row["telefono"],
            direccion=row["direccion"],
            email=row["email"],
            id=row["id"],
        )

    def listar(self) -> list[Cliente]:
        filas = self.conn.execute(
            "SELECT * FROM clientes ORDER BY nombre"
        ).fetchall()
        return [self._map(r) for r in filas]

    def obtener(self, cliente_id: int) -> Optional[Cliente]:
        fila = self.conn.execute(
            "SELECT * FROM clientes WHERE id = ?", (cliente_id,)
        ).fetchone()
        return self._map(fila) if fila else None

    def crear(self, cliente: Cliente) -> Cliente:
        cliente.validar()
        cur = self.conn.execute(
            "INSERT INTO clientes (nombre, responsable, telefono, email, direccion) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                cliente.nombre.strip(),
                cliente.responsable,
                cliente.telefono,
                cliente.email,
                cliente.direccion,
            ),
        )
        cliente.id = cur.lastrowid
        self.conn.commit()
        return cliente

    def actualizar(self, cliente: Cliente) -> Cliente:
        if cliente.id is None:
            raise DatosInvalidosError("Cliente sin id: no se puede actualizar.")
        cliente.validar()
        self.conn.execute(
            "UPDATE clientes SET nombre=?, responsable=?, telefono=?, email=?, "
            "direccion=? WHERE id=?",
            (
                cliente.nombre.strip(),
                cliente.responsable,
                cliente.telefono,
                cliente.email,
                cliente.direccion,
                cliente.id,
            ),
        )
        self.conn.commit()
        return cliente

    def eliminar(self, cliente_id: int) -> None:
        try:
            self.conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise EliminacionRestringidaError(
                "No se puede eliminar el cliente: tiene proyectos asociados."
            ) from exc


# --------------------------------------------------------------------------- #
# Módulo C — Proyectos, seña y pagos
# --------------------------------------------------------------------------- #


def _map_trabajo(row: sqlite3.Row) -> TrabajoPendiente:
    fotografo = None
    if "f_id" in row.keys() and row["f_id"] is not None:
        fotografo = Fotografo(nombre=row["f_nombre"], apellido=row["f_apellido"], id=row["f_id"])
    proyecto = None
    if "p_id" in row.keys() and row["p_id"] is not None:
        proyecto = Proyecto(titulo=row["p_titulo"] or "", id=row["p_id"])
    return TrabajoPendiente(
        titulo=row["titulo"],
        fotografo_id=row["fotografo_id"],
        proyecto_id=row["proyecto_id"],
        fecha_entrega=a_fecha(row["fecha_entrega"]),
        estado=EstadoTrabajo(row["estado"]),
        descripcion=row["descripcion"] or "",
        id=row["id"],
        fotografo=fotografo,
        proyecto=proyecto,
        rol=row["rol"] or "",
    )


class ProyectoRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -- consultas --------------------------------------------------------- #
    def listar(self) -> list[Proyecto]:
        filas = self.conn.execute(
            _PROYECTO_SQL
            + " ORDER BY COALESCE(p.fecha_evento, '9999-12-31'), p.id DESC"
        ).fetchall()
        proyectos = [_map_proyecto(r) for r in filas]
        pagos = self.pagos_por_proyecto([p.id for p in proyectos if p.id])
        for proyecto in proyectos:
            proyecto.pagos = pagos.get(proyecto.id, [])
        return proyectos

    def titulos(self) -> dict[int, str]:
        """``id ➜ título`` sin cargar clientes ni pagos (calendario)."""
        filas = self.conn.execute("SELECT id, titulo FROM proyectos").fetchall()
        return {r["id"]: r["titulo"] or "" for r in filas}

    def obtener(self, proyecto_id: int) -> Optional[Proyecto]:
        fila = self.conn.execute(
            _PROYECTO_SQL + " WHERE p.id = ?", (proyecto_id,)
        ).fetchone()
        if fila is None:
            return None
        return _map_proyecto(fila, self.pagos_de(proyecto_id))

    def pagos_de(self, proyecto_id: int) -> list[Pago]:
        filas = self.conn.execute(
            "SELECT * FROM pagos WHERE proyecto_id = ? ORDER BY fecha, id",
            (proyecto_id,),
        ).fetchall()
        return [
            Pago(
                monto=r["monto"],
                fecha=a_fecha(r["fecha"]) or date.today(),
                medio=r["medio"],
                notas=r["notas"] or "",
                proyecto_id=r["proyecto_id"],
                id=r["id"],
            )
            for r in filas
        ]

    def pagos_por_proyecto(self, ids: Sequence[int]) -> dict[int, list[Pago]]:
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        filas = self.conn.execute(
            f"SELECT * FROM pagos WHERE proyecto_id IN ({placeholders}) ORDER BY fecha, id",
            list(ids),
        ).fetchall()
        resultado: dict[int, list[Pago]] = {}
        for r in filas:
            resultado.setdefault(r["proyecto_id"], []).append(
                Pago(
                    monto=r["monto"],
                    fecha=a_fecha(r["fecha"]) or date.today(),
                    medio=r["medio"],
                    notas=r["notas"] or "",
                    proyecto_id=r["proyecto_id"],
                    id=r["id"],
                )
            )
        return resultado

    # -- escritura --------------------------------------------------------- #
    def crear(self, proyecto: Proyecto) -> Proyecto:
        proyecto.validar()
        if proyecto.cliente_id is None:
            raise DatosInvalidosError("Debe indicar el cliente del proyecto.")
        cur = self.conn.execute(
            "INSERT INTO proyectos (titulo, cliente_id, fotografo_id, fecha_evento, "
            "estado, cobro_total, sena_monto, sena_fecha, sena_medio, direccion, notas, "
            "tipo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                proyecto.titulo.strip(),
                proyecto.cliente_id,
                proyecto.fotografo_id,
                _f(proyecto.fecha_evento),
                str(proyecto.estado),
                proyecto.cobro_total,
                proyecto.sena,
                _f(proyecto.sena_fecha),
                proyecto.sena_medio,
                proyecto.direccion,
                proyecto.notas,
                proyecto.tipo.strip(),
            ),
        )
        proyecto.id = cur.lastrowid
        self.conn.commit()
        return proyecto

    def actualizar(self, proyecto: Proyecto) -> Proyecto:
        if proyecto.id is None:
            raise DatosInvalidosError("Proyecto sin id: no se puede actualizar.")
        proyecto.validar()
        abonado = self.conn.execute(
            "SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE proyecto_id = ?",
            (proyecto.id,),
        ).fetchone()[0] + proyecto.sena
        if round(abonado - proyecto.cobro_total, 2) > 0:
            raise DatosInvalidosError(
                "El cobro total no puede ser menor a lo ya abonado (seña + pagos)."
            )
        self.conn.execute(
            "UPDATE proyectos SET titulo=?, cliente_id=?, fotografo_id=?, fecha_evento=?, "
            "estado=?, cobro_total=?, sena_monto=?, sena_fecha=?, sena_medio=?, "
            "direccion=?, notas=?, tipo=? WHERE id=?",
            (
                proyecto.titulo.strip(),
                proyecto.cliente_id,
                proyecto.fotografo_id,
                _f(proyecto.fecha_evento),
                str(proyecto.estado),
                proyecto.cobro_total,
                proyecto.sena,
                _f(proyecto.sena_fecha),
                proyecto.sena_medio,
                proyecto.direccion,
                proyecto.notas,
                proyecto.tipo.strip(),
                proyecto.id,
            ),
        )
        self.conn.commit()
        return proyecto

    def eliminar(self, proyecto_id: int) -> None:
        self.conn.execute("DELETE FROM proyectos WHERE id = ?", (proyecto_id,))
        self.conn.commit()

    # -- cobros ------------------------------------------------------------ #
    def crear_pago(
        self,
        proyecto_id: int,
        monto: float,
        fecha: Fecha = None,
        medio: str = "Efectivo",
        notas: str = "",
    ) -> Pago:
        proyecto = self.obtener(proyecto_id)
        if proyecto is None:
            raise DatosInvalidosError("El proyecto seleccionado no existe.")
        proyecto.validar_pago(float(monto))
        cur = self.conn.execute(
            "INSERT INTO pagos (proyecto_id, monto, fecha, medio, notas) VALUES (?, ?, ?, ?, ?)",
            (proyecto_id, float(monto), _f(fecha) or a_texto(date.today()), medio, notas),
        )
        self.conn.commit()
        return Pago(
            monto=float(monto),
            fecha=a_fecha(fecha) or date.today(),
            medio=medio,
            notas=notas,
            proyecto_id=proyecto_id,
            id=cur.lastrowid,
        )

    def tipos(self) -> list[str]:
        """Tipos de proyecto sugeridos: los de partida más los ya usados."""
        usados = [r[0] for r in self.conn.execute(
            "SELECT DISTINCT tipo FROM proyectos WHERE tipo <> '' ORDER BY tipo")]
        return TIPOS_PROYECTO + [t for t in usados if t not in TIPOS_PROYECTO]

    def eliminar_pago(self, pago_id: int) -> None:
        self.conn.execute("DELETE FROM pagos WHERE id = ?", (pago_id,))
        self.conn.commit()

    def registrar_sena(
        self, proyecto_id: int, monto: float, fecha: Fecha = None, medio: str = "Efectivo"
    ) -> None:
        if monto < 0:
            raise DatosInvalidosError("La seña no puede ser negativa.")
        proyecto = self.obtener(proyecto_id)
        if proyecto is not None and round(
            monto + proyecto.total_pagos_parciales - proyecto.cobro_total, 2
        ) > 0:
            raise DatosInvalidosError("La seña más los pagos supera el cobro total.")
        self.conn.execute(
            "UPDATE proyectos SET sena_monto = ?, sena_fecha = ?, sena_medio = ? WHERE id = ?",
            (float(monto), _f(fecha) or a_texto(date.today()), medio, proyecto_id),
        )
        self.conn.commit()


# --------------------------------------------------------------------------- #
# Módulo D — Servicios, plantillas y contratos
# --------------------------------------------------------------------------- #


class ServicioRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _map(row: sqlite3.Row) -> Servicio:
        return Servicio(
            nombre=row["nombre"],
            categoria=row["categoria"],
            precio=row["precio"],
            unidad=row["unidad"],
            activo=bool(row["activo"]),
            notas=row["notas"] or "",
            id=row["id"],
        )

    def listar(self, solo_activos: bool = False) -> list[Servicio]:
        sql = "SELECT * FROM servicios"
        if solo_activos:
            sql += " WHERE activo = 1"
        sql += " ORDER BY categoria, nombre"
        return [self._map(r) for r in self.conn.execute(sql).fetchall()]

    def obtener(self, servicio_id: int) -> Optional[Servicio]:
        fila = self.conn.execute(
            "SELECT * FROM servicios WHERE id = ?", (servicio_id,)
        ).fetchone()
        return self._map(fila) if fila else None

    def crear(self, servicio: Servicio) -> Servicio:
        servicio.validar()
        cur = self.conn.execute(
            "INSERT INTO servicios (nombre, categoria, precio, unidad, activo, notas) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                servicio.nombre.strip(),
                servicio.categoria,
                servicio.precio,
                servicio.unidad,
                1 if servicio.activo else 0,
                servicio.notas,
            ),
        )
        servicio.id = cur.lastrowid
        self.conn.commit()
        return servicio

    def actualizar(self, servicio: Servicio) -> Servicio:
        if servicio.id is None:
            raise DatosInvalidosError("Servicio sin id.")
        servicio.validar()
        self.conn.execute(
            "UPDATE servicios SET nombre=?, categoria=?, precio=?, unidad=?, "
            "activo=?, notas=? WHERE id=?",
            (
                servicio.nombre.strip(),
                servicio.categoria,
                servicio.precio,
                servicio.unidad,
                1 if servicio.activo else 0,
                servicio.notas,
                servicio.id,
            ),
        )
        self.conn.commit()
        return servicio

    def eliminar(self, servicio_id: int) -> None:
        self.conn.execute("DELETE FROM servicios WHERE id = ?", (servicio_id,))
        self.conn.commit()

    def categorias(self) -> list[str]:
        filas = self.conn.execute(
            "SELECT DISTINCT categoria FROM servicios ORDER BY categoria"
        ).fetchall()
        return [r["categoria"] for r in filas]


class PlantillaRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _map(row: sqlite3.Row) -> PlantillaContrato:
        return PlantillaContrato(
            nombre=row["nombre"], contenido=row["contenido"] or "", id=row["id"]
        )

    def listar(self) -> list[PlantillaContrato]:
        filas = self.conn.execute(
            "SELECT * FROM plantillas_contrato ORDER BY nombre"
        ).fetchall()
        return [self._map(r) for r in filas]

    def obtener(self, plantilla_id: int) -> Optional[PlantillaContrato]:
        fila = self.conn.execute(
            "SELECT * FROM plantillas_contrato WHERE id = ?", (plantilla_id,)
        ).fetchone()
        return self._map(fila) if fila else None

    def crear(self, plantilla: PlantillaContrato) -> PlantillaContrato:
        if not plantilla.nombre.strip():
            raise DatosInvalidosError("La plantilla necesita un nombre.")
        cur = self.conn.execute(
            "INSERT INTO plantillas_contrato (nombre, contenido) VALUES (?, ?)",
            (plantilla.nombre.strip(), plantilla.contenido),
        )
        plantilla.id = cur.lastrowid
        self.conn.commit()
        return plantilla

    def actualizar(self, plantilla: PlantillaContrato) -> PlantillaContrato:
        if plantilla.id is None:
            raise DatosInvalidosError("Plantilla sin id.")
        self.conn.execute(
            "UPDATE plantillas_contrato SET nombre=?, contenido=? WHERE id=?",
            (plantilla.nombre.strip(), plantilla.contenido, plantilla.id),
        )
        self.conn.commit()
        return plantilla

    def eliminar(self, plantilla_id: int) -> None:
        self.conn.execute("DELETE FROM plantillas_contrato WHERE id = ?", (plantilla_id,))
        self.conn.commit()


class ContratoRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _map(row: sqlite3.Row) -> Contrato:
        return Contrato(
            nombre=row["nombre"],
            proyecto_id=row["proyecto_id"],
            plantilla_id=row["plantilla_id"],
            contenido=row["contenido"] or "",
            estado=row["estado"] or "Borrador",
            fecha=a_fecha(row["fecha"]),
            id=row["id"],
        )

    def listar(self) -> list[Contrato]:
        filas = self.conn.execute(
            "SELECT ct.*, p.titulo AS p_titulo, p.id AS p_id FROM contratos ct "
            "LEFT JOIN proyectos p ON p.id = ct.proyecto_id ORDER BY ct.fecha DESC, ct.id DESC"
        ).fetchall()
        contratos = []
        for fila in filas:
            contrato = self._map(fila)
            if fila["p_id"] is not None:
                contrato.proyecto = Proyecto(titulo=fila["p_titulo"] or "", id=fila["p_id"])
            contratos.append(contrato)
        return contratos

    def de_proyecto(self, proyecto_id: int) -> list[Contrato]:
        filas = self.conn.execute(
            "SELECT * FROM contratos WHERE proyecto_id = ? ORDER BY fecha DESC, id DESC",
            (proyecto_id,),
        ).fetchall()
        return [self._map(r) for r in filas]

    def crear(self, contrato: Contrato) -> Contrato:
        if not contrato.nombre.strip():
            raise DatosInvalidosError("El contrato necesita un nombre.")
        cur = self.conn.execute(
            "INSERT INTO contratos (nombre, proyecto_id, plantilla_id, contenido, estado, fecha) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                contrato.nombre.strip(),
                contrato.proyecto_id,
                contrato.plantilla_id,
                contrato.contenido,
                contrato.estado,
                _f(contrato.fecha) or a_texto(date.today()),
            ),
        )
        contrato.id = cur.lastrowid
        self.conn.commit()
        return contrato

    def actualizar(self, contrato: Contrato) -> Contrato:
        if contrato.id is None:
            raise DatosInvalidosError("Contrato sin id.")
        self.conn.execute(
            "UPDATE contratos SET nombre=?, proyecto_id=?, plantilla_id=?, contenido=?, "
            "estado=?, fecha=? WHERE id=?",
            (
                contrato.nombre.strip(),
                contrato.proyecto_id,
                contrato.plantilla_id,
                contrato.contenido,
                contrato.estado,
                _f(contrato.fecha),
                contrato.id,
            ),
        )
        self.conn.commit()
        return contrato

    def eliminar(self, contrato_id: int) -> None:
        self.conn.execute("DELETE FROM contratos WHERE id = ?", (contrato_id,))
        self.conn.commit()


# --------------------------------------------------------------------------- #
# Trabajos pendientes y calendario
# --------------------------------------------------------------------------- #


class TrabajoRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    _SQL = (
        "SELECT t.*, f.id AS f_id, f.nombre AS f_nombre, f.apellido AS f_apellido, "
        "p.id AS p_id, p.titulo AS p_titulo FROM trabajos_pendientes t "
        "JOIN fotografos f ON f.id = t.fotografo_id "
        "LEFT JOIN proyectos p ON p.id = t.proyecto_id "
    )

    def listar(
        self,
        fotografo_id: Optional[int] = None,
        estado: Optional[EstadoTrabajo] = None,
        proyecto_id: Optional[int] = None,
    ) -> list[TrabajoPendiente]:
        sql = self._SQL
        condiciones, params = [], []
        if fotografo_id is not None:
            condiciones.append("t.fotografo_id = ?")
            params.append(fotografo_id)
        if estado is not None:
            condiciones.append("t.estado = ?")
            params.append(str(estado))
        if proyecto_id is not None:
            condiciones.append("t.proyecto_id = ?")
            params.append(proyecto_id)
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY t.estado IN ('Pendiente', 'En edición') DESC, "
        sql += "COALESCE(t.fecha_entrega, '9999-12-31'), t.id"
        return [_map_trabajo(r) for r in self.conn.execute(sql, params).fetchall()]

    def obtener(self, trabajo_id: int) -> Optional[TrabajoPendiente]:
        fila = self.conn.execute(
            self._SQL + " WHERE t.id = ?", (trabajo_id,)
        ).fetchone()
        return _map_trabajo(fila) if fila else None

    def crear(self, trabajo: TrabajoPendiente) -> TrabajoPendiente:
        trabajo.validar()
        cur = self.conn.execute(
            "INSERT INTO trabajos_pendientes (titulo, descripcion, fotografo_id, "
            "proyecto_id, fecha_entrega, estado, rol) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                trabajo.titulo.strip(),
                trabajo.descripcion,
                trabajo.fotografo_id,
                trabajo.proyecto_id,
                _f(trabajo.fecha_entrega),
                str(trabajo.estado),
                trabajo.rol.strip(),
            ),
        )
        trabajo.id = cur.lastrowid
        self.conn.commit()
        return trabajo

    def actualizar(self, trabajo: TrabajoPendiente) -> TrabajoPendiente:
        if trabajo.id is None:
            raise DatosInvalidosError("Trabajo sin id.")
        trabajo.validar()
        self.conn.execute(
            "UPDATE trabajos_pendientes SET titulo=?, descripcion=?, fotografo_id=?, "
            "proyecto_id=?, fecha_entrega=?, estado=?, rol=? WHERE id=?",
            (
                trabajo.titulo.strip(),
                trabajo.descripcion,
                trabajo.fotografo_id,
                trabajo.proyecto_id,
                _f(trabajo.fecha_entrega),
                str(trabajo.estado),
                trabajo.rol.strip(),
                trabajo.id,
            ),
        )
        self.conn.commit()
        return trabajo

    def eliminar(self, trabajo_id: int) -> None:
        self.conn.execute("DELETE FROM trabajos_pendientes WHERE id = ?", (trabajo_id,))
        self.conn.commit()

    def cambiar_estado(self, trabajo_id: int, estado: EstadoTrabajo) -> None:
        self.conn.execute(
            "UPDATE trabajos_pendientes SET estado = ? WHERE id = ?",
            (str(EstadoTrabajo(estado)), trabajo_id),
        )
        self.conn.commit()

    def roles(self) -> list[str]:
        """Roles sugeridos: los de partida más los que ya se usaron."""
        usados = [r[0] for r in self.conn.execute(
            "SELECT DISTINCT rol FROM trabajos_pendientes WHERE rol <> '' ORDER BY rol")]
        return ROLES_TRABAJO + [r for r in usados if r not in ROLES_TRABAJO]


_EVENTOS_UNION = """
    SELECT * FROM (
        SELECT p.fecha_evento AS fecha, '' AS hora,
               p.titulo || ' — ' || c.nombre AS titulo,
               'Sesión' AS tipo, p.fotografo_id AS fotografo_id, p.id AS proyecto_id
          FROM proyectos p JOIN clientes c ON c.id = p.cliente_id
         WHERE p.fecha_evento IS NOT NULL
        UNION ALL
        SELECT t.fecha_entrega, '',
               t.titulo || ' — ' || f.nombre || ' ' || f.apellido,
               'Entrega', t.fotografo_id, t.proyecto_id
          FROM trabajos_pendientes t JOIN fotografos f ON f.id = t.fotografo_id
         WHERE t.fecha_entrega IS NOT NULL AND t.estado IN ('Pendiente', 'En edición')
        UNION ALL
        SELECT e.fecha_service_proximo, '',
               'Service: ' || e.marca || ' ' || e.modelo || ' (' || e.numero_serie || ')',
               'Service', e.fotografo_id, NULL
          FROM equipos e WHERE e.fecha_service_proximo IS NOT NULL
        UNION ALL
        SELECT ev.fecha, ev.hora, ev.titulo, ev.tipo, ev.fotografo_id, ev.proyecto_id
          FROM eventos ev
    )
"""


class EventoRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _map(row: sqlite3.Row) -> Evento:
        return Evento(
            titulo=row["titulo"],
            fecha=a_fecha(row["fecha"]) or date.today(),
            hora=row["hora"] or "",
            tipo=row["tipo"],
            fotografo_id=row["fotografo_id"],
            proyecto_id=row["proyecto_id"],
            notas=row["notas"] if "notas" in row.keys() else "",
            id=row["id"] if "id" in row.keys() and row["id"] is not None else None,
        )

    def listar(self, fotografo_id: Optional[int] = None) -> list[Evento]:
        sql = "SELECT * FROM eventos"
        params: tuple = ()
        if fotografo_id is not None:
            sql += " WHERE fotografo_id = ?"
            params = (fotografo_id,)
        sql += " ORDER BY fecha, hora"
        filas = self.conn.execute(sql, params).fetchall()
        return [
            Evento(
                titulo=r["titulo"],
                fecha=a_fecha(r["fecha"]) or date.today(),
                hora=r["hora"] or "",
                tipo=r["tipo"],
                fotografo_id=r["fotografo_id"],
                proyecto_id=r["proyecto_id"],
                notas=r["notas"] or "",
                id=r["id"],
            )
            for r in filas
        ]

    def crear(self, evento: Evento) -> Evento:
        evento.validar()
        cur = self.conn.execute(
            "INSERT INTO eventos (titulo, fecha, hora, tipo, fotografo_id, proyecto_id, notas) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                evento.titulo.strip(),
                a_texto(evento.fecha),
                evento.hora,
                evento.tipo,
                evento.fotografo_id,
                evento.proyecto_id,
                evento.notas,
            ),
        )
        evento.id = cur.lastrowid
        self.conn.commit()
        return evento

    def actualizar(self, evento: Evento) -> Evento:
        if evento.id is None:
            raise DatosInvalidosError("Evento sin id.")
        evento.validar()
        self.conn.execute(
            "UPDATE eventos SET titulo=?, fecha=?, hora=?, tipo=?, fotografo_id=?, "
            "proyecto_id=?, notas=? WHERE id=?",
            (
                evento.titulo.strip(),
                a_texto(evento.fecha),
                evento.hora,
                evento.tipo,
                evento.fotografo_id,
                evento.proyecto_id,
                evento.notas,
                evento.id,
            ),
        )
        self.conn.commit()
        return evento

    def eliminar(self, evento_id: int) -> None:
        self.conn.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
        self.conn.commit()

    def consolidado(
        self,
        inicio: date,
        fin: date,
        fotografo_id: Optional[int] = None,
    ) -> list[Evento]:
        """Eventos de clientes + entregas + service + agenda personal."""
        sql = "SELECT * FROM (" + _EVENTOS_UNION + ") WHERE fecha BETWEEN ? AND ?"
        params: list = [a_texto(inicio), a_texto(fin)]
        if fotografo_id is not None:
            sql += " AND (fotografo_id IS NULL OR fotografo_id = ?)"
            params.append(fotografo_id)
        sql += " ORDER BY fecha, hora, titulo"
        return [self._map(r) for r in self.conn.execute(sql, params).fetchall()]

    def del_dia(self, fecha: date, fotografo_id: Optional[int] = None) -> list[Evento]:
        return self.consolidado(fecha, fecha, fotografo_id=fotografo_id)


# --------------------------------------------------------------------------- #
# Acceso — usuarios, contraseñas y recuperación
# --------------------------------------------------------------------------- #

_CREDENCIALES_INCORRECTAS = "Usuario o contraseña incorrectos."


def _momento(valor: datetime) -> str:
    return valor.isoformat(sep=" ", timespec="seconds")


class UsuarioRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _map(row: sqlite3.Row) -> Usuario:
        return Usuario(
            usuario=row["usuario"],
            nombre=row["nombre"],
            email=row["email"],
            rol=RolUsuario(row["rol"]),
            activo=bool(row["activo"]),
            debe_cambiar_password=bool(row["debe_cambiar"]),
            ultimo_acceso=(datetime.fromisoformat(row["ultimo_acceso"])
                           if row["ultimo_acceso"] else None),
            id=row["id"],
            fotografo_id=row["fotografo_id"],
        )

    def _fila(self, usuario: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", ((usuario or "").strip(),)
        ).fetchone()

    # -- consultas --------------------------------------------------------- #
    def hay_usuarios(self) -> bool:
        return self.conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None

    def listar(self) -> list[Usuario]:
        filas = self.conn.execute("SELECT * FROM usuarios ORDER BY usuario").fetchall()
        return [self._map(r) for r in filas]

    def obtener(self, usuario_id: int) -> Optional[Usuario]:
        fila = self.conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return self._map(fila) if fila else None

    def por_nombre(self, usuario: str) -> Optional[Usuario]:
        fila = self._fila(usuario)
        return self._map(fila) if fila else None

    def nombre_disponible(self, base: str) -> str:
        """``base`` o ``base2``, ``base3``… hasta dar con un usuario libre."""
        candidato, n = base, 2
        while self._fila(candidato) is not None:
            candidato, n = f"{base}{n}", n + 1
        return candidato

    def crear_para_fotografo(self, fotografo: Fotografo, rol: RolUsuario) -> tuple[Usuario, str]:
        """Cuenta de acceso del fotógrafo: usuario derivado de su nombre y una
        contraseña provisoria que deberá cambiar al ingresar."""
        usuario = Usuario(
            usuario=self.nombre_disponible(auth.sugerir_usuario(
                fotografo.nombre, fotografo.apellido)),
            nombre=fotografo.nombre_completo,
            email=fotografo.email,
            rol=rol,
            debe_cambiar_password=True,
            fotografo_id=fotografo.id,
        )
        temporal = auth.generar_password_temporal()
        self.crear(usuario, temporal)
        return usuario, temporal

    # -- altas, bajas y cambios -------------------------------------------- #
    def crear(self, usuario: Usuario, password: str) -> str:
        """Crea la cuenta y devuelve su código de recuperación (se muestra una vez)."""
        usuario.validar()
        auth.validar_password(password)
        codigo = auth.generar_codigo_recuperacion()
        try:
            cur = self.conn.execute(
                "INSERT INTO usuarios (usuario, nombre, email, rol, password_hash, "
                "codigo_hash, activo, debe_cambiar, fotografo_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    usuario.usuario.strip(),
                    usuario.nombre.strip(),
                    usuario.email.strip(),
                    str(usuario.rol),
                    auth.hash_password(password),
                    auth.hash_password(auth.normalizar_codigo(codigo)),
                    1 if usuario.activo else 0,
                    1 if usuario.debe_cambiar_password else 0,
                    usuario.fotografo_id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DatosInvalidosError(
                f"Ya existe el usuario «{usuario.usuario.strip()}»."
            ) from exc
        usuario.id = cur.lastrowid
        self.conn.commit()
        return codigo

    def actualizar(self, usuario: Usuario) -> Usuario:
        """Nombre, email, rol y estado. El nombre de usuario no se cambia."""
        if usuario.id is None:
            raise DatosInvalidosError("Usuario sin id: no se puede actualizar.")
        if not (usuario.es_admin and usuario.activo):
            self._exigir_otro_admin(usuario.id)
        self.conn.execute(
            "UPDATE usuarios SET nombre=?, email=?, rol=?, activo=? WHERE id=?",
            (
                usuario.nombre.strip(),
                usuario.email.strip(),
                str(usuario.rol),
                1 if usuario.activo else 0,
                usuario.id,
            ),
        )
        self.conn.commit()
        return usuario

    def eliminar(self, usuario_id: int) -> None:
        self._exigir_otro_admin(usuario_id)
        self.conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        self.conn.commit()

    def _exigir_otro_admin(self, usuario_id: int) -> None:
        """Nunca se queda la base sin un administrador activo que pueda entrar."""
        otros = self.conn.execute(
            "SELECT COUNT(*) FROM usuarios WHERE rol = ? AND activo = 1 AND id <> ?",
            (str(RolUsuario.ADMINISTRADOR), usuario_id),
        ).fetchone()[0]
        if not otros:
            raise EliminacionRestringidaError(
                "Debe quedar al menos un administrador activo."
            )

    # -- ingreso ----------------------------------------------------------- #
    def autenticar(
        self, usuario: str, password: str, ahora: Optional[datetime] = None
    ) -> Usuario:
        ahora = ahora or datetime.now()
        fila = self._fila(usuario)
        if fila is None:
            raise CredencialesInvalidasError(_CREDENCIALES_INCORRECTAS)
        self._exigir_desbloqueo(fila, ahora)
        if not auth.verificar_password(password, fila["password_hash"]):
            self._registrar_fallo(fila, ahora)
            raise CredencialesInvalidasError(_CREDENCIALES_INCORRECTAS)
        if not fila["activo"]:
            raise CredencialesInvalidasError(
                "La cuenta está desactivada. Consulte a un administrador."
            )
        self.conn.execute(
            "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL, "
            "ultimo_acceso = ? WHERE id = ?",
            (_momento(ahora), fila["id"]),
        )
        self.conn.commit()
        return self.obtener(fila["id"])

    def _exigir_desbloqueo(self, fila: sqlite3.Row, ahora: datetime) -> None:
        if not fila["bloqueado_hasta"]:
            return
        hasta = datetime.fromisoformat(fila["bloqueado_hasta"])
        if hasta > ahora:
            minutos = max(1, -(-int((hasta - ahora).total_seconds()) // 60))
            raise CuentaBloqueadaError(
                "Cuenta bloqueada por intentos fallidos. "
                f"Vuelva a intentar en {minutos} minuto(s)."
            )

    def _registrar_fallo(self, fila: sqlite3.Row, ahora: datetime) -> None:
        intentos = fila["intentos_fallidos"] + 1
        if intentos >= auth.MAX_INTENTOS:
            hasta = ahora + timedelta(minutes=auth.MINUTOS_BLOQUEO)
            self.conn.execute(
                "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = ? "
                "WHERE id = ?",
                (_momento(hasta), fila["id"]),
            )
        else:
            self.conn.execute(
                "UPDATE usuarios SET intentos_fallidos = ? WHERE id = ?",
                (intentos, fila["id"]),
            )
        self.conn.commit()

    # -- contraseñas ------------------------------------------------------- #
    def _guardar_password(self, usuario_id: int, password: str, *,
                          debe_cambiar: bool = False) -> None:
        self.conn.execute(
            "UPDATE usuarios SET password_hash = ?, debe_cambiar = ?, "
            "intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
            (auth.hash_password(password), 1 if debe_cambiar else 0, usuario_id),
        )

    def cambiar_password(self, usuario_id: int, actual: str, nueva: str) -> None:
        fila = self.conn.execute(
            "SELECT password_hash FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        if fila is None or not auth.verificar_password(actual, fila["password_hash"]):
            raise CredencialesInvalidasError("La contraseña actual no es correcta.")
        self.definir_password(usuario_id, nueva)

    def definir_password(self, usuario_id: int, nueva: str) -> None:
        """Fija la contraseña de una sesión ya autenticada (cambio obligatorio)."""
        auth.validar_password(nueva)
        self._guardar_password(usuario_id, nueva)
        self.conn.commit()

    def restablecer_con_codigo(
        self, usuario: str, codigo: str, nueva: str, ahora: Optional[datetime] = None
    ) -> str:
        """Recuperación sin sesión: consume el código y devuelve uno nuevo."""
        ahora = ahora or datetime.now()
        incorrecto = "Usuario o código de recuperación incorrectos."
        fila = self._fila(usuario)
        if fila is None:
            raise CredencialesInvalidasError(incorrecto)
        self._exigir_desbloqueo(fila, ahora)
        if not auth.verificar_password(auth.normalizar_codigo(codigo), fila["codigo_hash"]):
            self._registrar_fallo(fila, ahora)
            raise CredencialesInvalidasError(incorrecto)
        auth.validar_password(nueva)
        self._guardar_password(fila["id"], nueva)
        return self._nuevo_codigo(fila["id"])

    def restablecer_por_admin(self, usuario_id: int) -> str:
        """Devuelve una contraseña provisoria; el usuario la cambia al ingresar."""
        temporal = auth.generar_password_temporal()
        self._guardar_password(usuario_id, temporal, debe_cambiar=True)
        self.conn.commit()
        return temporal

    def regenerar_codigo(self, usuario_id: int, password: str) -> str:
        fila = self.conn.execute(
            "SELECT password_hash FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        if fila is None or not auth.verificar_password(password, fila["password_hash"]):
            raise CredencialesInvalidasError("La contraseña no es correcta.")
        return self._nuevo_codigo(usuario_id)

    def _nuevo_codigo(self, usuario_id: int) -> str:
        codigo = auth.generar_codigo_recuperacion()
        self.conn.execute(
            "UPDATE usuarios SET codigo_hash = ? WHERE id = ?",
            (auth.hash_password(auth.normalizar_codigo(codigo)), usuario_id),
        )
        self.conn.commit()
        return codigo


# --------------------------------------------------------------------------- #
# Egresos y resumen general (sólo administradores)
# --------------------------------------------------------------------------- #


class EgresoRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def crear(self, egreso: Egreso) -> Egreso:
        egreso.validar()
        cur = self.conn.execute(
            "INSERT INTO egresos (fecha, concepto, categoria, monto, proyecto_id, notas) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (a_texto(egreso.fecha), egreso.concepto.strip(),
             egreso.categoria.strip() or "Otros", float(egreso.monto),
             egreso.proyecto_id, egreso.notas),
        )
        egreso.id = cur.lastrowid
        self.conn.commit()
        return egreso

    def eliminar(self, egreso_id: int) -> None:
        self.conn.execute("DELETE FROM egresos WHERE id = ?", (egreso_id,))
        self.conn.commit()

    def categorias(self) -> list[str]:
        usadas = [r[0] for r in self.conn.execute(
            "SELECT DISTINCT categoria FROM egresos ORDER BY categoria")]
        return CATEGORIAS_EGRESO + [c for c in usadas if c not in CATEGORIAS_EGRESO]


class InformeRepo:
    """Consultas agregadas del resumen general. Todas reciben un período
    ``[desde, hasta]``; ``None`` deja ese extremo abierto."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def _rango(desde: Fecha, hasta: Fecha) -> tuple[str, str]:
        return (_f(desde) or "0000-01-01", _f(hasta) or "9999-12-31")

    def _filas(self, sql: str, params: Sequence) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql, list(params)).fetchall()]

    # -- dinero ------------------------------------------------------------ #
    def movimientos(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        """Señas y pagos (ingresos) y egresos, del más reciente al más antiguo."""
        r = self._rango(desde, hasta)
        return self._filas(
            """
            SELECT * FROM (
                SELECT p.sena_fecha AS fecha, 'Ingreso' AS clase, 'Seña' AS concepto,
                       p.titulo AS proyecto, c.nombre AS cliente, p.tipo AS categoria,
                       p.sena_medio AS medio, p.sena_monto AS monto, NULL AS egreso_id
                  FROM proyectos p JOIN clientes c ON c.id = p.cliente_id
                 WHERE p.sena_monto > 0 AND p.sena_fecha IS NOT NULL
                UNION ALL
                SELECT g.fecha, 'Ingreso', COALESCE(NULLIF(g.notas, ''), 'Pago'),
                       p.titulo, c.nombre, p.tipo, g.medio, g.monto, NULL
                  FROM pagos g JOIN proyectos p ON p.id = g.proyecto_id
                  JOIN clientes c ON c.id = p.cliente_id
                UNION ALL
                SELECT e.fecha, 'Egreso', e.concepto, COALESCE(p.titulo, ''), '',
                       e.categoria, '', e.monto, e.id
                  FROM egresos e LEFT JOIN proyectos p ON p.id = e.proyecto_id
            ) WHERE fecha BETWEEN ? AND ? ORDER BY fecha DESC, clase
            """, r)

    def saldo_por_cobrar(self) -> float:
        fila = self.conn.execute(
            "SELECT COALESCE(SUM(MAX(p.cobro_total - p.sena_monto - COALESCE(("
            "SELECT SUM(monto) FROM pagos g WHERE g.proyecto_id = p.id), 0), 0)), 0) "
            "FROM proyectos p"
        ).fetchone()
        return float(fila[0])

    # -- equipos ----------------------------------------------------------- #
    def salidas_por_equipo(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        return self._filas(
            "SELECT e.marca || ' ' || e.modelo AS equipo, "
            "COALESCE(e.numero_serie, '') AS numero_serie, e.estado, "
            "COUNT(h.id) AS salidas, MAX(h.fecha_asignacion) AS ultima "
            "FROM equipos e LEFT JOIN historial_asignaciones h ON h.equipo_id = e.id "
            "AND h.fecha_asignacion BETWEEN ? AND ? "
            "GROUP BY e.id ORDER BY salidas DESC, equipo", self._rango(desde, hasta))

    # -- personal ---------------------------------------------------------- #
    # Un trabajo cuenta en la fecha del evento de su proyecto o, si no tiene
    # proyecto, en su fecha de entrega. Los cancelados no cuentan.
    _TRABAJOS = (
        "FROM trabajos_pendientes t LEFT JOIN proyectos p ON p.id = t.proyecto_id "
        "WHERE t.estado <> 'Cancelado' "
        "AND COALESCE(p.fecha_evento, t.fecha_entrega, '0000-01-01') BETWEEN ? AND ? "
    )

    def eventos_por_fotografo(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        r = self._rango(desde, hasta)
        return self._filas(
            "SELECT f.nombre || ' ' || f.apellido AS fotografo, "
            " (SELECT COUNT(*) FROM proyectos p WHERE p.fotografo_id = f.id "
            "   AND COALESCE(p.fecha_evento, '0000-01-01') BETWEEN ? AND ?) AS proyectos, "
            " (SELECT COUNT(*) " + self._TRABAJOS + " AND t.fotografo_id = f.id) AS trabajos, "
            " (SELECT COUNT(DISTINCT t.proyecto_id) " + self._TRABAJOS
            + " AND t.fotografo_id = f.id) AS eventos "
            "FROM fotografos f ORDER BY trabajos + proyectos DESC, fotografo",
            r + r + r)

    def roles_cubiertos(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        return self._filas(
            "SELECT COALESCE(NULLIF(t.rol, ''), 'Sin rol') AS rol, COUNT(*) AS veces, "
            "COUNT(DISTINCT t.proyecto_id) AS eventos " + self._TRABAJOS
            + "GROUP BY 1 ORDER BY veces DESC, rol", self._rango(desde, hasta))

    # -- clientes, proyectos y contratos ----------------------------------- #
    def movimientos_por_cliente(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        return self._filas(
            "SELECT c.nombre AS cliente, COUNT(p.id) AS proyectos, "
            "COALESCE(SUM(p.cobro_total), 0) AS contratado, "
            "COALESCE(SUM(p.sena_monto + COALESCE((SELECT SUM(monto) FROM pagos g "
            "  WHERE g.proyecto_id = p.id), 0)), 0) AS cobrado "
            "FROM clientes c JOIN proyectos p ON p.cliente_id = c.id "
            "WHERE COALESCE(p.fecha_evento, substr(p.creado_en, 1, 10)) BETWEEN ? AND ? "
            "GROUP BY c.id ORDER BY contratado DESC, cliente", self._rango(desde, hasta))

    def proyectos_por_tipo(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        return self._filas(
            "SELECT COALESCE(NULLIF(p.tipo, ''), 'Sin tipo') AS tipo, COUNT(*) AS proyectos, "
            "COALESCE(SUM(p.cobro_total), 0) AS contratado FROM proyectos p "
            "WHERE COALESCE(p.fecha_evento, substr(p.creado_en, 1, 10)) BETWEEN ? AND ? "
            "GROUP BY 1 ORDER BY proyectos DESC, tipo", self._rango(desde, hasta))

    def proyectos_por_estado(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        return self._filas(
            "SELECT p.estado, COUNT(*) AS proyectos FROM proyectos p "
            "WHERE COALESCE(p.fecha_evento, substr(p.creado_en, 1, 10)) BETWEEN ? AND ? "
            "GROUP BY 1 ORDER BY proyectos DESC", self._rango(desde, hasta))

    def contratos_por_estado(self, desde: Fecha = None, hasta: Fecha = None) -> list[dict]:
        return self._filas(
            "SELECT estado, COUNT(*) AS contratos FROM contratos "
            "WHERE COALESCE(fecha, '0000-01-01') BETWEEN ? AND ? "
            "GROUP BY 1 ORDER BY contratos DESC", self._rango(desde, hasta))


# --------------------------------------------------------------------------- #
# Agrupador de repositorios + utilidades de la app
# --------------------------------------------------------------------------- #


class Repositorios:
    """Fachada única que entrega la app a todas las vistas."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.fotografos = FotografoRepo(conn)
        self.equipos = EquipoRepo(conn)
        self.clientes = ClienteRepo(conn)
        self.proyectos = ProyectoRepo(conn)
        self.servicios = ServicioRepo(conn)
        self.plantillas = PlantillaRepo(conn)
        self.contratos = ContratoRepo(conn)
        self.trabajos = TrabajoRepo(conn)
        self.eventos = EventoRepo(conn)
        self.usuarios = UsuarioRepo(conn)
        self.egresos = EgresoRepo(conn)
        self.informes = InformeRepo(conn)

    # -- configuración ----------------------------------------------------- #
    def config(self, clave: str, defecto: str = "") -> str:
        fila = self.conn.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave,)
        ).fetchone()
        return fila["valor"] if fila else defecto

    def set_config(self, clave: str, valor: str) -> None:
        self.conn.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, valor),
        )
        self.conn.commit()

    @property
    def nombre_estudio(self) -> str:
        return self.config("estudio", "Estudio Fotia")

    # -- estadísticas para el panel de control ----------------------------- #
    def resumen(self) -> dict[str, int]:
        def contar(sql: str) -> int:
            return int(self.conn.execute(sql).fetchone()[0])

        equipos = self.listar_estados_equipos()
        return {
            "equipos": contar("SELECT COUNT(*) FROM equipos"),
            "en_uso": equipos.get("En uso", 0),
            "en_stock": equipos.get("En stock", 0),
            "fotografos": contar("SELECT COUNT(*) FROM fotografos WHERE activo = 1"),
            "clientes": contar("SELECT COUNT(*) FROM clientes"),
            "proyectos": contar("SELECT COUNT(*) FROM proyectos"),
            "trabajos_abiertos": contar(
                "SELECT COUNT(*) FROM trabajos_pendientes "
                "WHERE estado IN ('Pendiente', 'En edición')"
            ),
            "eventos": contar("SELECT COUNT(*) FROM eventos"),
            "servicios": contar("SELECT COUNT(*) FROM servicios"),
            "contratos": contar("SELECT COUNT(*) FROM contratos"),
        }

    def listar_estados_equipos(self) -> dict[str, int]:
        filas = self.conn.execute(
            "SELECT estado, COUNT(*) AS total FROM equipos GROUP BY estado"
        ).fetchall()
        return {r["estado"]: r["total"] for r in filas}

    def esta_vacio(self) -> bool:
        fila = self.conn.execute("SELECT COUNT(*) FROM equipos").fetchone()[0]
        return int(fila) == 0
