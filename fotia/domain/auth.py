"""Credenciales de usuario: hash de contraseñas y códigos de recuperación.

Sin SQLite ni UI. Las contraseñas nunca se guardan: sólo su derivación
PBKDF2-HMAC-SHA256 con sal propia, en el formato
``pbkdf2_sha256$<iteraciones>$<sal hex>$<hash hex>``.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import unicodedata

from .errors import DatosInvalidosError

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000
LARGO_MINIMO = 8

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 5

# Sin 0/O ni 1/I/L: el código se copia a mano desde un papel.
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_ALFABETO_TEMPORAL = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"


def hash_password(password: str, *, iteraciones: int | None = None) -> str:
    iteraciones = iteraciones or ITERACIONES
    sal = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, iteraciones)
    return f"{ALGORITMO}${iteraciones}${sal.hex()}${derivado.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = almacenado.split("$")
        if algoritmo != ALGORITMO:
            return False
        derivado = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(sal), int(iteraciones)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(derivado.hex(), esperado)


def validar_password(password: str) -> None:
    if len(password) < LARGO_MINIMO:
        raise DatosInvalidosError(
            f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres."
        )
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise DatosInvalidosError("La contraseña debe combinar letras y números.")


def generar_codigo_recuperacion() -> str:
    """Código de un solo uso, p. ej. ``K7MQ-2XWP-9RTD-HB4N`` (~79 bits)."""
    grupos = [
        "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(4)) for _ in range(4)
    ]
    return "-".join(grupos)


def normalizar_codigo(codigo: str) -> str:
    """Tolera minúsculas, espacios y guiones al tipear el código."""
    return "".join(c for c in (codigo or "").upper() if c.isalnum())


def generar_password_temporal() -> str:
    """Contraseña provisoria que cumple :func:`validar_password`."""
    while True:
        candidata = "".join(secrets.choice(_ALFABETO_TEMPORAL) for _ in range(10))
        if any(c.isalpha() for c in candidata) and any(c.isdigit() for c in candidata):
            return candidata


def sugerir_usuario(nombre: str, apellido: str = "") -> str:
    """``Tomás`` + ``Benítez`` ➜ ``tomas.benitez`` (sin acentos ni espacios)."""
    partes = []
    for parte in (nombre, apellido):
        plano = unicodedata.normalize("NFKD", parte or "")
        limpio = "".join(c for c in plano.lower() if c.isascii() and c.isalnum())
        if limpio:
            partes.append(limpio)
    return ".".join(partes).ljust(3, "0") if partes else "usuario"
