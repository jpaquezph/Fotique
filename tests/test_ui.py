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

    proyecto = max(app.repos.proyectos.listar(),
                   key=lambda p: p.obtener_saldo_pendiente())
    dialogo = DialogoPago(app.ventana, proyecto)
    dialogo.update()
    with pytest.raises(DatosInvalidosError):
        dialogo._guardar()

    dialogo._campos["monto"].insert(0, "150.000,50")
    datos = dialogo._guardar()
    assert datos["monto"] == 150000.5

    dialogo._campos["monto"].delete(0, "end")
    dialogo._campos["monto"].insert(0, str(proyecto.obtener_saldo_pendiente() + 1))
    with pytest.raises(DatosInvalidosError):  # supera el cobro total
        dialogo._guardar()
    dialogo.destroy()


def test_las_fechas_se_eligen_del_calendario(app):
    from datetime import date

    from fotia.ui.dialogs import DialogoAsignar
    from fotia.ui.fechas import Calendario, SelectorFecha

    equipo = app.repos.equipos.listar()[-1]
    dialogo = DialogoAsignar(app.ventana, equipo, app.repos.fotografos.listar(),
                             app.repos.proyectos.listar())
    dialogo.update()
    retiro, entrega = dialogo._campos["retiro"], dialogo._campos["entrega"]
    assert isinstance(retiro, SelectorFecha)
    assert retiro.fecha() == date.today() and entrega.fecha() is None

    elegidas = []
    calendario = Calendario(dialogo, date(2026, 10, 4), elegidas.append)
    calendario._subir_nivel()            # días ➜ años
    calendario._mover(-1)                # página anterior de años
    calendario._ir_a(anio=2011)          # ➜ meses
    calendario._ir_a(mes=3)              # ➜ días de marzo de 2011
    assert (calendario._anio, calendario._mes, calendario._modo) == (2011, 3, "dias")
    calendario._elegir(date(2011, 3, 15))
    assert elegidas == [date(2011, 3, 15)]

    dialogo.poner_fecha("entrega", date(2020, 1, 1))
    with pytest.raises(Exception):       # entrega anterior al retiro
        dialogo._guardar()
    dialogo.poner_fecha("entrega", date.today())
    datos = dialogo._guardar()
    assert datos["fecha"] == datos["fecha_prevista"] == date.today()
    assert datos["proyecto_id"] is None
    dialogo.destroy()


def test_doble_clic_en_un_dia_del_calendario_agrega_un_evento(app, monkeypatch):
    from datetime import timedelta

    from fotia.domain.models import Evento
    from fotia.ui.views import calendario

    class DialogoFalso:
        def __init__(self, _master, _fotografos, _proyectos, fecha, evento=None):
            self._fecha = fecha

        def mostrar(self):
            return Evento(titulo="Reunión con proveedores", fecha=self._fecha)

    monkeypatch.setattr(calendario, "DialogoEvento", DialogoFalso)
    app.ventana.mostrar("calendario")
    vista = app.ventana.vistas["calendario"]
    indice = 17 if vista._inicio_grilla() + timedelta(days=17) != vista._dia else 18
    dia = vista._inicio_grilla() + timedelta(days=indice)

    vista._nuevo_evento_en_celda(indice)
    app.ventana.update()
    assert vista._dia == dia
    creados = [e for e in app.repos.eventos.listar()
               if e.titulo == "Reunión con proveedores"]
    assert [e.fecha for e in creados] == [dia]
    assert "Reunión con proveedores" in [
        vista.tabla.tree.item(i, "values")[1] for i in vista.tabla.tree.get_children()]
    app.repos.eventos.eliminar(creados[0].id)
    app.ventana.mostrar("panel")


def test_historial_de_equipos_filtra_por_equipo_fotografo_y_fecha(app):
    from fotia.ui.dialogs import DialogoHistorialEquipos
    from fotia.util import a_fecha

    repos = app.repos
    todos = repos.equipos.historial()
    assert todos

    def cargar(equipo_id, fotografo_id, desde, hasta):
        return repos.equipos.historial(equipo_id=equipo_id, fotografo_id=fotografo_id,
                                       desde=desde, hasta=hasta)

    def mostrados(dialogo):
        return len(dialogo.tabla.tree.get_children())

    dialogo = DialogoHistorialEquipos(app.ventana, repos.equipos.listar(),
                                      repos.fotografos.listar(), cargar)
    dialogo.update()
    assert mostrados(dialogo) == len(todos)

    dia = a_fecha(todos[-1]["fecha_asignacion"])
    dialogo._desde.set(dia)              # elegir en el calendario refresca solo
    dialogo._hasta.set(dia)
    assert mostrados(dialogo) == sum(
        1 for m in todos if a_fecha(m["fecha_asignacion"]) == dia)

    dialogo._limpiar()
    fotografo = next(f for f in repos.fotografos.listar()
                     if f.id == todos[0]["fotografo_id"])
    dialogo._fotografo.set(fotografo.nombre_completo)
    dialogo._refrescar()
    assert mostrados(dialogo) == len(repos.equipos.historial(fotografo_id=fotografo.id))
    dialogo.destroy()

    # doble clic en un equipo: abre ya filtrado por esa unidad
    equipo = next(e for e in repos.equipos.listar() if e.id == todos[0]["equipo_id"])
    dialogo = DialogoHistorialEquipos(app.ventana, repos.equipos.listar(),
                                      repos.fotografos.listar(), cargar, equipo)
    assert mostrados(dialogo) == len(repos.equipos.historial(equipo_id=equipo.id))
    dialogo.destroy()


def test_tarifario_agrupa_los_servicios_por_categoria(app):
    from fotia.ui.views.servicios import _agrupar

    servicios = app.repos.servicios.listar()
    filas, objetos, etiquetas = _agrupar(servicios)
    categorias = {s.categoria for s in servicios}
    assert etiquetas.count("grupo") == len(categorias)
    assert [o for o in objetos if o is not None] == servicios
    assert all(o is None for o, e in zip(objetos, etiquetas) if e == "grupo")

    vista = app.ventana.vistas["servicios"]
    vista.refrescar()
    assert len(vista.tabla.tree.get_children()) == len(servicios) + len(categorias)


def test_resumen_general_recorre_sus_secciones(app):
    from fotia.ui.views.resumen import PERIODOS, SECCIONES, rango_periodo
    from datetime import date

    vista = app.ventana.vistas["resumen"]
    app.ventana.mostrar("resumen")
    for seccion in SECCIONES:
        vista._seccion.set(seccion)
        vista._mostrar_seccion()
        app.ventana.update()
    vista._seccion.set("Dinero")
    vista._periodo.set("Todo")
    vista._mostrar_seccion()
    movimientos = app.repos.informes.movimientos()
    assert len(vista.tabla_movimientos.tree.get_children()) == len(movimientos)
    assert vista.torta_dinero._datos  # los ingresos del estudio de ejemplo

    assert rango_periodo("Este mes", date(2026, 2, 10)) == (
        date(2026, 2, 1), date(2026, 2, 28))
    assert rango_periodo("Año pasado", date(2026, 2, 10)) == (
        date(2025, 1, 1), date(2025, 12, 31))
    assert rango_periodo("Todo") == (None, None)
    assert set(PERIODOS) >= {"Este mes", "Todo"}


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


def _textos_de_botones(widget) -> set[str]:
    import customtkinter as ctk

    textos = set()
    for hijo in widget.winfo_children():
        if isinstance(hijo, ctk.CTkButton):
            textos.add(hijo.cget("text"))
        textos |= _textos_de_botones(hijo)
    return textos


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
    assert "resumen" in ventana.vistas and "Eliminar" in _textos_de_botones(
        ventana.vistas["equipos"])
    # «Cambiar de usuario» (pie de la barra lateral) vuelve a la pantalla de ingreso
    from fotia.ui.widgets import DialogoMensaje

    monkeypatch.setattr(DialogoMensaje, "confirmar", lambda *a, **k: True)
    assert "Cambiar de usuario" in _textos_de_botones(ventana._principal[0])
    ventana.pedir_cambio_de_usuario()
    assert app.usuario is None
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
    assert "resumen" not in ventana.vistas
    assert "usuarios" not in ventana._botones
    assert "Eliminar" not in _textos_de_botones(ventana.vistas["equipos"])


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
