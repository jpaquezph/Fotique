"""Estudio fotográfico de ejemplo para las pruebas y los scripts (no se empaqueta)."""

from __future__ import annotations

from datetime import date, timedelta

from fotique.domain.models import (
    Cliente,
    Contrato,
    Equipo,
    EstadoEquipo,
    EstadoProyecto,
    EstadoTrabajo,
    Evento,
    Fotografo,
    PlantillaContrato,
    Proyecto,
    Servicio,
    TrabajoPendiente,
)
from fotique.domain.services import PLANTILLA_CONTRATO_BASE

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def _en(dias: int) -> date:
    """Fecha relativa a hoy (útil para ver alertas de service y entregas)."""
    return date.today() + timedelta(days=dias)


def cargar_datos_demo(repos) -> dict[str, int]:
    """Carga un estudio fotográfico completo de ejemplo. Idempotente."""
    if not repos.esta_vacio():
        return repos.resumen()

    # -- Módulo B: personal ------------------------------------------------ #
    fotografos = [
        Fotografo(nombre="Jorge", apellido="Páquez", telefono="+54 9 341 555 0101",
                  email="jorge@fotique.example"),
        Fotografo(nombre="Marina", apellido="Roldán", telefono="+54 9 341 555 0102",
                  email="marina@fotique.example"),
        Fotografo(nombre="Tomás", apellido="Benítez", telefono="+54 9 341 555 0103",
                  email="tomas@fotique.example"),
        Fotografo(nombre="Lucía", apellido="Ferreyra", telefono="+54 9 341 555 0104",
                  email="lucia@fotique.example"),
    ]
    for fotografo in fotografos:
        repos.fotografos.crear(fotografo)
    jorge, marina, tomas, _ = fotografos

    # -- Módulo A: inventario --------------------------------------------- #
    equipos = [
        Equipo(numero_serie="SN123456", marca="Sony", modelo="A7 IV", categoria="Cámara",
               fecha_adquisicion=_en(-820), fecha_service_ultimo=_en(-380),
               fecha_service_proximo=_en(-15)),
        Equipo(numero_serie="SN223344", marca="Sony", modelo="A7 IV", categoria="Cámara",
               fecha_adquisicion=_en(-600), fecha_service_ultimo=_en(-200),
               fecha_service_proximo=_en(18)),
        Equipo(numero_serie="SN998877", marca="Canon", modelo="R6 Mark II",
               categoria="Cámara",
               fecha_adquisicion=_en(-420), fecha_service_ultimo=_en(-160),
               fecha_service_proximo=_en(120)),
        Equipo(numero_serie="SN556677", marca="Nikon", modelo="Z6 III",
               fecha_adquisicion=_en(-300), fecha_service_proximo=_en(25)),
        Equipo(numero_serie="LEN80MM01", marca="Sigma", modelo="85mm f/1.4",
               fecha_adquisicion=_en(-900), fecha_service_proximo=_en(300)),
        Equipo(numero_serie="LEN247001", marca="Sony", modelo="24-70mm f/2.8",
               fecha_adquisicion=_en(-700), fecha_service_proximo=_en(9)),
        Equipo(numero_serie="FLASH900X", marca="Godox", modelo="V1-S",
               categoria="Iluminación",
               fecha_adquisicion=_en(-250)),
        Equipo(numero_serie="TRIPD001", marca="Manfrotto", modelo="055XPRO3",
               categoria="Accesorio",
               fecha_adquisicion=_en(-1100), notas="Incluye cabeza 496."),
    ]
    for equipo in equipos:
        repos.equipos.crear(equipo)

    repos.equipos.asignar(equipos[0].id, jorge.id, _en(-40), "Casa de Rivas")
    repos.equipos.asignar(equipos[4].id, jorge.id, _en(-40))
    repos.equipos.asignar(equipos[2].id, marina.id, _en(-20), "Casamiento Vera")
    repos.equipos.asignar(equipos[5].id, tomas.id, _en(-7), "Book corporativo")

    # -- Módulo C: clientes y proyectos ------------------------------------ #
    clientes = [
        Cliente(nombre="María López", responsable="María López",
                telefono="+54 9 341 444 0001",
                direccion="Av. Pellegrini 2400, Rosario"),
        Cliente(nombre="Estudio Vértice", responsable="Pablo Sandoval",
                telefono="+54 341 444 0002",
                direccion="Cordoba 1230, Rosario"),
        Cliente(nombre="Familia Rivas", responsable="Ana Rivas",
                telefono="+54 9 341 444 0003",
                direccion="Callao 340, Funes"),
        Cliente(nombre="Bodas Vera & Paz", responsable="Sofía Vera",
                telefono="+54 9 341 444 0004",
                direccion="Club del Lago, Rosario"),
        Cliente(nombre="Heladera Nórdica", responsable="Dante Iglesias",
                telefono="+54 341 444 0005",
                direccion="San Martín 890, Rosario"),
    ]
    for cliente in clientes:
        repos.clientes.crear(cliente)

    proyectos = [
        Proyecto(cliente="", titulo="Casamiento López & Paz", tipo="Boda", cobro_total=1_500_000,
                 sena=500_000, cliente_id=clientes[0].id, fotografo_id=jorge.id,
                 fecha_evento=_en(45), estado=EstadoProyecto.CONFIRMADO,
                 sena_fecha=_en(-30), sena_medio="Transferencia",
                 direccion="Estancia La Candelaria, Funes"),
        Proyecto(cliente="", titulo="Book corporativo Vértice", tipo="Empresarial", cobro_total=420_000,
                 sena=140_000, cliente_id=clientes[1].id, fotografo_id=tomas.id,
                 fecha_evento=_en(12), estado=EstadoProyecto.EN_CURSO,
                 sena_fecha=_en(-10), sena_medio="Efectivo"),
        Proyecto(cliente="", titulo="15 años Emilia Rivas", tipo="15 años", cobro_total=680_000,
                 sena=200_000, cliente_id=clientes[2].id, fotografo_id=marina.id,
                 fecha_evento=_en(70), estado=EstadoProyecto.CONFIRMADO,
                 sena_fecha=_en(-5), sena_medio="Mercado Pago"),
        Proyecto(cliente="", titulo="Casamiento Vera (ceremonia)", tipo="Boda", cobro_total=2_100_000,
                 sena=700_000, cliente_id=clientes[3].id, fotografo_id=marina.id,
                 fecha_evento=_en(-25), estado=EstadoProyecto.CERRADO,
                 sena_fecha=_en(-120), sena_medio="Transferencia"),
        Proyecto(cliente="", titulo="Catálogo Nórdica invierno", tipo="Empresarial", cobro_total=560_000,
                 sena=0, cliente_id=clientes[4].id, fotografo_id=tomas.id,
                 fecha_evento=_en(20), estado=EstadoProyecto.PRESUPUESTO),
        Proyecto(cliente="", titulo="Product shots Nórdica", tipo="Gastronómica", cobro_total=310_000,
                 sena=100_000, cliente_id=clientes[4].id, fotografo_id=jorge.id,
                 fecha_evento=_en(-60), estado=EstadoProyecto.CERRADO,
                 sena_fecha=_en(-90), sena_medio="Transferencia"),
    ]
    for proyecto in proyectos:
        repos.proyectos.crear(proyecto)

    repos.proyectos.crear_pago(proyectos[0].id, 300_000, _en(-10), "Transferencia",
                               "Cuota 2")
    repos.proyectos.crear_pago(proyectos[1].id, 140_000, _en(-1), "Efectivo", "Cuota 2")
    repos.proyectos.crear_pago(proyectos[3].id, 700_000, _en(-20), "Transferencia",
                               "Cuota 2")
    repos.proyectos.crear_pago(proyectos[3].id, 500_000, _en(-3), "Transferencia",
                               "Cuota final")
    repos.proyectos.crear_pago(proyectos[5].id, 150_000, _en(-55), "Efectivo")
    repos.proyectos.crear_pago(proyectos[5].id, 60_000, _en(-30), "Efectivo")

    # -- Trabajos y entregas --------------------------------------- #
    trabajos = [
        TrabajoPendiente(titulo="Edición selección casamiento", rol="Fotógrafo", descripcion="120 fotos",
                         fotografo_id=jorge.id, proyecto_id=proyectos[0].id,
                         fecha_entrega=_en(60), estado=EstadoTrabajo.EN_EDICION),
        TrabajoPendiente(titulo="Entrega galería online", rol="Fotógrafo", descripcion="Link privado",
                         fotografo_id=jorge.id, proyecto_id=proyectos[0].id,
                         fecha_entrega=_en(65), estado=EstadoTrabajo.PENDIENTE),
        TrabajoPendiente(titulo="Retoque retratos equipo", rol="Fotógrafo", descripcion="30 fotos",
                         fotografo_id=tomas.id, proyecto_id=proyectos[1].id,
                         fecha_entrega=_en(4), estado=EstadoTrabajo.EN_EDICION),
        TrabajoPendiente(titulo="Prueba de luz locación", rol="Iluminador",
                         fotografo_id=marina.id, proyecto_id=proyectos[2].id,
                         fecha_entrega=_en(21), estado=EstadoTrabajo.PENDIENTE),
        TrabajoPendiente(titulo="Álbum impreso Vera", rol="Segunda cámara", descripcion="Fotolibro 30x30",
                         fotografo_id=marina.id, proyecto_id=proyectos[3].id,
                         fecha_entrega=_en(-8), estado=EstadoTrabajo.ENTREGADO),
        TrabajoPendiente(titulo="Selección producto Nórdica", rol="Asistente", descripcion="40 fotos",
                         fotografo_id=jorge.id, proyecto_id=proyectos[5].id,
                         fecha_entrega=_en(-40), estado=EstadoTrabajo.ENTREGADO),
    ]
    for trabajo in trabajos:
        repos.trabajos.crear(trabajo)

    # -- Módulo D: tarifario --------------------------------------- #
    servicios = [
        Servicio(nombre="Cobertura boda (8 hs)", categoria="Coberturas",
                 precio=650_000, unidad="evento"),
        Servicio(nombre="Cobertura 15 años (6 hs)", categoria="Coberturas",
                 precio=420_000, unidad="evento"),
        Servicio(nombre="Sesión de estudio (2 hs)", categoria="Sesiones",
                 precio=120_000, unidad="sesión"),
        Servicio(nombre="Book corporativo", categoria="Sesiones",
                 precio=180_000, unidad="sesión"),
        Servicio(nombre="Edición por foto extra", categoria="Edición",
                 precio=4_500, unidad="foto"),
        Servicio(nombre="Retoque premium", categoria="Edición",
                 precio=9_000, unidad="foto"),
        Servicio(nombre="Fotolibro 20x20 (30 págs.)", categoria="Fotolibros",
                 precio=95_000, unidad="unidad"),
        Servicio(nombre="Copias 20x30 mate", categoria="Fotolibros",
                 precio=6_500, unidad="copia"),
        Servicio(nombre="Viáticos zona Litoral", categoria="Viáticos",
                 precio=35_000, unidad="día"),
        Servicio(nombre="Asistente de fotografía", categoria="Personal",
                 precio=85_000, unidad="jornada"),
    ]
    for servicio in servicios:
        repos.servicios.crear(servicio)

    # -- Contratos ------------------------------------------------- #
    plantilla = repos.plantillas.crear(
        PlantillaContrato(
            nombre="Contrato estándar de servicios",
            contenido=PLANTILLA_CONTRATO_BASE,
        )
    )
    repos.plantillas.crear(
        PlantillaContrato(
            nombre="Addendum de exclusividad",
            contenido=(
                "ADDENDUM\n\nEl cliente {{cliente}} solicita exclusividad para el "
                "proyecto {{titulo}} a realizarse el {{fecha_evento}}.\n\n"
                "Importe adicional: {{cobro_total}}   Saldo: {{saldo}}"
            ),
        )
    )
    repos.contratos.crear(
        Contrato(
            nombre="Contrato Casamiento López & Paz",
            proyecto_id=proyectos[0].id,
            plantilla_id=plantilla.id,
            contenido="Firmado por ambas partes.",
            estado="Firmado",
            fecha=_en(-30),
        )
    )

    # -- Agenda ---------------------------------------------------- #
    eventos = [
        Evento(titulo="Previa sesión de fotos López", fecha=_en(10), hora="16:00",
               tipo="Sesión", fotografo_id=jorge.id, proyecto_id=proyectos[0].id),
        Evento(titulo="Reunión presupuesto Nórdica", fecha=_en(3), hora="11:00",
               tipo="Reunión", notas="Definir cantidad de productos."),
        Evento(titulo="Entrega álbum Vera (retiro)", fecha=_en(-8), hora="18:30",
               tipo="Entrega", fotografo_id=marina.id, proyecto_id=proyectos[3].id),
        Evento(titulo="Setup estudio", fecha=_en(1), hora="09:00", tipo="Otro"),
    ]
    for evento in eventos:
        repos.eventos.crear(evento)

    repos.set_config("estudio", "Estudio Fotique")
    return repos.resumen()
