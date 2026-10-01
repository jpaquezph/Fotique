"""Caso TDD 3 del SRS: cálculo de saldo y reglas comerciales."""

from __future__ import annotations

import pytest

from fotia.domain import DatosInvalidosError, EliminacionRestringidaError, Fotografo
from fotia.domain.models import Cliente, EstadoTrabajo, Pago, Proyecto, TrabajoPendiente
from fotia.domain.services import (
    generar_texto_contrato,
    proyectos_con_saldo,
    resumen_financiero,
    validar_eliminacion_fotografo,
)
from fotia.util import a_fecha, fecha_legible, moneda
from datetime import date


def test_calculo_saldo_pendiente_proyecto():
    proyecto = Proyecto(cliente="Maria Lopez", cobro_total=150000.0, sena=50000.0)

    assert proyecto.obtener_saldo_pendiente() == 100000.0


def test_saldo_descuenta_pagos_parciales():
    proyecto = Proyecto(
        cliente="Ana Rivas",
        cobro_total=680_000.0,
        sena=200_000.0,
        pagos=[Pago(monto=180_000.0, fecha=date(2026, 9, 1))],
    )

    assert proyecto.total_pagado == 380_000.0
    assert proyecto.saldo == 300_000.0
    assert resumen_financiero(proyecto)["saldo"] == 300_000.0


def test_proyectos_con_saldo_pendiente():
    al_dia = Proyecto(cliente="A", cobro_total=100_000, sena=100_000)
    pendiente = Proyecto(cliente="B", cobro_total=100_000, sena=40_000)

    assert proyectos_con_saldo([al_dia, pendiente]) == [pendiente]


def test_proyecto_sin_cobro_total_no_da_saldo_negativo():
    proyecto = Proyecto(cliente="Sin precio")

    assert proyecto.obtener_saldo_pendiente() == 0.0


def test_validaciones_de_proyecto():
    with pytest.raises(DatosInvalidosError):
        Proyecto(cliente="   ").validar()
    with pytest.raises(DatosInvalidosError):
        Proyecto(cliente="X", cobro_total=-1).validar()
    with pytest.raises(DatosInvalidosError):
        Proyecto(cliente="X", cobro_total=100, sena=500).validar()


def test_cliente_requiere_nombre():
    with pytest.raises(DatosInvalidosError):
        Cliente(nombre="").validar()


def test_no_se_elimina_fotografo_con_entregas_activas():
    fotografo = Fotografo(nombre="Marina")
    fotografo.trabajos = [
        TrabajoPendiente(titulo="Edición", fotografo_id=1,
                         estado=EstadoTrabajo.EN_EDICION)
    ]

    with pytest.raises(EliminacionRestringidaError):
        validar_eliminacion_fotografo(fotografo)


def test_no_se_elimina_fotografo_con_equipos():
    from fotia.domain.models import Equipo

    fotografo = Fotografo(nombre="Jorge")
    fotografo.equipos_tomados = [Equipo(numero_serie="SN1", marca="Sony", modelo="A7")]

    with pytest.raises(EliminacionRestringidaError):
        validar_eliminacion_fotografo(fotografo)


def test_generacion_de_contrato_desde_plantilla():
    proyecto = Proyecto(
        cliente="María López",
        titulo="Casamiento López & Paz",
        cobro_total=1_500_000,
        sena=500_000,
        fecha_evento=date(2026, 11, 14),
    )

    texto = generar_texto_contrato(
        "{{cliente}} | {{titulo}} | {{fecha_evento}} | {{saldo}} | {{estudio}}",
        proyecto,
        estudio="Fotia",
    )

    assert texto == "María López | Casamiento López & Paz | 14/11/2026 | $ 1.000.000,00 | Fotia"


def test_utilidades_de_fecha_y_moneda():
    assert fecha_legible("2026-09-30") == "30/09/2026"
    assert fecha_legible(None) == ""
    assert a_fecha(date(2026, 1, 2)) == date(2026, 1, 2)
    assert moneda(150000) == "$ 150.000,00"
    assert moneda(-2500.5) == "-$ 2.500,50"
