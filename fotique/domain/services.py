"""Reglas de negocio transversales de Fotique (servicios de dominio)."""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from ..util import a_fecha, a_texto, fecha_legible, moneda
from .errors import DatosInvalidosError, EliminacionRestringidaError
from .models import (
    Equipo,
    EstadoProyecto,
    EstadoService,
    EstadoTrabajo,
    Fotografo,
    Proyecto,
    TrabajoPendiente,
)

__all__ = [
    "PLANTILLA_CONTRATO_BASE",
    "a_fecha",
    "a_texto",
    "asignar_equipo",
    "entregas_por_estado",
    "equipos_en_alerta",
    "equipos_en_uso_de",
    "fecha_legible",
    "generar_texto_contrato",
    "moneda",
    "proyectos_con_saldo",
    "resumen_financiero",
    "saldo_proyecto",
    "validar_eliminacion_fotografo",
    "validar_proyecto",
]

# --------------------------------------------------------------------------- #
# Inventario (Módulo A)
# --------------------------------------------------------------------------- #


def asignar_equipo(
    equipo: Equipo, fotografo: Optional[Fotografo], fecha: Optional[date] = None
) -> date:
    """Asigna un equipo ``En stock`` a un fotógrafo responsable."""
    equipo.asignar_a_fotografo(fotografo)
    return fecha or date.today()


def equipos_en_alerta(
    equipos: Iterable[Equipo], hoy: Optional[date] = None, dias_aviso: int = 30
) -> list[tuple[Equipo, EstadoService]]:
    """Equipos con service vencido o próximo."""
    hoy = hoy or date.today()
    alertas = []
    for equipo in equipos:
        estado = equipo.estado_service(hoy=hoy, dias_aviso=dias_aviso)
        if estado in (EstadoService.VENCIDO, EstadoService.PROXIMO):
            alertas.append((equipo, estado))
    return alertas


def equipos_en_uso_de(fotografo: Fotografo) -> list[Equipo]:
    return [e for e in fotografo.equipos_tomados]


# --------------------------------------------------------------------------- #
# Personal (Módulo B)
# --------------------------------------------------------------------------- #


def validar_eliminacion_fotografo(fotografo: Fotografo) -> None:
    """No se elimina un fotógrafo con entregas activas ni con equipos."""
    if fotografo.entregas_activas:
        raise EliminacionRestringidaError(
            f"{fotografo.nombre_completo} tiene "
            f"{len(fotografo.entregas_activas)} entrega(s) pendiente(s)."
        )
    if fotografo.equipos_tomados:
        raise EliminacionRestringidaError(
            f"{fotografo.nombre_completo} tiene equipos tomados del stock: "
            + ", ".join(e.descripcion for e in fotografo.equipos_tomados)
        )


def entregas_por_estado(
    trabajos: Iterable[TrabajoPendiente], estado: EstadoTrabajo
) -> list[TrabajoPendiente]:
    return [t for t in trabajos if t.estado == estado]


# --------------------------------------------------------------------------- #
# Comercial (Módulo C)
# --------------------------------------------------------------------------- #


def saldo_proyecto(proyecto: Proyecto) -> float:
    """Cobro total - seña - pagos parciales."""
    return proyecto.obtener_saldo_pendiente()


def proyectos_con_saldo(proyectos: Iterable[Proyecto]) -> list[Proyecto]:
    return [p for p in proyectos if p.obtener_saldo_pendiente() > 0]


def resumen_financiero(proyecto: Proyecto) -> dict[str, float]:
    return {
        "cobro_total": proyecto.cobro_total,
        "sena": proyecto.sena,
        "pagos_parciales": proyecto.total_pagos_parciales,
        "total_pagado": proyecto.total_pagado,
        "saldo": proyecto.obtener_saldo_pendiente(),
    }


def validar_proyecto(proyecto: Proyecto) -> None:
    proyecto.validar()
    if proyecto.estado not in tuple(EstadoProyecto):
        raise DatosInvalidosError(f"Estado de proyecto inválido: {proyecto.estado}")


# --------------------------------------------------------------------------- #
# Contratos
# --------------------------------------------------------------------------- #

PLANTILLA_CONTRATO_BASE = """CONTRATO DE PRESTACIÓN DE SERVICIOS FOTOGRÁFICOS

Entre {{estudio}} y {{cliente}}, por el proyecto "{{titulo}}".

Cliente: {{cliente}}
Teléfono: {{telefono_cliente}}
Evento: {{fecha_evento}}
Locación: {{direccion}}
Fotógrafo responsable: {{fotografo}}

Importe total: {{cobro_total}}
Seña abonada: {{sena}}
Saldo pendiente: {{saldo}}

{{contenido_extra}}

Firmas:
Cliente ______________________   Estudio ______________________
"""


def _d(valor: object, vacio: str = "—") -> str:
    texto = str(valor).strip() if valor is not None else ""
    return texto or vacio


def generar_texto_contrato(
    plantilla: str, proyecto: Proyecto, estudio: str = "Estudio Fotique", extra: str = ""
) -> str:
    """Completa una plantilla con los datos del proyecto."""
    from ..util import moneda as _moneda  # import diferido: evita ciclos

    datos = {
        "estudio": estudio,
        "cliente": _d(proyecto.cliente),
        "titulo": _d(proyecto.titulo, "Sin título"),
        "fecha_evento": fecha_legible(proyecto.fecha_evento) or "—",
        "direccion": _d(proyecto.direccion),
        "fotografo": (
            proyecto.fotografo.nombre_completo if proyecto.fotografo else "—"
        ),
        "cobro_total": _moneda(proyecto.cobro_total),
        "sena": _moneda(proyecto.sena),
        "saldo": _moneda(proyecto.obtener_saldo_pendiente()),
        "telefono_cliente": _d(getattr(proyecto, "telefono_cliente", "")),
        "contenido_extra": extra,
    }
    texto = plantilla
    for clave, valor in datos.items():
        texto = texto.replace("{{" + clave + "}}", valor)
    return texto
