from __future__ import annotations

import pytest

from fotia.db import BaseDatos


@pytest.fixture()
def db() -> BaseDatos:
    """Base SQLite en memoria con el esquema completo (RNF-04)."""
    base = BaseDatos(":memory:")
    yield base
    base.cerrar()


@pytest.fixture()
def repos(db: BaseDatos):
    return db.repos
