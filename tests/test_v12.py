"""Fotique 1.2: serie opcional, tope de pagos, roles, egresos, informes y migración."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from fotique.db import BaseDatos
from fotique.db.connection import VERSION_ESQUEMA
from fotique.domain import auth
from fotique.domain.errors import DatosInvalidosError
from fotique.domain.models import (
    ROLES_TRABAJO,
    TIPOS_PROYECTO,
    Cliente,
    Egreso,
    Equipo,
    EstadoTrabajo,
    Fotografo,
    Proyecto,
    RolUsuario,
    TrabajoPendiente,
)

ESQUEMA_V1 = Path(__file__).parent / "datos" / "schema_v1.sql"


@pytest.fixture()
def estudio(repos):
    """Un fotógrafo, un cliente y un proyecto de 1.000 con seña de 200."""
    fotografo = repos.fotografos.crear(Fotografo(nombre="Tomás", apellido="Benítez"))
    cliente = repos.clientes.crear(Cliente(nombre="María López"))
    proyecto = repos.proyectos.crear(Proyecto(
        titulo="Boda López", cliente_id=cliente.id, cobro_total=1000, sena=200,
        sena_fecha=date(2026, 3, 1), fecha_evento=date(2026, 5, 10), tipo="Boda",
        fotografo_id=fotografo.id))
    return fotografo, cliente, proyecto


# -- equipos ----------------------------------------------------------------- #


def test_numero_de_serie_opcional_y_repetible_vacio(repos):
    a = repos.equipos.crear(Equipo(marca="Godox", modelo="V1"))
    b = repos.equipos.crear(Equipo(numero_serie="  ", marca="Godox", modelo="V1"))
    assert a.id != b.id
    assert [e.numero_serie for e in repos.equipos.listar()] == ["", ""]
    assert a.nombre == "Godox V1"
    repos.equipos.crear(Equipo(numero_serie="X1", marca="Sony", modelo="A7"))
    with pytest.raises(DatosInvalidosError):  # la serie, si se carga, sigue siendo única
        repos.equipos.crear(Equipo(numero_serie="X1", marca="Sony", modelo="A7"))


def test_asignar_con_proyecto_retiro_y_entrega(repos, estudio):
    fotografo, _cliente, proyecto = estudio
    equipo = repos.equipos.crear(Equipo(marca="Sony", modelo="A7 IV"))
    with pytest.raises(DatosInvalidosError):
        repos.equipos.asignar(equipo.id, fotografo.id, date(2026, 5, 9),
                              fecha_prevista=date(2026, 5, 8))
    repos.equipos.asignar(equipo.id, fotografo.id, date(2026, 5, 9),
                          proyecto_id=proyecto.id, fecha_prevista=date(2026, 5, 11))
    movimiento = repos.equipos.historial(equipo_id=equipo.id)[0]
    assert movimiento["p_titulo"] == "Boda López"
    assert movimiento["fecha_asignacion"] == "2026-05-09"
    assert movimiento["fecha_prevista"] == "2026-05-11"
    assert movimiento["fecha_devolucion"] is None


# -- cobros ------------------------------------------------------------------ #


def test_los_pagos_no_superan_el_cobro_total(repos, estudio):
    _f, _c, proyecto = estudio
    repos.proyectos.crear_pago(proyecto.id, 500, date(2026, 4, 1))
    with pytest.raises(DatosInvalidosError):  # 200 + 500 + 301 > 1000
        repos.proyectos.crear_pago(proyecto.id, 301, date(2026, 4, 2))
    repos.proyectos.crear_pago(proyecto.id, 300, date(2026, 4, 2))  # justo el saldo
    assert repos.proyectos.obtener(proyecto.id).obtener_saldo_pendiente() == 0
    with pytest.raises(DatosInvalidosError):
        repos.proyectos.crear_pago(proyecto.id, 0.01, date(2026, 4, 3))


def test_el_cobro_total_no_baja_de_lo_abonado(repos, estudio):
    _f, _c, proyecto = estudio
    repos.proyectos.crear_pago(proyecto.id, 500, date(2026, 4, 1))
    proyecto.cobro_total = 600
    with pytest.raises(DatosInvalidosError):
        repos.proyectos.actualizar(proyecto)


# -- roles, tipos y entregas ------------------------------------------------- #


def test_roles_y_tipos_sugeridos_incluyen_los_nuevos(repos, estudio):
    fotografo, _c, proyecto = estudio
    assert repos.trabajos.roles() == ROLES_TRABAJO
    repos.trabajos.crear(TrabajoPendiente(titulo="Dron", fotografo_id=fotografo.id,
                                          proyecto_id=proyecto.id, rol="Piloto de dron"))
    assert repos.trabajos.roles() == ROLES_TRABAJO + ["Piloto de dron"]
    assert repos.trabajos.listar()[0].rol == "Piloto de dron"

    proyecto.tipo = "Bautismo"
    repos.proyectos.actualizar(proyecto)
    assert repos.proyectos.tipos() == TIPOS_PROYECTO + ["Bautismo"]


def test_entrega_cancelada_no_cuenta_como_activa(repos, estudio):
    fotografo, _c, _p = estudio
    trabajo = repos.trabajos.crear(
        TrabajoPendiente(titulo="Álbum", fotografo_id=fotografo.id))
    assert repos.fotografos.listar_resumen()[0]["n_activos"] == 1
    repos.trabajos.cambiar_estado(trabajo.id, EstadoTrabajo.CANCELADO)
    assert repos.trabajos.obtener(trabajo.id).estado == EstadoTrabajo.CANCELADO
    assert repos.fotografos.listar_resumen()[0]["n_activos"] == 0
    assert repos.fotografos.detalle(fotografo.id).entregas_activas == []


# -- cuenta del fotógrafo ---------------------------------------------------- #


def test_alta_de_fotografo_con_cuenta_y_rol(repos, estudio, monkeypatch):
    monkeypatch.setattr(auth, "ITERACIONES", 1_000)
    fotografo, _c, _p = estudio
    usuario, temporal = repos.usuarios.crear_para_fotografo(
        fotografo, RolUsuario.ADMINISTRADOR)
    assert usuario.usuario == "tomas.benitez"
    assert usuario.fotografo_id == fotografo.id
    ingresado = repos.usuarios.autenticar("tomas.benitez", temporal)
    assert ingresado.es_admin and ingresado.debe_cambiar_password
    assert repos.fotografos.listar_resumen()[0]["rol"] == "Administrador"

    homonimo = repos.fotografos.crear(Fotografo(nombre="Tomas", apellido="Benitez"))
    otro, _ = repos.usuarios.crear_para_fotografo(homonimo, RolUsuario.USUARIO)
    assert otro.usuario == "tomas.benitez2"


# -- egresos e informes ------------------------------------------------------ #


def test_movimientos_de_dinero_por_periodo(repos, estudio):
    _f, _c, proyecto = estudio
    repos.proyectos.crear_pago(proyecto.id, 300, date(2026, 4, 1), "Transferencia", "Cuota 2")
    repos.egresos.crear(Egreso(concepto="Alquiler de luces", monto=120,
                               fecha=date(2026, 4, 5), categoria="Alquileres",
                               proyecto_id=proyecto.id))
    with pytest.raises(DatosInvalidosError):
        repos.egresos.crear(Egreso(concepto="", monto=10, fecha=date(2026, 4, 5)))

    todos = repos.informes.movimientos()
    assert [(m["clase"], m["monto"]) for m in todos] == [
        ("Egreso", 120), ("Ingreso", 300), ("Ingreso", 200)]
    abril = repos.informes.movimientos(date(2026, 4, 1), date(2026, 4, 30))
    assert [m["concepto"] for m in abril] == ["Alquiler de luces", "Cuota 2"]
    assert abril[1]["categoria"] == "Boda"
    assert repos.informes.saldo_por_cobrar() == 500

    repos.egresos.eliminar(todos[0]["egreso_id"])
    assert len(repos.informes.movimientos()) == 2


def test_resumen_de_equipos_personal_y_roles(repos, estudio):
    fotografo, _c, proyecto = estudio
    otro = repos.fotografos.crear(Fotografo(nombre="Marina"))
    equipo = repos.equipos.crear(Equipo(marca="Sony", modelo="A7 IV"))
    sin_uso = repos.equipos.crear(Equipo(marca="Godox", modelo="V1"))
    for dia in (1, 8):
        repos.equipos.asignar(equipo.id, fotografo.id, date(2026, 5, dia))
        repos.equipos.devolver(equipo.id, date(2026, 5, dia + 1))

    for quien, rol in ((fotografo, "Fotógrafo"), (otro, "Fotógrafo"), (otro, "Iluminador")):
        repos.trabajos.crear(TrabajoPendiente(
            titulo=rol, fotografo_id=quien.id, proyecto_id=proyecto.id, rol=rol))
    cancelado = repos.trabajos.crear(TrabajoPendiente(
        titulo="x", fotografo_id=otro.id, proyecto_id=proyecto.id, rol="Asistente"))
    repos.trabajos.cambiar_estado(cancelado.id, EstadoTrabajo.CANCELADO)

    salidas = {f["equipo"]: f["salidas"] for f in repos.informes.salidas_por_equipo()}
    assert salidas == {"Sony A7 IV": 2, "Godox V1": 0}
    assert sin_uso.id is not None

    # dos personas cubrieron «Fotógrafo» en un mismo evento: 2 veces, 1 evento
    roles = {r["rol"]: (r["veces"], r["eventos"])
             for r in repos.informes.roles_cubiertos()}
    assert roles == {"Fotógrafo": (2, 1), "Iluminador": (1, 1)}

    por_fotografo = {f["fotografo"].strip(): f for f in repos.informes.eventos_por_fotografo()}
    assert por_fotografo["Tomás Benítez"]["proyectos"] == 1
    assert por_fotografo["Marina"]["trabajos"] == 2
    assert por_fotografo["Marina"]["eventos"] == 1

    fuera = repos.informes.roles_cubiertos(date(2027, 1, 1), date(2027, 12, 31))
    assert fuera == []


def test_resumen_de_clientes_y_tipos(repos, estudio):
    _f, cliente, proyecto = estudio
    repos.proyectos.crear_pago(proyecto.id, 300, date(2026, 4, 1))
    fila = repos.informes.movimientos_por_cliente()[0]
    assert (fila["cliente"], fila["proyectos"], fila["contratado"], fila["cobrado"]) == (
        cliente.nombre, 1, 1000, 500)
    assert repos.informes.proyectos_por_tipo()[0]["tipo"] == "Boda"
    assert repos.informes.proyectos_por_estado()[0]["proyectos"] == 1


# -- migración --------------------------------------------------------------- #


def test_migra_una_base_de_la_version_anterior(tmp_path):
    ruta = tmp_path / "vieja.db"
    vieja = sqlite3.connect(ruta)
    vieja.executescript(ESQUEMA_V1.read_text(encoding="utf-8"))
    vieja.executescript("""
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
            nombre TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
            rol TEXT NOT NULL DEFAULT 'Operador'
                CHECK (rol IN ('Administrador', 'Operador')),
            password_hash TEXT NOT NULL, codigo_hash TEXT NOT NULL DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1, debe_cambiar INTEGER NOT NULL DEFAULT 0,
            intentos_fallidos INTEGER NOT NULL DEFAULT 0, bloqueado_hasta TEXT,
            ultimo_acceso TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
        INSERT INTO usuarios (usuario, rol, password_hash) VALUES
            ('jorge', 'Administrador', 'h1'), ('marina', 'Operador', 'h2');
        INSERT INTO fotografos (nombre) VALUES ('Jorge');
        INSERT INTO equipos (numero_serie, marca, modelo, estado, fotografo_id)
            VALUES ('SN1', 'Sony', 'A7', 'En uso', 1), ('SN2', 'Godox', 'V1', 'En stock', NULL);
        INSERT INTO historial_asignaciones (equipo_id, fotografo_id, fecha_asignacion)
            VALUES (1, 1, '2026-09-01');
        INSERT INTO clientes (nombre) VALUES ('María');
        INSERT INTO proyectos (titulo, cliente_id, cobro_total) VALUES ('Boda', 1, 1000);
        INSERT INTO trabajos_pendientes (titulo, fotografo_id, proyecto_id, estado)
            VALUES ('Álbum', 1, 1, 'En edición');
    """)
    vieja.commit()
    vieja.close()

    base = BaseDatos(ruta)
    try:
        conn = base.conn
        assert conn.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (tmp_path / "vieja.db.antes-de-v2").exists()

        assert [(u.usuario, str(u.rol)) for u in base.repos.usuarios.listar()] == [
            ("jorge", "Administrador"), ("marina", "Usuario")]
        equipos = base.repos.equipos.listar()
        assert {e.numero_serie for e in equipos} == {"SN1", "SN2"}
        assert next(e for e in equipos if e.numero_serie == "SN1").fotografo_actual.nombre == "Jorge"
        assert base.repos.equipos.historial()[0]["fecha_prevista"] is None
        trabajo = base.repos.trabajos.listar()[0]
        assert (trabajo.titulo, trabajo.estado, trabajo.rol) == (
            "Álbum", EstadoTrabajo.EN_EDICION, "")
        assert base.repos.proyectos.listar()[0].tipo == ""

        # lo que la versión anterior rechazaba ahora se puede guardar
        base.repos.equipos.crear(Equipo(marca="Sony", modelo="FX3"))
        base.repos.trabajos.cambiar_estado(trabajo.id, EstadoTrabajo.CANCELADO)
        # y las claves foráneas siguen apuntando a las tablas reconstruidas
        base.repos.equipos.devolver(equipos[0].id if equipos[0].numero_serie == "SN1"
                                    else equipos[1].id)
        assert base.repos.equipos.historial()[0]["fecha_devolucion"] is not None
    finally:
        base.cerrar()

    base = BaseDatos(ruta)  # abrirla de nuevo no vuelve a migrar ni pierde datos
    try:
        assert len(base.repos.equipos.listar()) == 3
    finally:
        base.cerrar()


# -- categorías del tarifario ------------------------------------------------ #


def test_categorias_del_tarifario_se_agregan_y_quitan(repos):
    from fotique.domain.errors import EliminacionRestringidaError
    from fotique.domain.models import Servicio

    servicios = repos.servicios
    assert servicios.categorias() == []
    servicios.crear_categoria("Drone")
    with pytest.raises(DatosInvalidosError):
        servicios.crear_categoria("drone")      # ya existe (sin distinguir mayúsculas)
    with pytest.raises(DatosInvalidosError):
        servicios.crear_categoria("   ")

    servicios.crear(Servicio(nombre="Cobertura boda", categoria="Coberturas", precio=10))
    assert servicios.categorias_con_uso() == [("Coberturas", 1), ("Drone", 0)]

    with pytest.raises(EliminacionRestringidaError):
        servicios.eliminar_categoria("Coberturas")  # la usa un servicio
    servicios.eliminar_categoria("Drone")
    assert servicios.categorias() == ["Coberturas"]
