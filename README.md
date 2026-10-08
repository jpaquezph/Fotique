# Fotique

**Sistema integral de gestión fotográfica** para escritorio: inventario de equipos,
personal, clientes y proyectos, calendario del estudio, tarifario, contratos y
respaldos. 100% *offline-first* (SQLite local), sin servidores ni internet.

Documento de partida: [`Relevamiento Fotique.md`](Relevamiento%20Fotique.md) (SRS v2.0).

**Repositorio:** <https://github.com/jpaquezph/Fotique>

| Referencia | Contenido |
|---|---|
| `main` | Última actualización disponible. |
| `dev` | Misma punta que `main`. |
| `v1.0` | Tag de la versión 1.0.0, cerrada el 01/10/2026. |
| `v1.2` | Tag de la versión 1.2.0 (04/10/2026). |
| `v1.3` | Tag de la versión 1.3.0 (05/10/2026). |
| `v1.4` | Tag de la versión 1.4.0 (08/10/2026). |
| `1.2`, `1.3`, … | Una rama por versión, con los cambios de esa versión. `1.5` es la que está en desarrollo. |

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
python main.py D:\datos\fotique.db
```

Si no se indica nada, la base vive en:

| Sistema   | Ruta                                              |
|-----------|---------------------------------------------------|
| Windows   | `%APPDATA%\Fotique\fotique.db`                        |
| macOS     | `~/Library/Application Support/Fotique/fotique.db`    |
| Linux     | `~/.local/share/fotique/fotique.db`                   |

Variables útiles: `FOTIQUE_DB` (ruta de la base), `FOTIQUE_DATA_DIR` (carpeta de datos).

La aplicación **arranca en blanco**: no se cargan datos de ejemplo. El estudio
de muestra vive en `tests/datos_demo.py`, sólo para las pruebas y los scripts;
no forma parte del ejecutable.

## Acceso y usuarios

La aplicación pide iniciar sesión. La primera vez que se abre una base sin
usuarios se crea la cuenta de **administrador**; el resto de las cuentas se dan
de alta desde la sección **Usuarios** (sólo visible para administradores).

- **Recuperar la contraseña:** cada cuenta recibe al crearse un *código de
  recuperación* de un solo uso (`XXXX-XXXX-XXXX-XXXX`). Con «¿Olvidó su
  contraseña?» ese código permite elegir una nueva y entrega un código nuevo.
  Se puede regenerar desde **Mi cuenta**.
- **Sin código:** un administrador restablece la contraseña desde **Usuarios**;
  se genera una provisoria que el usuario debe cambiar al ingresar.
- **Bloqueo:** 5 intentos fallidos bloquean la cuenta 5 minutos.
- **Roles:** `Administrador` y `Usuario`. Sólo los administradores ven
  **Usuarios** y **Resumen general**, eliminan equipos y restauran respaldos.
- **Fotógrafos:** al dar de alta uno, el administrador elige su rol y se crea
  su cuenta con una contraseña provisoria.

Las contraseñas y los códigos se guardan sólo como hash (PBKDF2-HMAC-SHA256).
El inicio de sesión controla el acceso a la aplicación; el archivo `fotique.db`
no está cifrado, así que quien pueda leerlo desde fuera de Fotique puede ver los
datos del estudio.

## Tests (TDD)

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Pirámide de testing del SRS §4:

1. **Unitarias** — `tests/test_dominio_equipos.py`, `tests/test_dominio_comercial.py`
   (asignación de equipos, saldos, validaciones, alertas de service).
2. **Integración (SQLite `:memory:`)** — `tests/test_repositorios.py`
   (historial, restricciones de borrado, calendario consolidado, respaldos).
3. **GUI** — `tests/test_ui.py` (ventanas, diálogos, formularios, pantalla de acceso).

El acceso tiene su propia suite en `tests/test_usuarios.py` (hash, ingreso,
bloqueo, recuperación y reglas de administración) y lo propio de la 1.2
en `tests/test_v12.py` (migración, cobros, roles, egresos e informes).

Smoke manual (no requiere pytest):

```powershell
python scripts\smoke_ui.py
python scripts\smoke_dialogos.py
```

## Generar el ejecutable

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean fotique.spec
```

`fotique.spec` ya está configurado en modo *onefile*: el resultado es un único
**`dist\Fotique.exe`** autocontenido (incluye el esquema `schema.sql`). Se puede
copiar a cualquier PC con Windows, sin instalar Python.

Si preferís una carpeta con el ejecutable (arranque más rápido y menos
falsos positivos de antivirus), cambiá el `EXE(...)` final del spec por el modo
*onedir* con `COLLECT`, o usá:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir `
    --name Fotique --add-data "fotique\db\schema.sql;fotique\db" main.py
```

---

## Módulos

| Módulo | Qué hace | Dónde |
|---|---|---|
| Inventario | Ficha de cada equipo, asignación con proyecto y fechas, historial de movimientos, alertas de service | `fotique/ui/views/equipos.py` |
| Fotógrafos | Personal, equipos tomados, trabajos con rol, historial de entregas | `fotique/ui/views/fotografos.py` |
| Clientes y proyectos | Tipo de proyecto, seña, cobros con tope en el total, saldo automático | `fotique/ui/views/proyectos.py` |
| Calendario, tarifario y contratos | Agenda unificada, precios, contratos desde plantillas | `fotique/ui/views/{calendario,servicios,contratos}.py` |
| Resumen general | Dinero, equipos, personal, clientes y contratos por período, con gráficos | `fotique/ui/views/resumen.py` |
| Configuración y usuarios | Mi cuenta, apariencia, versión, respaldo y restauración de la base; cuentas y roles | `fotique/ui/views/{configuracion,respaldos,usuarios}.py` |

### Estructura

```
Fotique/
├── main.py                  # lanzador
├── fotique.spec               # PyInstaller
├── fotique/
│   ├── app.py               # composición: base de datos + ventana
│   ├── util.py              # fechas, moneda, rutas
│   ├── domain/              # modelos y reglas de negocio (sin Qt ni SQLite)
│   │   ├── models.py        # Equipo, Fotografo, Proyecto, …
│   │   ├── services.py      # asignaciones, saldos, generación de contratos
│   │   ├── auth.py          # hash de contraseñas y códigos de recuperación
│   │   └── errors.py        # excepciones de negocio
│   ├── db/
│   │   ├── schema.sql       # esquema SQLite (RF + índices)
│   │   ├── connection.py    # conexión, integridad, respaldos
│   │   └── repositories.py  # CRUD + consultas
│   └── ui/
│       ├── theme.py         # paleta (pares claro/oscuro) y estilos ttk
│       ├── acceso.py        # pantalla de ingreso, primer usuario y recuperación
│       ├── fechas.py        # selector de fecha con calendario
│       ├── graficos.py      # gráfico de torta
│       ├── widgets.py       # Tabla, diálogos, campos, conversiones
│       ├── dialogs.py       # todos los formularios modales
│       ├── ventana_principal.py
│       └── views/           # una vista por módulo
├── tests/                   # pytest (unidad + integración + GUI)
└── scripts/                 # smoke tests de UI
```

### Convenciones

- **Reglas de negocio** siempre en `fotique/domain` (testeadas sin UI ni BD).
- **La capa de datos** traduce filas ⇄ objetos; nunca se filtra SQL a la UI.
- **Errores de negocio** derivan de `FotiqueError` y se muestran en un diálogo
  (`ejecutar_protegido`).
- Fechas en ISO (`YYYY-MM-DD`) en la base, `dd/mm/aaaa` en la interfaz.
- Importes en `REAL`; el formato local (`$ 1.500.000,00`) lo hace `moneda()`.
