-- Fotique — Esquema SQLite (offline-first)
-- Idempotente: se ejecuta con IF NOT EXISTS en cada arranque.

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------------- #
-- Módulo B — Fotógrafos / Personal
-- --------------------------------------------------------------------------- #
CREATE TABLE IF NOT EXISTS fotografos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL,
    apellido    TEXT    NOT NULL DEFAULT '',
    telefono    TEXT    NOT NULL DEFAULT '',
    email       TEXT    NOT NULL DEFAULT '',
    activo      INTEGER NOT NULL DEFAULT 1,
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- --------------------------------------------------------------------------- #
-- Módulo A — Inventario
-- --------------------------------------------------------------------------- #
CREATE TABLE IF NOT EXISTS equipos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_serie        TEXT    UNIQUE,
    marca               TEXT    NOT NULL,
    modelo              TEXT    NOT NULL,
    fecha_adquisicion   TEXT,
    fecha_service_ultimo TEXT,
    fecha_service_proximo TEXT,
    estado              TEXT    NOT NULL DEFAULT 'En stock'
                            CHECK (estado IN ('En stock', 'En uso')),
    fotografo_id        INTEGER REFERENCES fotografos (id) ON DELETE RESTRICT,
    notas               TEXT    NOT NULL DEFAULT '',
    categoria           TEXT    NOT NULL DEFAULT '',
    -- Si está "En uso" el fotógrafo responsable es obligatorio.
    CHECK (estado = 'En stock' OR fotografo_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS categorias_equipo (
    nombre TEXT PRIMARY KEY COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS historial_asignaciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id        INTEGER NOT NULL REFERENCES equipos (id) ON DELETE CASCADE,
    fotografo_id     INTEGER REFERENCES fotografos (id) ON DELETE SET NULL,
    fecha_asignacion TEXT    NOT NULL,
    fecha_devolucion TEXT,
    observaciones    TEXT    NOT NULL DEFAULT '',
    proyecto_id      INTEGER REFERENCES proyectos (id) ON DELETE SET NULL,
    fecha_prevista   TEXT
);

-- --------------------------------------------------------------------------- #
-- Módulo C — Clientes y Proyectos
-- --------------------------------------------------------------------------- #
CREATE TABLE IF NOT EXISTS clientes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    responsable TEXT NOT NULL DEFAULT '',
    telefono    TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL DEFAULT '',
    direccion   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS proyectos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo       TEXT    NOT NULL DEFAULT '',
    cliente_id   INTEGER NOT NULL REFERENCES clientes (id) ON DELETE RESTRICT,
    fotografo_id INTEGER REFERENCES fotografos (id) ON DELETE SET NULL,
    fecha_evento TEXT,
    estado       TEXT    NOT NULL DEFAULT 'Presupuesto'
                    CHECK (estado IN ('Presupuesto', 'Confirmado', 'En curso', 'Cerrado')),
    cobro_total  REAL    NOT NULL DEFAULT 0,
    sena_monto   REAL    NOT NULL DEFAULT 0,
    sena_fecha   TEXT,
    sena_medio   TEXT    NOT NULL DEFAULT '',
    direccion    TEXT    NOT NULL DEFAULT '',
    notas        TEXT    NOT NULL DEFAULT '',
    creado_en    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    tipo         TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS pagos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos (id) ON DELETE CASCADE,
    monto       REAL    NOT NULL CHECK (monto > 0),
    fecha       TEXT    NOT NULL,
    medio       TEXT    NOT NULL DEFAULT 'Efectivo',
    notas       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS egresos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT    NOT NULL,
    concepto    TEXT    NOT NULL,
    categoria   TEXT    NOT NULL DEFAULT 'Otros',
    monto       REAL    NOT NULL CHECK (monto > 0),
    proyecto_id INTEGER REFERENCES proyectos (id) ON DELETE SET NULL,
    notas       TEXT    NOT NULL DEFAULT ''
);

-- --------------------------------------------------------------------------- #
-- Módulo D — Contratos y tarifario
-- --------------------------------------------------------------------------- #
CREATE TABLE IF NOT EXISTS plantillas_contrato (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre   TEXT NOT NULL,
    contenido TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS contratos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    proyecto_id INTEGER REFERENCES proyectos (id) ON DELETE CASCADE,
    plantilla_id INTEGER REFERENCES plantillas_contrato (id) ON DELETE SET NULL,
    contenido   TEXT NOT NULL DEFAULT '',
    estado      TEXT NOT NULL DEFAULT 'Borrador',
    fecha       TEXT
);

CREATE TABLE IF NOT EXISTS servicios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'Otros',
    precio    REAL NOT NULL DEFAULT 0,
    unidad    TEXT NOT NULL DEFAULT 'servicio',
    activo    INTEGER NOT NULL DEFAULT 1,
    notas     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS categorias_servicio (
    nombre TEXT PRIMARY KEY COLLATE NOCASE
);

-- --------------------------------------------------------------------------- #
-- Entregas y calendario
-- --------------------------------------------------------------------------- #
CREATE TABLE IF NOT EXISTS trabajos_pendientes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo        TEXT    NOT NULL,
    descripcion   TEXT    NOT NULL DEFAULT '',
    fotografo_id  INTEGER NOT NULL REFERENCES fotografos (id) ON DELETE RESTRICT,
    proyecto_id   INTEGER REFERENCES proyectos (id) ON DELETE SET NULL,
    fecha_entrega TEXT,
    estado        TEXT    NOT NULL DEFAULT 'Pendiente'
                    CHECK (estado IN ('Pendiente', 'En edición', 'Entregado', 'Cancelado')),
    rol           TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS eventos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo       TEXT NOT NULL,
    fecha        TEXT NOT NULL,
    hora         TEXT NOT NULL DEFAULT '',
    tipo         TEXT NOT NULL DEFAULT 'Sesión'
                    CHECK (tipo IN ('Sesión', 'Entrega', 'Service', 'Reunión', 'Otro')),
    fotografo_id INTEGER REFERENCES fotografos (id) ON DELETE CASCADE,
    proyecto_id  INTEGER REFERENCES proyectos (id) ON DELETE SET NULL,
    notas        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL DEFAULT ''
);

-- --------------------------------------------------------------------------- #
-- Acceso — usuarios de la aplicación
-- --------------------------------------------------------------------------- #
-- password_hash y codigo_hash guardan derivaciones PBKDF2, nunca texto plano.
CREATE TABLE IF NOT EXISTS usuarios (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario            TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    nombre             TEXT    NOT NULL DEFAULT '',
    email              TEXT    NOT NULL DEFAULT '',
    rol                TEXT    NOT NULL DEFAULT 'Usuario'
                           CHECK (rol IN ('Administrador', 'Usuario')),
    password_hash      TEXT    NOT NULL,
    codigo_hash        TEXT    NOT NULL DEFAULT '',
    activo             INTEGER NOT NULL DEFAULT 1,
    debe_cambiar       INTEGER NOT NULL DEFAULT 0,
    intentos_fallidos  INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta    TEXT,
    ultimo_acceso      TEXT,
    creado_en          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    fotografo_id       INTEGER REFERENCES fotografos (id) ON DELETE SET NULL
);

-- Índices de los listados y filtros más usados
CREATE INDEX IF NOT EXISTS idx_equipos_estado      ON equipos (estado);
CREATE INDEX IF NOT EXISTS idx_equipos_fotografo   ON equipos (fotografo_id);
CREATE INDEX IF NOT EXISTS idx_equipos_service     ON equipos (fecha_service_proximo);
CREATE INDEX IF NOT EXISTS idx_hist_equipo         ON historial_asignaciones (equipo_id);
CREATE INDEX IF NOT EXISTS idx_proyectos_cliente   ON proyectos (cliente_id);
CREATE INDEX IF NOT EXISTS idx_proyectos_fecha     ON proyectos (fecha_evento);
CREATE INDEX IF NOT EXISTS idx_pagos_proyecto      ON pagos (proyecto_id);
CREATE INDEX IF NOT EXISTS idx_trabajos_fotografo  ON trabajos_pendientes (fotografo_id);
CREATE INDEX IF NOT EXISTS idx_trabajos_estado     ON trabajos_pendientes (estado);
CREATE INDEX IF NOT EXISTS idx_trabajos_entrega    ON trabajos_pendientes (fecha_entrega);
CREATE INDEX IF NOT EXISTS idx_eventos_fecha       ON eventos (fecha);
CREATE INDEX IF NOT EXISTS idx_contratos_proyecto  ON contratos (proyecto_id);
CREATE INDEX IF NOT EXISTS idx_pagos_fecha         ON pagos (fecha);
CREATE INDEX IF NOT EXISTS idx_egresos_fecha       ON egresos (fecha);
CREATE INDEX IF NOT EXISTS idx_hist_fecha          ON historial_asignaciones (fecha_asignacion);
