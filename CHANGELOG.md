# Changelog

Todo lo notable de Fotique se documenta acá.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [1.5.0] — en desarrollo

### Agregado

- **Producto de los equipos**: nueva columna «Producto» en el inventario y
  campo en la ficha de cada equipo, para anotar qué es (cámara, lente,
  flash…). Es opcional y la búsqueda también encuentra por producto.

## [1.4.0] — 2026-10-08

### Agregado

- **Logo de Fotique** en la barra lateral y en la pantalla de ingreso (negro en
  modo claro, blanco en modo oscuro) e **ícono propio** en las ventanas, la
  barra de tareas y el ejecutable.
- **Categoría de los equipos**: nueva columna en el inventario y campo en la
  ficha de cada equipo. La lista arranca con Cámara, Iluminación, Accesorio,
  Mantenimiento y Filtros, y se amplía o recorta con el botón «Categorías»
  del inventario o con «Agregar / quitar» en la misma ficha del equipo;
  la búsqueda también encuentra por categoría.

### Cambiado

- **La aplicación pasa a llamarse Fotique** (antes Fotia): paquete `fotique`,
  ejecutable `Fotique.exe`, variables `FOTIQUE_DB` y `FOTIQUE_DATA_DIR`. La
  carpeta de datos anterior (`%APPDATA%\Fotia\fotia.db`) se renombra sola a
  `%APPDATA%\Fotique\fotique.db` en el primer arranque.
- **Calendario de fechas**: la grilla de años va de 2010 a 2033 en una sola
  página (antes mostraba 12 años y había que retroceder para llegar a 2010).
- **La aplicación arranca en blanco**: ya no se cargan datos de ejemplo en la
  primera ejecución ni cuando la base queda vacía. El estudio de muestra pasa
  a `tests/datos_demo.py` y deja de viajar en el ejecutable.
- El texto bajo el logo pasa a «FOTIQUE · GESTIÓN PROFESIONAL».

### Corregido

- El logo se vuelve a leer si Tk falla al decodificar el PNG (error esporádico
  y sin mensaje); antes ese fallo podía cortar la pantalla de ingreso.

## [1.3.0] — 2026-10-05

### Agregado

- **Eventos desde el calendario**: doble clic en un día abre «Nuevo evento»
  con esa fecha ya cargada.
- **Historial de movimientos de equipos** con filtros por equipo, fotógrafo y
  rango de fechas de retiro (elegidas del calendario). El doble clic sobre un
  equipo lo abre ya filtrado por esa unidad.
- **Cambiar de usuario** desde el pie de la barra lateral: vuelve a la
  pantalla de ingreso.

### Cambiado

- **Nueva apariencia**: paleta en tinta oscura con acento violeta, barra
  lateral oscura también en modo claro, logo «fotique.», botones con forma de
  píldora y tonos suaves (relleno pleno sólo para la acción principal),
  títulos más grandes y tarjetas y tablas que se despegan del fondo.
- Tarjetas del panel de control en una gama fría armónica; «Saldo a cobrar»
  en verde.
- Tarjetas del resumen general sólidas con texto blanco; «Resultado» pasa a
  rojo cuando los egresos superan a los ingresos.
- En clientes y proyectos el color de la fila indica el estado: verde
  (confirmado o en curso), amarillo (presupuesto) y rojo (cerrado). La barra
  de acciones entra completa en pantalla.
- Tarifario agrupado por categoría, con filas más altas y alternadas.
- Gráficos de torta con bordes suavizados.

### Quitado

- «Historial global» del inventario: lo reemplaza «Historial».

## [1.2.0] — 2026-10-04

### Agregado

- **Resumen general** (sólo administradores): ingresos, egresos y movimientos
  de dinero; salidas por equipo; eventos y trabajos por fotógrafo; roles
  cubiertos; movimientos por cliente; proyectos y contratos por estado. Con
  filtro de período, secciones y gráficos de torta. Incluye el registro de
  **egresos**.
- **Calendario para elegir fechas** en todos los formularios, con navegación
  por año y mes para llegar rápido a fechas antiguas. Ya no se tipean.
- Asignación de equipos con **proyecto**, **fecha de retiro** y **fecha de
  entrega**; el historial de movimientos muestra esos datos.
- **Rol por trabajo** (Fotógrafo, Segunda cámara, Tercera cámara, Iluminador,
  Asistente o uno nuevo), independiente del perfil de la persona.
- **Tipo de proyecto** con categorías propias (Boda, 15 años, Empresarial,
  Gastronómica o las que se escriban).
- Al dar de alta un fotógrafo, el administrador elige su **rol en el sistema**
  y se crea su cuenta de acceso con contraseña provisoria.
- **Historial de entregas** por fotógrafo: activas, cerradas y canceladas, con
  acciones para marcar entregada, cancelar o reabrir.
- **Categorías del tarifario** administrables: se agregan y quitan desde el
  botón «Categorías» (sólo se quita una categoría sin servicios).
- Sección **Configuración** con Mi cuenta, Apariencia, Versión y Respaldo de
  datos (reemplaza a «Respaldo y datos» y al pie de la barra lateral).
- **Líneas de grilla** entre filas y columnas en todas las tablas.

### Cambiado

- El número de serie de un equipo es opcional.
- Lo abonado (seña + pagos) no puede superar el cobro total del proyecto.
- Eliminar equipos queda reservado a los administradores.
- «Ficha» de un equipo pasa a ser su historial de movimientos.
- Fotógrafos y servicios del tarifario ya no tienen estado activo/inactivo.
- El rol «Operador» pasa a llamarse «Usuario».
- Panel de control con tarjetas compactas de color sólido y tipografía en
  negrita; la sección «Inventario» lista los equipos en verde (disponibles) o
  rojo (en uso) con la fecha de su próximo service.
- En el inventario de equipos el color de cada fila indica disponibilidad; el
  estado del service se lee en la columna «Alerta».
- Tablas con letra más grande y filas más altas.
- Selectores, segmentos y desplegables en azul tenue en lugar de gris.
- «Resumen general» pasa al segundo lugar del menú.
- Cerrar sesión pide confirmación.
- La ventana y los diálogos se ajustan al tamaño real de la pantalla y las
  tablas se adaptan al alto disponible, sin cortar la parte inferior.
- Se quitaron de la interfaz y del código las referencias a los códigos de
  requisitos (RF / RNF).

### Quitado

- «Ver todo el mes» del calendario y «Cargar datos de ejemplo» de respaldos.

### Migración

- Al abrir una base de versiones anteriores se actualiza sola al esquema
  nuevo; antes se guarda una copia junto a ella (`fotique.db.antes-de-v2`).

### Corregido

- En la 1.1 la ventana podía abrirse más chica que su contenido en pantallas
  con escalado de Windows.

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

Primera versión cerrada, alineada al SRS «Relevamiento Fotique» v2.0.

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
- Empaquetado con PyInstaller (`fotique.spec` → `dist\Fotique.exe`).

### Notas de la primera ejecución

- Se crea la base en `%APPDATA%\Fotique\fotique.db` (ver `fotique/util.py`).
- Si la base está vacía se cargan datos de ejemplo una única vez.
