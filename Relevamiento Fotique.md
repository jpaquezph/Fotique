# Especificación de Requerimientos de Software (SRS) — Versión Actualizada

**Proyecto:** Sistema Integral de Gestión Fotográfica (Desktop)

**Stack Tecnológico:** Python

**Versión:** 2.0

**Fecha:** Septiembre 2026

## 1. Documento de Relevamiento e Identificación del Problema

### 1.1 Objetivos del Sistema

- **Objetivo General:** Desarrollar un sistema de escritorio centralizado en **Python**, seguro y *offline-first* para la gestión operativa, logística de personal/equipamiento y gestión comercial de un estudio fotográfico.

- **Objetivos Específicos:**

  - Controlar el ciclo de vida, estado de mantenimiento e historial de asignación del equipamiento por fotógrafo.

  - Gestionar el equipo de fotógrafos, asignación de inventario, calendarios individuales y entregas/trabajos pendientes.

  - Administrar la relación comercial con los clientes por proyecto (señas, cobros totales, eventos).

  - Centralizar plantillas de contratos, listas de precios, catálogo de servicios y un calendario general del estudio.

### 1.2 Actores del Sistema

- **Administrador / Fotógrafo Principal:** Acceso total a la gestión comercial, financiera, de personal y de inventario.

- **Fotógrafo Integrante:** Consulta de calendario personal, asignación de equipos tomados del stock y tareas/entregas pendientes.

## 2. Requisitos Funcionales (RF)

### Módulo A: Inventario y Control de Equipos

- **RF-01 (Ficha de Equipo):** El sistema debe registrar cada unidad de equipamiento con los siguientes campos obligatorios:

  - Número de Serie

  - Marca

  - Modelo

  - Fecha de adquisición

  - Fecha de service (último y próximo)

  - Estado: `En stock` o `En uso`

  - Fotógrafo asignado (obligatorio si el estado es `En uso`)

  - Notas / Observaciones

- **RF-02 (Trazabilidad y Movimiento de Stock):** Cambiar el estado de un equipo a `En uso` debe requerir la selección del fotógrafo responsable y quedar registrado en el historial de uso.

- **RF-03 (Alertas de Service):** El sistema debe emitir alertas visuales cuando la fecha de service de un equipo esté próxima o vencida.

### Módulo B: Gestión de Fotógrafos / Personal

- **RF-04 (Registro de Fotógrafos):** Gestión de la base de datos de fotógrafos con:

  - Nombre y apellido

  - Información de contacto (teléfono, email)

  - Historial y lista actual de equipos tomados del stock

  - Calendario personal de asignaciones

  - Listado de entregas y trabajos pendientes con estados (Pendiente, En edición, Entregado)

### Módulo C: Clientes y Proyectos

- **RF-05 (Estructura Proyecto - Cliente):** Registros agrupados por Proyecto, conteniendo:

  - Nombre y apellido del cliente

  - Responsable / Contacto principal

  - Celular / Teléfono

  - Dirección (del cliente o locación del evento)

  - Fecha del proyecto/evento

  - Calendario específico del proyecto

  - Registro de Seña (monto, fecha y medio de pago)

  - Cobro Total y Cálculo automático de saldo pendiente (`Cobro Total - Seña - Pagos parciales`)

### Módulo D: Generales y Administración

- **RF-06 (Gestión de Contratos):** Almacenamiento y generación de contratos a partir de plantillas, vinculables a cada proyecto.

- **RF-07 (Precios y Servicios):** Tarifario configurable de servicios (coberturas, paquetes, edición, fotolibros, viáticos).

- **RF-08 (Calendario General):** Vista consolidada e interactiva que unifique eventos de clientes, calendarios de fotógrafos y fechas de entrega/service.

## 3. Requisitos No Funcionales (RNF)

- **RNF-01 (Lenguaje y Ecosistema):** Desarrollado enteramente en **Python** (utilizando librerías estándar y frameworks GUI/DB nativos o consolidados como PySide6/PyQt6 o CustomTkinter).

- **RNF-02 (Arquitectura Offline-First):** Funcionamiento local sin necesidad de internet, con base de datos **SQLite** embebida.

- **RNF-03 (Rendimiento):** Tiempos de respuesta para consultas de listados $\\le 150\\text\{ ms\}$.

- **RNF-04 (Integridad de Datos):** Reglas de validación relacional para evitar asignar equipos inexistentes o eliminar fotógrafos con entregas activas.

- **RNF-05 (Backups):** Exportación e importación rápida de la base de datos SQLite a archivos de respaldo (`.db` o `.sqlite`).

## 4. Estrategia de Testing y TDD (Python)

El desarrollo en Python aplicará TDD mediante la librería estándar `unittest` o `pytest`.

```
[ Red: Escribir test que falla ] ➔ [ Green: Escribir código mínimo en Python ] ➔ [ Refactor: Optimizar código ]
```

### 4.1 Pirámide de Testing

1. **Pruebas Unitarias (`pytest`):** Cobertura del 80%+ en lógica de negocio (cálculo de saldos de clientes, validación de estado de equipos, etc.).

2. **Pruebas de Integración (SQLite In-Memory):** Pruebas del ORM o capa de datos creando la base de datos en memoria (`sqlite3.connect(":memory:")`).

3. **Pruebas de GUI / Interfaz:** Verificación de señales, slots y renderizado de componentes.

### 4.2 Casos de Prueba TDD (Ejemplos en Python)

#### Caso 1: Asignación de Equipo a Fotógrafo

Python

```
def test_asignar_equipo_a_fotografo_exitoso():

    equipo = Equipo(

        numero_serie="SN123456",

        marca="Sony",

        modelo="A7 IV",

        estado="En stock",

    )

    fotografo = Fotografo(nombre="Jorge", apellido="Paquez")


    equipo.asignar_a_fotografo(fotografo)


    assert equipo.estado == "En uso"

    assert equipo.fotografo_actual == fotografo

    assert equipo in fotografo.equipos_tomados
```

#### Caso 2: Intento de Asignar Equipo Ya Usado

Python

```
def test_asignar_equipo_ya_en_uso_lanza_excepcion():

    equipo = Equipo(

        numero_serie="SN123456",

        marca="Sony",

        modelo="A7 IV",

        estado="En uso",

        fotografo_actual=Fotografo(nombre="Juan"),

    )

    otro_fotografo = Fotografo(nombre="Pedro")


    with pytest.raises(EquipoNoDisponibleException):

        equipo.asignar_a_fotografo(otro_fotografo)
```

#### Caso 3: Cálculo de Saldo Pendiente del Cliente

Python

```
def test_calculo_saldo_pendiente_proyecto():

    proyecto = Proyecto(

        cliente="Maria Lopez", cobro_total=150000.0, sena=50000.0

    )


    assert proyecto.obtener_saldo_pendiente() == 100000.0


## 5. Modelo Entidad-Relación (E-R) Sugerido

```
[Fotógrafos] 1 ─── N [Equipos] (Asignación actual)

     │

     └─── N [Trabajos_Pendientes]

     │

     └─── N [Proyectos] (Fotógrafo asignado)


[Clientes] 1 ─── N [Proyectos]

                      │

                      ├─── 1 [Registro_Pago] (Seña, Cobro Total, Saldo)

                      │

                      └─── 1 [Contrato]
```

