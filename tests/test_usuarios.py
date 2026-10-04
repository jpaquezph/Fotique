"""Acceso: hash de contraseñas, ingreso, bloqueo y recuperación."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from fotia.domain import auth
from fotia.domain.errors import (
    CredencialesInvalidasError,
    CuentaBloqueadaError,
    DatosInvalidosError,
    EliminacionRestringidaError,
)
from fotia.domain.models import RolUsuario, Usuario

CLAVE = "fotia2026"


@pytest.fixture(autouse=True)
def _hash_rapido(monkeypatch):
    monkeypatch.setattr(auth, "ITERACIONES", 1_000)


@pytest.fixture()
def usuarios(repos):
    return repos.usuarios


@pytest.fixture()
def admin(usuarios):
    usuario = Usuario(usuario="jorge", nombre="Jorge Páquez",
                      rol=RolUsuario.ADMINISTRADOR)
    usuario.codigo = usuarios.crear(usuario, CLAVE)  # type: ignore[attr-defined]
    return usuario


# -- dominio ----------------------------------------------------------------- #


def test_el_hash_no_contiene_la_password_y_verifica():
    almacenado = auth.hash_password(CLAVE)
    assert CLAVE not in almacenado
    assert almacenado != auth.hash_password(CLAVE)  # sal distinta en cada hash
    assert auth.verificar_password(CLAVE, almacenado)
    assert not auth.verificar_password(CLAVE + "x", almacenado)
    assert not auth.verificar_password(CLAVE, "basura")


@pytest.mark.parametrize("debil", ["", "corta1", "sololetras", "12345678"])
def test_password_debil_se_rechaza(debil):
    with pytest.raises(DatosInvalidosError):
        auth.validar_password(debil)


def test_password_temporal_cumple_la_politica():
    auth.validar_password(auth.generar_password_temporal())


# -- alta e ingreso ---------------------------------------------------------- #


def test_base_nueva_no_tiene_usuarios(usuarios):
    assert not usuarios.hay_usuarios()


def test_crear_e_ingresar(usuarios, admin):
    assert usuarios.hay_usuarios()
    ingresado = usuarios.autenticar("JORGE", CLAVE)  # usuario sin distinguir mayúsculas
    assert ingresado.id == admin.id
    assert ingresado.es_admin
    assert ingresado.ultimo_acceso is not None


def test_la_password_no_se_guarda_en_texto_plano(usuarios, admin):
    fila = usuarios.conn.execute("SELECT * FROM usuarios").fetchone()
    assert CLAVE not in fila["password_hash"]
    assert admin.codigo.replace("-", "") not in fila["codigo_hash"]


def test_usuario_duplicado(usuarios, admin):
    with pytest.raises(DatosInvalidosError):
        usuarios.crear(Usuario(usuario="Jorge"), CLAVE)


def test_credenciales_incorrectas(usuarios, admin):
    with pytest.raises(CredencialesInvalidasError):
        usuarios.autenticar("jorge", "otraclave1")
    with pytest.raises(CredencialesInvalidasError):
        usuarios.autenticar("nadie", CLAVE)


def test_bloqueo_tras_intentos_fallidos_y_desbloqueo(usuarios, admin):
    ahora = datetime(2026, 10, 4, 10, 0, 0)
    for _ in range(auth.MAX_INTENTOS):
        with pytest.raises(CredencialesInvalidasError):
            usuarios.autenticar("jorge", "incorrecta1", ahora=ahora)
    with pytest.raises(CuentaBloqueadaError):
        usuarios.autenticar("jorge", CLAVE, ahora=ahora)
    despues = ahora + timedelta(minutes=auth.MINUTOS_BLOQUEO, seconds=1)
    assert usuarios.autenticar("jorge", CLAVE, ahora=despues).id == admin.id


def test_cuenta_desactivada_no_ingresa(usuarios, admin):
    operador = Usuario(usuario="marina")
    usuarios.crear(operador, CLAVE)
    operador.activo = False
    usuarios.actualizar(operador)
    with pytest.raises(CredencialesInvalidasError):
        usuarios.autenticar("marina", CLAVE)


# -- contraseñas y recuperación ---------------------------------------------- #


def test_cambiar_password(usuarios, admin):
    with pytest.raises(CredencialesInvalidasError):
        usuarios.cambiar_password(admin.id, "incorrecta1", "nuevaclave9")
    usuarios.cambiar_password(admin.id, CLAVE, "nuevaclave9")
    assert usuarios.autenticar("jorge", "nuevaclave9")
    with pytest.raises(CredencialesInvalidasError):
        usuarios.autenticar("jorge", CLAVE)


def test_recuperar_con_codigo_es_de_un_solo_uso(usuarios, admin):
    codigo_tipeado = admin.codigo.lower().replace("-", " ")
    nuevo = usuarios.restablecer_con_codigo("jorge", codigo_tipeado, "recuperada7")
    assert usuarios.autenticar("jorge", "recuperada7")
    assert nuevo != admin.codigo
    with pytest.raises(CredencialesInvalidasError):
        usuarios.restablecer_con_codigo("jorge", admin.codigo, "otraclave8")
    usuarios.restablecer_con_codigo("jorge", nuevo, "otraclave8")
    assert usuarios.autenticar("jorge", "otraclave8")


def test_recuperar_con_codigo_incorrecto_no_cambia_nada(usuarios, admin):
    with pytest.raises(CredencialesInvalidasError):
        usuarios.restablecer_con_codigo("jorge", "AAAA-BBBB-CCCC-DDDD", "recuperada7")
    assert usuarios.autenticar("jorge", CLAVE)


def test_recuperar_desbloquea_la_cuenta(usuarios, admin):
    ahora = datetime(2026, 10, 4, 10, 0, 0)
    for _ in range(auth.MAX_INTENTOS - 1):
        with pytest.raises(CredencialesInvalidasError):
            usuarios.autenticar("jorge", "incorrecta1", ahora=ahora)
    usuarios.restablecer_con_codigo("jorge", admin.codigo, "recuperada7", ahora=ahora)
    with pytest.raises(CredencialesInvalidasError):
        usuarios.autenticar("jorge", "incorrecta1", ahora=ahora)
    assert usuarios.autenticar("jorge", "recuperada7", ahora=ahora)


def test_regenerar_codigo_anula_el_anterior(usuarios, admin):
    with pytest.raises(CredencialesInvalidasError):
        usuarios.regenerar_codigo(admin.id, "incorrecta1")
    nuevo = usuarios.regenerar_codigo(admin.id, CLAVE)
    with pytest.raises(CredencialesInvalidasError):
        usuarios.restablecer_con_codigo("jorge", admin.codigo, "recuperada7")
    usuarios.restablecer_con_codigo("jorge", nuevo, "recuperada7")


def test_restablecer_por_admin_obliga_a_cambiar(usuarios, admin):
    operador = Usuario(usuario="marina")
    usuarios.crear(operador, CLAVE)
    temporal = usuarios.restablecer_por_admin(operador.id)
    ingresado = usuarios.autenticar("marina", temporal)
    assert ingresado.debe_cambiar_password
    usuarios.definir_password(operador.id, "definitiva5")
    assert not usuarios.autenticar("marina", "definitiva5").debe_cambiar_password


# -- administración ---------------------------------------------------------- #


def test_siempre_queda_un_administrador_activo(usuarios, admin):
    with pytest.raises(EliminacionRestringidaError):
        usuarios.eliminar(admin.id)
    admin.rol = RolUsuario.USUARIO
    with pytest.raises(EliminacionRestringidaError):
        usuarios.actualizar(admin)
    admin.rol, admin.activo = RolUsuario.ADMINISTRADOR, False
    with pytest.raises(EliminacionRestringidaError):
        usuarios.actualizar(admin)

    otro = Usuario(usuario="marina", rol=RolUsuario.ADMINISTRADOR)
    usuarios.crear(otro, CLAVE)
    usuarios.eliminar(admin.id)
    assert [u.usuario for u in usuarios.listar()] == ["marina"]


def test_nombre_de_usuario_invalido(usuarios):
    for nombre in ("", "ab", "con espacio"):
        with pytest.raises(DatosInvalidosError):
            usuarios.crear(Usuario(usuario=nombre), CLAVE)
