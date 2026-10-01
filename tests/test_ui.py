"""Pruebas de GUI (pirámide nivel 3): ventanas, diálogos y formularios."""

from __future__ import annotations

import pytest

tkinter = pytest.importorskip("tkinter")  # noqa: N806


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    from fotia.app import Aplicacion
    from fotia.db import cargar_datos_demo
    from fotia.ui import VentanaPrincipal
    from fotia.ui.theme import aplicar_estilo_tabla, configurar_apariencia

    configurar_apariencia("Dark")
    aplicar_estilo_tabla()
    base = Aplicacion(tmp_path_factory.mktemp("ui") / "ui.db")
    cargar_datos_demo(base.repos)
    ventana = VentanaPrincipal(base)
    base.ventana = ventana
    ventana.update()
    yield base
    ventana.destroy()
    base.cerrar()


def test_todas_las_vistas_se_construyen_y_refrescan(app):
    from fotia.ui.views import TODAS

    assert len(app.ventana.vistas) == len(TODAS)
    for clave, vista in app.ventana.vistas.items():
        vista.refrescar()
        app.ventana.update()
        assert vista.clave == clave


def test_navegacion_entre_vistas(app):
    claves = list(app.ventana.vistas)
    for clave in claves:
        app.ventana.mostrar(clave)
        app.ventana.update()
        assert app.ventana.clave_activa == clave
    app.ventana.mostrar("panel")
    assert app.ventana.clave_activa == "panel"


def test_resumen_del_panel_usa_la_base(app):
    vista = app.ventana.vistas["panel"]
    vista.refrescar()
    resumen = app.repos.resumen()
    assert vista._tarjetas["equipos"]._valor.cget("text") == str(resumen["equipos"])


def test_tabla_de_equipos_muestra_la_base(app):
    vista = app.ventana.vistas["equipos"]
    vista.refrescar()
    assert len(vista.tabla.tree.get_children()) == len(app.repos.equipos.listar())
    assert not vista.tabla.vacio()


def test_seleccion_en_tabla(app):
    vista = app.ventana.vistas["equipos"]
    vista.refrescar()
    primer_iid = vista.tabla.tree.get_children()[0]
    vista.tabla.tree.selection_set(primer_iid)
    seleccionado = vista.tabla.seleccionado()
    assert seleccionado is not None
    assert seleccionado.numero_serie


# -- formularios ------------------------------------------------------------ #


def test_dialogo_de_equipo_extrae_los_campos(app):
    from fotia.ui.dialogs import DialogoEquipo

    equipo = app.repos.equipos.listar()[0]
    dialogo = DialogoEquipo(app.ventana, equipo)
    dialogo.update()
    assert dialogo.texto("serie") == equipo.numero_serie
    dialogo._campos["marca"].delete(0, "end")
    dialogo._campos["marca"].insert(0, "Canon")
    guardado = dialogo._guardar()
    assert guardado.marca == "Canon"
    assert guardado.id == equipo.id
    dialogo.destroy()


def test_dialogo_de_pago_valida_monto(app):
    from fotia.domain.errors import DatosInvalidosError
    from fotia.ui.dialogs import DialogoPago

    proyecto = app.repos.proyectos.listar()[0]
    dialogo = DialogoPago(app.ventana, proyecto)
    dialogo.update()
    with pytest.raises(DatosInvalidosError):
        dialogo._guardar()

    dialogo._campos["monto"].insert(0, "150.000,50")
    datos = dialogo._guardar()
    assert datos["monto"] == 150000.5
    dialogo.destroy()


def test_selector_de_objetos_devuelve_el_elegido(app):
    from fotia.ui.dialogs import DialogoEvento, _etiqueta_fotografo

    fotografos = app.repos.fotografos.listar()
    from fotia.domain.models import Evento
    from datetime import date

    dialogo = DialogoEvento(app.ventana, fotografos, app.repos.proyectos.listar(),
                            date.today(), Evento(titulo="T", fecha=date.today()))
    dialogo.update()
    elegido = dialogo.objeto("fotografo")
    assert elegido is not None
    assert dialogo.texto("fotografo") == _etiqueta_fotografo(elegido)
    dialogo.destroy()


def test_contrato_se_genera_desde_plantilla(app):
    from fotia.ui.dialogs import DialogoContrato

    proyecto = app.repos.proyectos.listar()[0]
    plantillas = app.repos.plantillas.listar()
    dialogo = DialogoContrato(app.ventana, app.repos.proyectos.listar(), plantillas)
    dialogo.update()
    dialogo._objetos_selector["proyecto"][
        next(iter(dialogo._objetos_selector["proyecto"]))
    ] = proyecto
    dialogo._campos["proyecto"].set(
        next(k for k, v in dialogo._objetos_selector["proyecto"].items()
             if v is proyecto))
    dialogo._campos["plantilla"].set(plantillas[0].nombre)
    dialogo._generar_contenido()
    contenido = dialogo.texto("contenido")
    assert proyecto.cliente in contenido
    assert str(proyecto.cobro_total) not in contenido or "$" in contenido
    dialogo.destroy()


# -- utilidades de campos ---------------------------------------------------- #


def test_parsear_fecha_y_monto():
    from datetime import date

    from fotia.ui.widgets import parsear_fecha, parsear_monto

    assert parsear_fecha("30/09/2026") == date(2026, 9, 30)
    assert parsear_fecha("2026-09-30") == date(2026, 9, 30)
    assert parsear_fecha("") is None
    assert parsear_monto("1500000") == 1_500_000
    assert parsear_monto("1.500.000,00") == 1_500_000
    assert parsear_monto("1,500,000.00") == 1_500_000
    assert parsear_monto("123,45") == 123.45
    assert parsear_monto("") == 0.0
