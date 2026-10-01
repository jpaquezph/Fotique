# Changelog

Todo lo notable de Fotia se documenta acá.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

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
