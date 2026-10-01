"""Caso TDD 1 y 2 del SRS: asignación de equipos."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from fotia.domain import (
    AsignacionInvalidaError,
    DatosInvalidosError,
    Equipo,
    EquipoNoDisponibleException,
    EstadoEquipo,
    EstadoService,
    EstadoTrabajo,
    Fotografo,
    EstadoInvalidoError,
)
from fotia.domain.services import equipos_en_alerta


def test_asignar_equipo_a_fotografo_exitoso():
    equipo = Equipo(
        numero_serie="SN123456",
        marca="Sony",
        modelo="A7 IV",
        estado="En stock",
    )
    fotografo = Fotografo(nombre="Jorge", apellido="Paquez")

    equipo.asignar_a_fotografo(fotografo)

    assert equipo.estado == EstadoEquipo.EN_USO
    assert equipo.fotografo_actual == fotografo
    assert equipo in fotografo.equipos_tomados


def test_asignar_equipo_ya_en_uso_lanza_excepcion():
    equipo = Equipo(
        numero_serie="SN123456",
        marca="Sony",
        modelo="A7 IV",
        estado="En uso",
        fotografo_actual=Fotografo(nombre="Juan"),
    )
    otro_fotografo = Fotografo(nombre="Pedro")

    with pytest.raises(EquipoNoDisponibleException):
        equipo.asignar_a_fotografo(otro_fotografo)


def test_equipo_en_uso_sin_fotografo_es_invalido():
    with pytest.raises(AsignacionInvalidaError):
        Equipo(numero_serie="SN1", marca="Canon", modelo="R6", estado="En uso")


def test_asignar_sin_fotografo_lanza_excepcion():
    equipo = Equipo(numero_serie="SN2", marca="Canon", modelo="R6")
    with pytest.raises(AsignacionInvalidaError):
        equipo.asignar_a_fotografo(None)


def test_devolver_equipo_al_stock():
    fotografo = Fotografo(nombre="Marina")
    equipo = Equipo(numero_serie="SN3", marca="Nikon", modelo="Z6")
    equipo.asignar_a_fotografo(fotografo)

    equipo.devolver()

    assert equipo.estado == EstadoEquipo.EN_STOCK
    assert equipo.fotografo_actual is None
    assert equipo not in fotografo.equipos_tomados


def test_devolver_equipo_ya_en_stock_lanza_excepcion():
    equipo = Equipo(numero_serie="SN4", marca="Nikon", modelo="Z6")
    with pytest.raises(EstadoInvalidoError):
        equipo.devolver()


def test_numero_serie_obligatorio():
    with pytest.raises(DatosInvalidosError):
        Equipo(numero_serie="  ", marca="Sony", modelo="A7")


def test_alertas_de_service_vencido_y_proximo():
    hoy = date(2026, 9, 30)
    vencido = Equipo(
        numero_serie="A", marca="Sony", modelo="A7 IV",
        fecha_service_proximo=hoy - timedelta(days=10),
    )
    proximo = Equipo(
        numero_serie="B", marca="Sony", modelo="A7 IV",
        fecha_service_proximo=hoy + timedelta(days=15),
    )
    en_regra = Equipo(
        numero_serie="C", marca="Sony", modelo="A7 IV",
        fecha_service_proximo=hoy + timedelta(days=200),
    )
    sin_fecha = Equipo(numero_serie="D", marca="Godox", modelo="V1")

    alertas = dict(
        (e.numero_serie, estado)
        for e, estado in equipos_en_alerta(
            [vencido, proximo, en_regra, sin_fecha], hoy=hoy, dias_aviso=30
        )
    )

    assert alertas == {"A": EstadoService.VENCIDO, "B": EstadoService.PROXIMO}
    assert vencido.estado_service(hoy=hoy) == EstadoService.VENCIDO
    assert sin_fecha.estado_service(hoy=hoy) == EstadoService.SIN_FECHA


def test_trabajos_activos_del_fotografo():
    fotografo = Fotografo(nombre="Tomás")
    fotografo.trabajos = []
    from fotia.domain.models import TrabajoPendiente

    fotografo.trabajos = [
        TrabajoPendiente(titulo="Edición", fotografo_id=1),
        TrabajoPendiente(titulo="Álbum", fotografo_id=1, estado=EstadoTrabajo.ENTREGADO),
    ]

    assert len(fotografo.entregas_activas) == 1
