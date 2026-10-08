"""Smoke test de los diálogos: construye cada uno con datos reales y lo cierra."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fotique.app import Aplicacion  # noqa: E402
from tests.datos_demo import cargar_datos_demo  # noqa: E402
from fotique.domain.models import Evento, PlantillaContrato, Servicio  # noqa: E402
from fotique.ui import VentanaPrincipal  # noqa: E402
from fotique.ui.dialogs import (  # noqa: E402
    DialogoAsignar,
    DialogoCliente,
    DialogoContrato,
    DialogoDevolver,
    DialogoDetalleProyecto,
    DialogoEquipo,
    DialogoEvento,
    DialogoFichaEquipo,
    DialogoFichaFotografo,
    DialogoFotografo,
    DialogoMensaje,
    DialogoPago,
    DialogoPlantilla,
    DialogoProyecto,
    DialogoServicio,
    DialogoTabla,
    DialogoTrabajo,
)
from fotique.ui.theme import aplicar_estilo_tabla, configurar_apariencia  # noqa: E402


def _log(mensaje: str) -> None:
    print(mensaje, flush=True)


def main() -> int:
    carpeta = Path(__file__).resolve().parent / "_smoke"
    shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(parents=True, exist_ok=True)

    app = Aplicacion(carpeta / "fotique_smoke.db")
    configurar_apariencia("Dark")
    aplicar_estilo_tabla()
    cargar_datos_demo(app.repos)
    repos = app.repos

    ventana = VentanaPrincipal(app)
    app.ventana = ventana
    ventana.update()

    equipo = repos.equipos.listar()[0]
    fotografo = repos.fotografos.listar()[0]
    cliente = repos.clientes.listar()[0]
    proyecto = repos.proyectos.listar()[0]
    servicio = repos.servicios.listar()[0]
    plantilla = repos.plantillas.listar()[0]
    contrato = repos.contratos.listar()[0]
    trabajo = repos.trabajos.listar()[0]

    pruebas = [
        ("DialogoEquipo (nuevo)", lambda: DialogoEquipo(ventana)),
        ("DialogoEquipo (editar)", lambda: DialogoEquipo(ventana, equipo,
                                                         repos.equipos.categorias())),
        ("DialogoAsignar", lambda: DialogoAsignar(ventana, equipo,
                                                   repos.fotografos.listar())),
        ("DialogoDevolver", lambda: DialogoDevolver(ventana, equipo)),
        ("DialogoFichaEquipo", lambda: DialogoFichaEquipo(
            ventana, equipo, repos.equipos.historial(equipo_id=equipo.id))),
        ("DialogoTabla", lambda: DialogoTabla(
            ventana, "Prueba", [{"clave": "a", "titulo": "A"}], [["1"], ["2"]])),
        ("DialogoFotografo", lambda: DialogoFotografo(ventana, fotografo)),
        ("DialogoFichaFotografo", lambda: DialogoFichaFotografo(
            ventana, repos.fotografos.detalle(fotografo.id),
            repos.fotografos.equipos_de(fotografo.id),
            repos.fotografos.trabajos_de(fotografo.id))),
        ("DialogoCliente", lambda: DialogoCliente(ventana, cliente)),
        ("DialogoProyecto", lambda: DialogoProyecto(
            ventana, repos.clientes.listar(), repos.fotografos.listar(), proyecto)),
        ("DialogoPago", lambda: DialogoPago(ventana, proyecto)),
        ("DialogoDetalleProyecto", lambda: DialogoDetalleProyecto(ventana, proyecto)),
        ("DialogoTrabajo", lambda: DialogoTrabajo(
            ventana, repos.fotografos.listar(), repos.proyectos.listar(), trabajo)),
        ("DialogoEvento", lambda: DialogoEvento(
            ventana, repos.fotografos.listar(), repos.proyectos.listar(),
            proyecto.fecha_evento, Evento(titulo="X", fecha=proyecto.fecha_evento))),
        ("DialogoServicio", lambda: DialogoServicio(
            ventana, repos.servicios.categorias(), servicio)),
        ("DialogoPlantilla", lambda: DialogoPlantilla(ventana, plantilla)),
        ("DialogoContrato", lambda: DialogoContrato(
            ventana, repos.proyectos.listar(), repos.plantillas.listar(), contrato)),
        ("DialogoMensaje info", lambda: DialogoMensaje(
            ventana, "Info", "Mensaje informativo", tipo="info")),
        ("DialogoMensaje error", lambda: DialogoMensaje(
            ventana, "Error", "Mensaje de error", tipo="error")),
        ("DialogoMensaje confirmar", lambda: DialogoMensaje(
            ventana, "¿Seguro?", "Confirmación", tipo="confirmar")),
    ]

    errores: list[str] = []
    for nombre, fabrica in pruebas:
        try:
            dialogo = fabrica()
            dialogo.update()
            dialogo.destroy()
            _log(f"  {nombre}: OK")
        except Exception as exc:  # noqa: BLE001
            errores.append(f"{nombre}: {type(exc).__name__}: {exc}")
            _log(f"  {nombre}: FALLA — {type(exc).__name__}: {exc}")

    # datos de prueba sueltos
    try:
        Servicio(nombre="Prueba", precio=10).validar()
        PlantillaContrato(nombre="P")
        _log("  modelos auxiliares: OK")
    except Exception as exc:  # noqa: BLE001
        errores.append(f"modelos: {exc}")

    ventana.destroy()
    app.cerrar()

    if errores:
        _log(f"SMOKE FALLÓ ({len(errores)}):")
        for e in errores:
            _log(f"  - {e}")
        return 1
    _log("SMOKE OK: todos los diálogos se construyeron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
