# Fotia

**Sistema integral de gestión fotográfica** para escritorio: inventario de equipos,
personal, clientes y proyectos, calendario del estudio, tarifario, contratos y
respaldos. 100% *offline-first* (SQLite local), sin servidores ni internet.

Documento de partida: [`Relevamiento Fotia.md`](Relevamiento%20Fotia.md) (SRS v2.0).

**Repositorio:** <https://github.com/jpaquezph/Fotia>

| Referencia | Contenido |
|---|---|
| `main` | Última versión estable (siempre actualizada). |
| `dev` | Misma punta que `main`: rama de desarrollo para próximos cambios. |
| `v1.0` | Tag de la versión 1.0.0, cerrada el 01/10/2026. |

---

## Requisitos

- Python 3.11 o superior
- `pip install -r requirements.txt` (solo CustomTkinter, todo lo demás es estándar)

## Ejecutar desde el código

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

Opcional: pasar una ruta de base de datos distinta

```powershell
python main.py D:\datos\fotia.db
```

Si no se indica nada, la base vive en:

| Sistema   | Ruta                                              |
|-----------|---------------------------------------------------|
| Windows   | `%APPDATA%\Fotia\fotia.db`                        |
| macOS     | `~/Library/Application Support/Fotia/fotia.db`    |
| Linux     | `~/.local/share/fotia/fotia.db`                   |

Variables útiles: `FOTIA_DB` (ruta de la base), `FOTIA_DATA_DIR` (carpeta de datos).

En la **primera ejecución** se carga un conjunto de datos de ejemplo para poder
recorrer la aplicación; a partir de ahí nunca se vuelve a sembrar solo.

## Tests (TDD)

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Pirámide de testing del SRS §4:

1. **Unitarias** — `tests/test_dominio_equipos.py`, `tests/test_dominio_comercial.py`
   (asignación de equipos, saldos, validaciones, alertas de service).
2. **Integración (SQLite `:memory:`)** — `tests/test_repositorios.py`
   (historial, restricciones de borrado, calendario consolidado, respaldos).
3. **GUI** — `tests/test_ui.py` (ventanas, diálogos, formularios).

Smoke manual (no requiere pytest):

```powershell
python scripts\smoke_ui.py
python scripts\smoke_dialogos.py
```

## Generar el ejecutable

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean fotia.spec
```

`fotia.spec` ya está configurado en modo *onefile*: el resultado es un único
**`dist\Fotia.exe`** autocontenido (incluye el esquema `schema.sql`). Se puede
copiar a cualquier PC con Windows, sin instalar Python.

Si preferís una carpeta con el ejecutable (arranque más rápido y menos
falsos positivos de antivirus), cambiá el `EXE(...)` final del spec por el modo
*onedir* con `COLLECT`, o usá:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir `
    --name Fotia --add-data "fotia\db\schema.sql;fotia\db" main.py
```

---

## Módulos y requisitos cubiertos

| Módulo | Requisitos | Dónde |
|---|---|---|
| A · Inventario | RF-01 ficha, RF-02 trazabilidad/historial, RF-03 alertas de service | `fotia/ui/views/equipos.py`, `fotia/db/repositories.py` |
| B · Fotógrafos | RF-04 registro, equipos tomados, entregas pendientes | `fotia/ui/views/fotografos.py` |
| C · Clientes y proyectos | RF-05 seña, cobros, saldo automático | `fotia/ui/views/proyectos.py` |
| D · Generales | RF-06 contratos con plantillas, RF-07 tarifario, RF-08 calendario unificado | `fotia/ui/views/{contratos,servicios,calendario}.py` |
| RNF | RNF-01 Python, RNF-02 SQLite offline, RNF-03 listados en SQL, RNF-04 integridad, RNF-05 respaldos | `fotia/db/`, `fotia/domain/` |

### Estructura

```
Fotia/
├── main.py                  # lanzador
├── fotia.spec               # PyInstaller
├── fotia/
│   ├── app.py               # composición: base de datos + ventana
│   ├── util.py              # fechas, moneda, rutas
│   ├── domain/              # modelos y reglas de negocio (sin Qt ni SQLite)
│   │   ├── models.py        # Equipo, Fotografo, Proyecto, …
│   │   ├── services.py      # asignaciones, saldos, generación de contratos
│   │   └── errors.py        # excepciones de negocio
│   ├── db/
│   │   ├── schema.sql       # esquema SQLite (RF + índices)
│   │   ├── connection.py    # conexión, integridad, respaldos (RNF-05)
│   │   ├── repositories.py  # CRUD + consultas
│   │   └── seed.py          # datos de ejemplo
│   └── ui/
│       ├── theme.py         # paleta y estilos ttk
│       ├── widgets.py       # Tabla, diálogos, campos, conversiones
│       ├── dialogs.py       # todos los formularios modales
│       ├── ventana_principal.py
│       └── views/           # una vista por módulo
├── tests/                   # pytest (unidad + integración + GUI)
└── scripts/                 # smoke tests de UI
```

### Convenciones

- **Reglas de negocio** siempre en `fotia/domain` (testeadas sin UI ni BD).
- **La capa de datos** traduce filas ⇄ objetos; nunca se filtra SQL a la UI.
- **Errores de negocio** derivan de `FotiaError` y se muestran en un diálogo
  (`ejecutar_protegido`).
- Fechas en ISO (`YYYY-MM-DD`) en la base, `dd/mm/aaaa` en la interfaz.
- Importes en `REAL`; el formato local (`$ 1.500.000,00`) lo hace `moneda()`.
