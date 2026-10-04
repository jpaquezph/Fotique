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


def test_las_vistas_se_construyen_al_abrirlas(app):
    vistas = app.ventana.vistas
    assert vistas.construida("panel")  # la inicial
    pendientes = [clave for clave in vistas if not vistas.construida(clave)]
    if pendientes:  # la precarga u otro test pudieron haberlas armado antes
        app.ventana.mostrar(pendientes[0])
        assert vistas.construida(pendientes[0])


def test_al_redimensionar_solo_queda_ubicada_la_vista_activa(app):
    ventana = app.ventana
    ventana.mostrar("equipos")
    ventana.mostrar("servicios")
    ventana.update()
    assert ventana.vistas["equipos"].winfo_manager()  # apilada debajo de la activa

    ventana.geometry("1200x740")
    ventana.update()
    assert ventana.vistas["servicios"].winfo_manager()
    assert not ventana.vistas["equipos"].winfo_manager()

    ventana.mostrar("equipos")
    ventana.update()
    assert ventana.vistas["equipos"].winfo_ismapped()


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


# -- acceso (al final: reemplaza la sesión de la ventana compartida) --------- #


def _completar(acceso, **valores):
    for clave, valor in valores.items():
        acceso._campos[clave].delete(0, "end")
        acceso._campos[clave].insert(0, valor)


def test_acceso_primer_usuario_ingreso_y_roles(app, monkeypatch):
    from fotia.domain import auth
    from fotia.domain.models import Usuario

    monkeypatch.setattr(auth, "ITERACIONES", 1_000)
    ventana = app.ventana

    # base sin usuarios: se pide crear al administrador
    ventana.cerrar_sesion()
    acceso = ventana._acceso
    assert len(ventana.vistas) == 0
    _completar(acceso, nombre="Jorge Páquez", usuario="jorge",
               password="fotia2026", repetir="otra2026")
    acceso._accion()
    assert "no coinciden" in acceso._mensaje.cget("text")
    assert not app.repos.usuarios.hay_usuarios()

    _completar(acceso, repetir="fotia2026")
    acceso._accion()
    assert app.usuario is None  # antes de entrar se muestra el código de recuperación
    acceso._accion()
    ventana.update()
    assert app.usuario.es_admin
    assert "usuarios" in ventana.vistas
    assert ventana.clave_activa == "panel"

    # contraseña incorrecta y luego ingreso de un operador
    app.repos.usuarios.crear(Usuario(usuario="marina"), "marina2026")
    ventana.cerrar_sesion()
    acceso = ventana._acceso
    _completar(acceso, usuario="marina", password="incorrecta1")
    acceso._accion()
    assert app.usuario is None
    assert "incorrectos" in acceso._mensaje.cget("text")

    _completar(acceso, password="marina2026")
    acceso._accion()
    ventana.update()
    assert app.usuario.usuario == "marina"
    assert "usuarios" not in ventana.vistas  # sólo administradores
    assert "usuarios" not in ventana._botones


def test_acceso_recupera_la_password_con_el_codigo(app, monkeypatch):
    from fotia.domain import auth

    monkeypatch.setattr(auth, "ITERACIONES", 1_000)
    ventana = app.ventana
    repo = app.repos.usuarios
    codigo = repo.regenerar_codigo(repo.por_nombre("marina").id, "marina2026")

    ventana.cerrar_sesion()
    acceso = ventana._acceso
    acceso.mostrar_recuperacion()
    _completar(acceso, usuario="marina", codigo=codigo,
               password="recuperada7", repetir="recuperada7")
    acceso._accion()   # restablece y muestra el código nuevo
    acceso._accion()   # vuelve al ingreso con el usuario cargado
    assert acceso._campos["usuario"].get() == "marina"
    _completar(acceso, password="recuperada7")
    acceso._accion()
    ventana.update()
    assert app.usuario.usuario == "marina"
