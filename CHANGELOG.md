# Changelog

Todo lo notable de Fotia se documenta acá.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [1.1.0] — 2026-10-04

### Agregado

- **Acceso con usuario y contraseña.** Al abrir una base sin usuarios se crea
  la cuenta de administrador; después se ingresa con usuario y contraseña.
  - Contraseñas guardadas sólo como hash PBKDF2-HMAC-SHA256 con sal propia.
  - Bloqueo de 5 minutos tras 5 intentos fallidos.
  - Recuperación con un código de un solo uso que se entrega al crear la
    cuenta (y se puede regenerar desde «Mi cuenta»), o por restablecimiento de
    un administrador con contraseña provisoria de cambio obligatorio.
  - Roles `Administrador` y `Operador`; sólo los administradores ven la sección
    «Usuarios» y pueden restaurar respaldos. Siempre queda al menos un
    administrador activo.
  - «Mi cuenta» (datos, cambio de contraseña) y «Cerrar sesión».

### Cambiado

- **Rendimiento.** Las vistas se construyen cuando se abren (y el resto se
  precarga con la ventana ya visible) en lugar de armarse todas al arrancar; el
  panel reutiliza sus filas; el calendario sólo redibuja las celdas que
  cambian y ya no consulta la base por cada fila; las búsquedas esperan a que
  se deje de tipear; al redimensionar sólo se recalcula la vista activa.
- **Apariencia.** Paleta única en pares claro/oscuro: el texto y los controles
  cambian solos con el modo (antes quedaban con los colores del arranque),
  botones en tonos apagados en modo oscuro y tablas, tarjetas, paneles y campos
  con el mismo fondo que la ventana.

## [1.0.0] — 2026-10-01

Primera versión cerrada, alineada al SRS «Relevamiento Fotia» v2.0.

### Agregado

- **Módulo A — Inventario (RF-01, RF-02, RF-03)**
  - Ficha de equipo con número de serie, marca, modelo, adquisición, service
    (último/próximo), estado `En stock`/`En uso`, fotógrafo responsable y notas.
  - Asignación a fotógrafo con registro en `historial_asignaciones` y devolución
    al stock; historial por equipo y global.
  - Alertas visuales de service vencido o próximo (30 días).
- **Módulo B — Fotógrafos (RF-04)**
  - ABM de personal con contacto, equipos tomados del stock, entregas y estados
    (`Pendiente`, `En edición`, `Entregado`).
  - Borrado restringido con equipos tomados o entregas activas (RNF-04).
- **Módulo C — Clientes y proyectos (RF-05)**
  - Clientes con responsable, contacto y dirección/locación.
  - Proyectos con fecha de evento, estado, fotógrafo, seña (monto/fecha/medio),
    pagos parciales y saldo calculado automáticamente.
  - Ficha financiera por proyecto con detalle de pagos.
- **Módulo D — Generales (RF-06, RF-07, RF-08)**
  - Contratos a partir de plantillas con variables (`{{cliente}}`, `{{saldo}}`,
    `{{fecha_evento}}`, …) vinculados a cada proyecto.
  - Tarifario configurable por categoría (coberturas, sesiones, edición,
    fotolibros, viáticos, personal).
  - Calendario general que unifica eventos de proyectos, entregas, service y
    agenda propia, con filtro por fotógrafo y vista mensual.
- **Requisitos no funcionales**
  - RNF-01 Python puro con CustomTkinter.
  - RNF-02 base SQLite embebida, funciona sin internet.
  - RNF-03 consultas resueltas en SQL con índices (listados ≤ 150 ms).
  - RNF-04 validaciones de integridad tanto en dominio como en el esquema.
  - RNF-05 creación y restauración de respaldos con `PRAGMA integrity_check`.
- Suite de tests: 51 pruebas (`pytest`) en tres niveles: unidad, integración
  SQLite en memoria y GUI; más smoke scripts de ventana y diálogos.
- Empaquetado con PyInstaller (`fotia.spec` → `dist\Fotia.exe`).

### Notas de la primera ejecución

- Se crea la base en `%APPDATA%\Fotia\fotia.db` (ver `fotia/util.py`).
- Si la base está vacía se cargan datos de ejemplo una única vez.
