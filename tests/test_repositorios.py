"""Pruebas de integración sobre SQLite en memoria (pirámide nivel 2)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from fotique.domain import (
    Cliente,
    DatosInvalidosError,
    EliminacionRestringidaError,
    Equipo,
    EquipoNoDisponibleException,
    EstadoEquipo,
    EstadoTrabajo,
    Evento,
    Fotografo,
    Proyecto,
    TrabajoPendiente,
)
from fotique.db import cargar_datos_demo


def _alta_base(repos):
    fotografo = repos.fotografos.crear(Fotografo(nombre="Jorge", apellido="Páquez"))
    equipo = repos.equipos.crear(
        Equipo(numero_serie="SN123456", marca="Sony", modelo="A7 IV")
    )
    cliente = repos.clientes.crear(Cliente(nombre="María López", telefono="123"))
    return fotografo, equipo, cliente


# -- Módulo A ---------------------------------------------------------------- #


def test_crear_equipo_y_detectar_serie_duplicada(repos):
    _alta_base(repos)

    with pytest.raises(DatosInvalidosError):
        repos.equipos.crear(Equipo(numero_serie="SN123456", marca="Canon", modelo="R6"))


def test_asignar_equipo_registra_historial(repos):
    fotografo, equipo, _ = _alta_base(repos)

    repos.equipos.asignar(equipo.id, fotografo.id, date(2026, 9, 1), "Casa de Rivas")

    guardado = repos.equipos.obtener(equipo.id)
    assert guardado.estado == EstadoEquipo.EN_USO
    assert guardado.fotografo_actual.id == fotografo.id
    historial = repos.equipos.historial(equipo_id=equipo.id)
    assert len(historial) == 1
    assert historial[0]["fecha_asignacion"] == "2026-09-01"
    assert historial[0]["f_nombre"] == "Jorge"
    assert repos.fotografos.detalle(fotografo.id).equipos_tomados[0].id == equipo.id


def test_asignar_equipo_en_uso_lanza_excepcion(repos):
    fotografo, equipo, _ = _alta_base(repos)
    repos.equipos.asignar(equipo.id, fotografo.id)

    with pytest.raises(EquipoNoDisponibleException):
        repos.equipos.asignar(equipo.id, fotografo.id)


def test_devolver_equipo_cierra_historial(repos):
    fotografo, equipo, _ = _alta_base(repos)
    repos.equipos.asignar(equipo.id, fotografo.id, date(2026, 8, 1))

    repos.equipos.devolver(equipo.id, date(2026, 9, 10))

    guardado = repos.equipos.obtener(equipo.id)
    assert guardado.estado == EstadoEquipo.EN_STOCK
    assert guardado.fotografo_actual is None
    historial = repos.equipos.historial(equipo_id=equipo.id)
    assert historial[0]["fecha_devolucion"] == "2026-09-10"


def test_no_se_elimina_equipo_en_uso(repos):
    fotografo, equipo, _ = _alta_base(repos)
    repos.equipos.asignar(equipo.id, fotografo.id)

    with pytest.raises(EliminacionRestringidaError):
        repos.equipos.eliminar(equipo.id)


def test_filtro_de_busqueda_por_estado_y_texto(repos):
    fotografo, equipo, _ = _alta_base(repos)
    sigma = repos.equipos.crear(Equipo(numero_serie="LEN1", marca="Sigma", modelo="85mm"))

    assert len(repos.equipos.listar()) == 2
    assert len(repos.equipos.listar(estado=EstadoEquipo.EN_STOCK)) == 2
    assert [e.id for e in repos.equipos.listar(texto="sigma")] == [sigma.id]
    assert repos.equipos.listar(texto="SN123456")[0].id == equipo.id

    repos.equipos.asignar(equipo.id, fotografo.id)

    assert len(repos.equipos.listar(estado=EstadoEquipo.EN_USO)) == 1
    assert len(repos.equipos.listar(estado=EstadoEquipo.EN_STOCK)) == 1
    assert repos.equipos.listar(texto="jorge")[0].id == equipo.id


def test_alertas_de_service_sobre_la_base(repos):
    hoy = date.today()
    repos.equipos.crear(
        Equipo(
            numero_serie="VENCIDO",
            marca="Sony",
            modelo="A7 IV",
            fecha_service_proximo=hoy - timedelta(days=5),
        )
    )
    repos.equipos.crear(
        Equipo(
            numero_serie="OK",
            marca="Sony",
            modelo="A7",
            fecha_service_proximo=hoy + timedelta(days=400),
        )
    )

    alertas = repos.equipos.alertas_service(dias_aviso=30)

    assert [e.numero_serie for e, _ in alertas] == ["VENCIDO"]


def test_check_de_integridad_equipo_en_uso_sin_fotografo(repos):
    _alta_base(repos)
    with pytest.raises(Exception):
        repos.conn.execute(
            "INSERT INTO equipos (numero_serie, marca, modelo, estado, fotografo_id) "
            "VALUES ('X', 'Y', 'Z', 'En uso', NULL)"
        )


# -- Módulo B ---------------------------------------------------------------- #


def test_eliminar_fotografo_con_equipos_esta_restringido(repos):
    fotografo, equipo, _ = _alta_base(repos)
    repos.equipos.asignar(equipo.id, fotografo.id)

    with pytest.raises(EliminacionRestringidaError):
        repos.fotografos.eliminar(fotografo.id)


def test_eliminar_fotografo_con_entrega_activa_esta_restringido(repos):
    fotografo, _, cliente = _alta_base(repos)
    repos.trabajos.crear(
        TrabajoPendiente(titulo="Edición", fotografo_id=fotografo.id,
                         estado=EstadoTrabajo.PENDIENTE, fecha_entrega=date(2026, 10, 5))
    )

    with pytest.raises(EliminacionRestringidaError):
        repos.fotografos.eliminar(fotografo.id)


def test_eliminar_fotografo_sin_dependencias(repos):
    fotografo, _, _ = _alta_base(repos)

    repos.fotografos.eliminar(fotografo.id)

    assert repos.fotografos.obtener(fotografo.id) is None


# -- Módulo C ---------------------------------------------------------------- #


def test_proyecto_con_sena_y_pagos(repos):
    _, _, cliente = _alta_base(repos)
    proyecto = repos.proyectos.crear(
        Proyecto(cliente="", titulo="Casamiento", cliente_id=cliente.id,
                 cobro_total=1_500_000, sena=500_000, fecha_evento=date(2026, 11, 14))
    )
    repos.proyectos.crear_pago(proyecto.id, 300_000, date(2026, 9, 1), "Transferencia")

    guardado = repos.proyectos.obtener(proyecto.id)

    assert guardado.cliente == "María López"
    assert guardado.total_pagado == 800_000
    assert guardado.obtener_saldo_pendiente() == 700_000
    assert [p.monto for p in repos.proyectos.listar()[0].pagos] == [300_000]


def test_pago_con_monto_invalido(repos):
    _, _, cliente = _alta_base(repos)
    proyecto = repos.proyectos.crear(
        Proyecto(cliente="", titulo="X", cliente_id=cliente.id, cobro_total=100)
    )

    with pytest.raises(DatosInvalidosError):
        repos.proyectos.crear_pago(proyecto.id, -5)


def test_no_se_elimina_cliente_con_proyectos(repos):
    _, _, cliente = _alta_base(repos)
    repos.proyectos.crear(
        Proyecto(cliente="", titulo="X", cliente_id=cliente.id, cobro_total=100)
    )

    with pytest.raises(EliminacionRestringidaError):
        repos.clientes.eliminar(cliente.id)


def test_sena_se_registra_en_el_proyecto(repos):
    _, _, cliente = _alta_base(repos)
    proyecto = repos.proyectos.crear(
        Proyecto(cliente="", titulo="X", cliente_id=cliente.id, cobro_total=900)
    )

    repos.proyectos.registrar_sena(proyecto.id, 300, date(2026, 3, 4), "Efectivo")
    guardado = repos.proyectos.obtener(proyecto.id)

    assert guardado.sena == 300
    assert guardado.sena_medio == "Efectivo"
    assert guardado.obtener_saldo_pendiente() == 600


# -- Módulo D / calendario --------------------------------------------------- #


def test_calendario_consolidado_unifica_todas_las_fuentes(repos):
    fotografo, equipo, cliente = _alta_base(repos)
    base = date(2026, 10, 15)
    proyecto = repos.proyectos.crear(
        Proyecto(cliente="", titulo="Casamiento", cliente_id=cliente.id,
                 cobro_total=100, fecha_evento=base)
    )
    repos.trabajos.crear(
        TrabajoPendiente(titulo="Entrega galería", fotografo_id=fotografo.id,
                         proyecto_id=proyecto.id, fecha_entrega=base)
    )
    repos.eventos.crear(
        Evento(titulo="Previa", fecha=base, hora="16:00", tipo="Sesión",
               fotografo_id=fotografo.id)
    )
    repos.equipos.crear(
        Equipo(numero_serie="SVC", marca="Sony", modelo="A7",
               fecha_service_proximo=base)
    )

    dia = repos.eventos.del_dia(base)
    tipos = sorted(e.tipo for e in dia)

    assert tipos == ["Entrega", "Service", "Sesión", "Sesión"]
    assert any("Casamiento" in e.titulo for e in dia)
    assert any("SVC" in e.titulo for e in dia)


def test_calendario_filtrado_por_fotografo(repos):
    fotografo, _, cliente = _alta_base(repos)
    otro = repos.fotografos.crear(Fotografo(nombre="Marina"))
    base = date(2026, 10, 20)
    repos.proyectos.crear(
        Proyecto(cliente="", titulo="A", cliente_id=cliente.id,
                 fotografo_id=fotografo.id, cobro_total=1, fecha_evento=base)
    )
    repos.eventos.crear(Evento(titulo="Del otro", fecha=base, tipo="Reunión",
                               fotografo_id=otro.id))

    filtrados = repos.eventos.del_dia(base, fotografo_id=fotografo.id)

    assert [e.titulo for e in filtrados] == ["A — María López"]


def test_servicios_y_contratos(repos):
    _, _, cliente = _alta_base(repos)
    from fotique.domain.models import Contrato, PlantillaContrato, Servicio

    servicio = repos.servicios.crear(
        Servicio(nombre="Cobertura boda", categoria="Coberturas", precio=100)
    )
    plantilla = repos.plantillas.crear(
        PlantillaContrato(nombre="Estándar", contenido="{{cliente}}")
    )
    proyecto = repos.proyectos.crear(
        Proyecto(cliente="", titulo="X", cliente_id=cliente.id, cobro_total=100)
    )
    contrato = repos.contratos.crear(
        Contrato(nombre="Contrato X", proyecto_id=proyecto.id,
                 plantilla_id=plantilla.id, contenido="Texto", fecha=date(2026, 1, 1))
    )

    assert repos.servicios.obtener(servicio.id).precio == 100
    assert [c.id for c in repos.contratos.de_proyecto(proyecto.id)] == [contrato.id]
    assert repos.contratos.listar()[0].proyecto.titulo == "X"


def test_resumen_y_carga_demo(repos):
    assert repos.esta_vacio() is True
    resumen = cargar_datos_demo(repos)

    assert resumen["equipos"] >= 6
    assert resumen["fotografos"] >= 3
    assert resumen["proyectos"] >= 5
    assert resumen["trabajos_abiertos"] >= 1
    assert repos.esta_vacio() is False

    # segunda carga: no duplica nada
    cargar_datos_demo(repos)
    assert repos.resumen() == resumen
    assert len(repos.equipos.listar(texto="Sony")) >= 2


def test_resumen_financiero_de_la_demo(repos):
    cargar_datos_demo(repos)

    proyectos = repos.proyectos.listar()
    assert all(isinstance(p, Proyecto) for p in proyectos)
    assert any(p.obtener_saldo_pendiente() > 0 for p in proyectos)


# -- Respaldos ------------------------------------------------------- #


def test_respaldo_y_restauracion(tmp_path):
    from fotique.db import BaseDatos

    ruta = tmp_path / "fotique.db"
    base = BaseDatos(ruta)
    cargar_datos_demo(base.repos)
    equipos_antes = base.repos.resumen()["equipos"]

    destino = base.respaldar(tmp_path / "respaldo.db")
    assert destino.exists()

    # cambiamos la base y volvemos al respaldo
    base.repos.equipos.eliminar(
        next(e.id for e in base.repos.equipos.listar() if e.estado == EstadoEquipo.EN_STOCK)
    )
    assert base.repos.resumen()["equipos"] == equipos_antes - 1

    base.restaurar(destino)
    assert base.repos.resumen()["equipos"] == equipos_antes
    base.cerrar()


def test_restaurar_archivo_invalido(tmp_path):
    from fotique.db import BaseDatos
    from fotique.domain.errors import ErrorBackups

    archivo = tmp_path / "basura.db"
    archivo.write_bytes(b"esto no es una base sqlite")

    base = BaseDatos(tmp_path / "fotique.db")
    with pytest.raises(ErrorBackups):
        base.restaurar(archivo)
    base.cerrar()
