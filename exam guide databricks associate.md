# Exam Guide — Databricks Certified Data Engineer Associate
*Versión vigente: May 4, 2026*

> Actualizado respecto a la versión anterior (Nov 30, 2025). Ver [comparación detallada](comparacion_examen_guide_nov2025_vs_may2026.md) de cambios.

---

## Sobre el Examen

| Campo | Detalle |
|-------|---------|
| Preguntas | 45 de opción múltiple (scored) |
| Tiempo | 90 minutos |
| Costo | USD 200, más impuestos aplicables según ley local |
| Modalidad | Online o centro de pruebas |
| Materiales | No permitidos |
| Prerequisito | Ninguno (recomendado: curso + 6 meses de experiencia) |
| Vigencia | 2 años |

> El examen puede incluir preguntas no puntuadas para recolección estadística. No afectan el puntaje.

---

## Entrenamiento Recomendado

- **Instructor-led:** Data Engineering with Databricks
- **Self-paced (Databricks Academy):**
  - Data Ingestion with Lakeflow Connect
  - Deploy Workloads with Lakeflow Jobs
  - DevOps Essentials for Data Engineering
  - Data Interoperability with Unity Catalog *(nuevo)*
  - Build Data Pipelines with Lakeflow Spark Declarative Pipeline
  - Get Started with Data Governance on Databricks *(nuevo)*

---

## Outline del Examen

> A diferencia de la versión anterior, el examen ahora define el peso (%) de cada sección.

### Section 1: Databricks Intelligence Platform (6%)
- Comprender los componentes centrales del Data Intelligence Platform: arquitectura, Delta Lake y Unity Catalog
- Comprender los servicios de compute de la plataforma (características, limitaciones, modelos de costo) y seleccionar la opción más adecuada según el caso de uso

### Section 2: Data Ingestion and Loading (21%)
- Habilitar y detallar patrones de ingesta (batch, streaming, incremental) e importar datos desde archivos locales, conectores estándar de Lakeflow Connect y conectores gestionados
- Usar el comando `COPY INTO` para cargar incrementalmente archivos desde cloud object storage (ADLS/S3/GCS) hacia tablas gobernadas por Unity Catalog
- Usar Auto Loader con schema enforcement y schema evolution en modo batch (directory listing o file notification)
- Configurar Lakeflow Connect para ingerir de forma confiable datos desde fuentes empresariales diversas
- Usar clientes JDBC/ODBC o REST en notebooks para llevar datos a cloud storage o directamente a tablas UC, orquestado con Lakeflow Jobs
- Priorizar entre Auto Loader, Lakeflow Connect (conectores estándar/gestionados), conectores partner y otros métodos según volumen, frecuencia, tipos de datos y necesidades de gobernanza
- Ingerir datos semi-estructurados y no estructurados (JSON, datos anidados) vía Lakeflow Connect y otros conectores gestionados

### Section 3: Data Transformation and Modeling (22%)
- Implementar limpieza de datos leyendo tablas bronze con PySpark/SQL, limpiando nulos, estandarizando tipos y escribiendo a tablas silver
- Combinar DataFrames con inner join, left join, broadcast join, llaves múltiples, cross join, union y union all
- Manipular columnas, filas y estructuras de tabla: agregar, eliminar, dividir, renombrar columnas, aplicar filtros y explotar arreglos
- Realizar deduplicación y operaciones de agregación sobre DataFrames (count, approx count distinct, mean, summary)
- Comprender parámetros básicos de tuning (`spark.sql.shuffle.partitions`, `spark.default.parallelism`, `spark.executor/driver.memory`, `spark.sql.autoBroadcastJoinThreshold`) y re-medir el rendimiento
- Comprender la diferencia y cómo construir objetos de la capa Gold: materialized views, views, streaming tables y tablas para equipos de BI/analytics en Unity Catalog
- Aplicar validaciones y reglas de calidad de datos para garantizar datasets Silver y Gold confiables

### Section 4: Working with Lakeflow Jobs (16%)
- Implementar flujos de control (retries y tareas condicionales como branching y looping) usando Lakeflow Jobs para orquestación de pipelines
- Configurar tareas comunes (notebook, SQL query, dashboard y pipeline) y sus dependencias usando el DAG-based task graph de Lakeflow Jobs
- Implementar schedules de jobs comprendiendo los tipos de trigger (scheduled, file arrival y table update)
- Elegir entre triggers basados en tiempo o en datos según la disponibilidad de datos y las dependencias del pipeline

### Section 5: Implementing CI/CD (10%)
- Gestionar el flujo de desarrollo de código dentro del workspace, incluyendo crear y alternar ramas en Databricks Git Folders (antes Databricks Repos), commit/push de cambios y creación de pull requests
- Comprender la configuración específica por entorno usando variables y overrides de Automation Bundles (antes Databricks Asset Bundles) para promover el mismo código entre dev, test y prod
- Desplegar Declarative Automation Bundles para empaquetar, configurar y promover Lakeflow Jobs, Lakeflow Spark Declarative Pipelines y otros assets del workspace entre ambientes
- Comprender el uso de Databricks CLI para validar, desplegar y gestionar Automation Bundles y otros assets del workspace en flujos de CI/CD automatizados

### Section 6: Troubleshooting, Monitoring, and Optimization (10%)
- Identificar tendencias de rendimiento de jobs usando el historial de ejecuciones (run history) de Lakeflow Jobs frente a líneas base históricas
- Usar la UI de Lakeflow Jobs para monitorear la salud del pipeline: interpretar estados, visualizar el DAG de tareas para identificar bloqueadores upstream, y rastrear tiempos de ejecución y tasas de falla
- Identificar cuellos de botella comunes (data skew, shuffling y disk spilling) interpretando métricas a nivel de stage en Spark UI
- Comprender las características de Liquid Clustering y predictive optimization
- Diagnosticar fallos de arranque de clusters, conflictos de librerías y problemas de out-of-memory

### Section 7: Governance and Security (15%)
- Diferenciar entre tablas managed y external en Unity Catalog y realizar operaciones básicas (crear, modificar, eliminar y convertir entre managed/external)
- Configurar controles de acceso vía UI y SQL aplicando privilegios GRANT, REVOKE y DENY a principals (usuarios, grupos, service principals) en los niveles adecuados de la jerarquía de seguridad
- Comprender column-level masking y row-level security para restringir la visibilidad de datos según grupos de usuario
- Comprender las políticas ABAC (Attribute-Based Access Control) de Unity Catalog para controlar de forma centralizada el filtrado a nivel de fila y el enmascaramiento de columnas para datos sensibles

---

## Preguntas de Muestra

### Pregunta 1
**Objetivo:** Identify common performance bottlenecks such as data skew, shuffling, and disk spilling by interpreting stage-level metrics in the Spark UI

Un data engineer nota que la duración de un batch job se duplicó tras incorporar una nueva fuente de datos. En Spark UI, el stage más largo muestra que la mayoría de tareas terminan en menos de 30 segundos, pero una tarea toma más de 10 minutos. El resumen de tareas del stage muestra Min/Median shuffle read cercano a 400 MB, mientras que el Max shuffle read supera los 5 GB.

¿Qué solución reduce el tiempo de ejecución del job?

```
A. Aumentar el tamaño del cluster agregando más executors para que la tarea lenta termine más rápido
B — CORRECTA. Confirmar que Adaptive Query Execution (AQE) con skew join handling está activo para dividir automáticamente la partición sobredimensionada en runtime
C. Reducir spark.sql.shuffle.partitions para consolidar el trabajo en menos tareas
D. Reparticionar manualmente el dataset usando una salt key antes del join para distribuir las llaves sesgadas de forma uniforme
```

**Respuesta: B** — Los executors adicionales no resuelven el sesgo: la tarea sobredimensionada seguirá siendo el cuello de botella. Reducir `shuffle.partitions` (C) empeora el problema al generar particiones aún más grandes. Reparticionar con salt key (D) es una técnica válida pero manual; la solución recomendada por el objetivo es primero verificar que AQE con skew join handling —una capacidad nativa de Spark en Databricks— esté activo, ya que resuelve el sesgo automáticamente en runtime.

---

### Pregunta 2
**Objetivo:** Understand Databricks Data Intelligence Platform's compute services, including their characteristics, limitations, and cost models, and select the most suitable option for each workload use case

Un data engineer requiere iteración rápida sobre pipelines manteniendo rollbacks confiables tras ingestas fallidas, garantizando pistas de auditoría para cumplimiento regulatorio, y proveyendo acceso consistente a una única fuente de verdad tanto para cargas de trabajo de AI como de BI.

¿Qué estrategia debería usar el data engineer para cumplir estos requisitos?

```
A. Almacenamiento CSV en DBFS con versionado manual de archivos y copias nocturnas para rollback
B — CORRECTA. Transacciones ACID de Delta Lake y time travel, gobernadas por Unity Catalog para acceso consistente y lineage
C. Cloud object storage únicamente, con consultas SQL ad hoc para recuperación y gobernanza
D. DataFrames efímeros en memoria para pistas de auditoría y distribución BI
```

**Respuesta: B** — Delta Lake provee ACID y time travel de forma nativa (rollback confiable), y Unity Catalog añade lineage y gobierno unificado sobre esa misma fuente de datos para AI y BI. Las opciones A, C y D carecen de garantías transaccionales, versionado nativo o gobernanza centralizada.

---

### Pregunta 3
**Objetivo:** Enable and detail data ingestion patterns, including batch, streaming, and incremental loading, and import data from sources such as local files, Lakeflow Connect standard connectors, and Lakeflow Connect managed connectors

Un data engineer está construyendo pipelines downstream para consumir audit logs de Databricks desde un bucket S3 propiedad del cliente. Antes de implementar inferencia de esquema y checkpointing, quiere entender el formato de entrega, la latencia típica de ingesta y si los archivos pueden sobrescribirse.

¿Cuál es el comportamiento de almacenamiento de los audit logs de Databricks?

```
A — CORRECTA. Los archivos se entregan como JSON con registro típico de eventos en menos de 15 minutos tras iniciar la entrega, y nuevas entregas pueden sobrescribir archivos existentes
B. Los archivos se entregan como CSV con garantías de latencia sub-minuto, y las sobrescrituras nunca ocurren para preservar la inmutabilidad
C. Los archivos se entregan como Parquet con consistencia eventual más allá de 24 horas, y las sobrescrituras están deshabilitadas para simplificar la ingesta streaming
D. Los archivos se entregan como JSON con cadencia batch semanal, y las sobrescrituras reemplazan completamente el contenido previo sin append
```

**Respuesta: A** — Los audit logs de Databricks se entregan como JSON con latencia típica menor a 15 minutos, y es un comportamiento conocido que entregas nuevas pueden sobrescribir archivos existentes — de ahí la importancia de diseñar el pipeline de ingesta (Auto Loader/checkpointing) considerando esta posibilidad, en vez de asumir inmutabilidad.

---

### Pregunta 4
**Objetivo:** Diagnose cluster startup failures, library conflicts, and out-of-memory issues

Un equipo de data engineering da soporte a múltiples analistas de negocio que ejecutan consultas SQL ad hoc durante el día sobre tablas Delta curadas. El equipo necesita garantizar rendimiento eficiente de las consultas, arranque rápido del cluster y soporte para múltiples usuarios simultáneos, controlando el costo al evitar escalamiento innecesario hacia clusters muy grandes.

¿Qué configuración de cluster cumple estos requisitos?

```
A. Un job cluster con autoscaling diseñado para workflows de ETL programados
B. Un all-purpose cluster configurado con un número fijo de worker nodes
C — CORRECTA. Un high-concurrency cluster con autoscaling habilitado
D. Un single-node cluster configurado para tareas de desarrollo ligeras
```

**Respuesta: C** — Los high-concurrency clusters están optimizados precisamente para múltiples usuarios ejecutando consultas SQL simultáneas, con aislamiento de queries y arranque rápido; el autoscaling permite controlar costos evitando sobre-aprovisionamiento. Los job clusters (A) están pensados para cargas ETL programadas, no ad hoc; un cluster de tamaño fijo (B) no controla costos eficientemente; un single-node (D) no soporta concurrencia real.

---

### Pregunta 5
**Objetivo:** Manage your code development workflow within the Databricks workspace UI, including creating and switching between branches in Databricks Git Folders (formerly Databricks Repos), committing and pushing changes, and creating pull requests using Databricks Git integration

Un equipo quiere una forma modular de desplegar, versionar y orquestar pipelines ETL en Databricks, habilitando CI/CD y repetibilidad.

¿Qué feature soporta este requisito?

```
A. Usar modelos en Unity Catalog para representar jobs ETL, donde cada modelo almacena el artefacto de código del pipeline y el CI/CD promueve versiones actualizando alias de modelo vinculados a tareas de Job
B. Empaquetar la lógica de transformación como librerías wheel almacenadas en Unity Catalog Volumes y vincularlas a tareas de Jobs para garantizar despliegue determinista entre entornos
C. Empaquetar la lógica de API dentro de un notebook montado en un Volume, y usar Jobs API v2 para disparar el notebook, dependiendo del historial de revisiones del notebook como sistema de versionado
D — CORRECTA. Usar DABs para definir recursos y assets de código, versionarlos en Git, y promover despliegues entre entornos mediante acciones de CI/CD automatizadas
```

**Respuesta: D** — Los Databricks Asset Bundles (hoy Declarative Automation Bundles) son el mecanismo diseñado específicamente para definir recursos (jobs, pipelines) como código, versionarlos en Git y promoverlos de forma automatizada y repetible entre dev/test/prod. Las opciones A, B y C reutilizan otros componentes de la plataforma (Unity Catalog models, Volumes, revisiones de notebook) de forma inadecuada como sustitutos de un mecanismo real de CI/CD.
