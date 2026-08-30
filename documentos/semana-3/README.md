# Semana 3 — Escenarios de Calidad (ASR) y guía Jira

**Proyecto:** Solventa · MISW4501 · Grupo 2
**Fecha:** 18 de agosto de 2026
**Rama:** `feature/semana-3`

---

## 1. Escenarios de Calidad (Hoja de Trabajo)

### RQ1 — Latencia / Desempeño

#### ASR-1.1 — Scoring en carga normal

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Socio de distribución (banco originador de crédito hipotecario) |
| **Estímulo** | Solicitud de cotización de seguro de vida hipotecario con perfilamiento Open Finance |
| **Ambiente** | Sistema operando en condiciones normales (500 req/min) |
| **Artefacto** | Servicio de Cotización & Rating + Servicio de Perfilamiento |
| **Respuesta** | El sistema calcula el perfil de riesgo combinando señales Open Finance y Open Data y devuelve la prima estimada |
| **Medida de respuesta** | 95% de solicitudes respondidas en < 200ms; p99 < 400ms |

#### ASR-1.2 — Scoring con proveedor externo degradado

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Cliente asegurado durante campaña masiva de socio (aerolínea) |
| **Estímulo** | 5.000 solicitudes de scoring concurrentes con proveedor Open Finance respondiendo lento (> 700ms) |
| **Ambiente** | Sistema bajo carga pico (10× tráfico normal), circuit breaker activo |
| **Artefacto** | Servicio de Perfilamiento + Caché Redis + Circuit Breaker |
| **Respuesta** | El sistema usa perfil de riesgo cacheado cuando Open Finance supera el timeout, operando en modo degradado elegante |
| **Medida de respuesta** | 95% de solicitudes respondidas en < 200ms usando caché; 0% de solicitudes perdidas por timeout externo |

---

### RQ2 — Facilidad de Modificación

#### ASR-2.1 — Nueva pasarela de pagos regional

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Equipo de desarrollo (desarrollador backend) |
| **Estímulo** | Integración de nueva pasarela de pagos para el mercado mexicano |
| **Ambiente** | Sistema en producción, otros servicios operando normalmente |
| **Artefacto** | Adaptador de Pagos (capa de adaptadores externos) |
| **Respuesta** | El desarrollador implementa el nuevo adaptador sin modificar el servicio de Pagos & Recaudo ni ningún otro servicio del núcleo |
| **Medida de respuesta** | Modificación + pruebas + despliegue completados en < 4 horas-hombre; cero cambios en servicios del núcleo de negocio |

#### ASR-2.2 — Nuevo ramo de seguro

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Área de producto / negocio |
| **Estímulo** | Solicitud de lanzamiento de nuevo ramo (seguro de mascota) no contemplado en el diseño inicial |
| **Ambiente** | Sistema en producción con 5 ramos activos |
| **Artefacto** | Servicio de Cotización & Rating + módulo de configuración de ramos |
| **Respuesta** | El equipo configura el nuevo ramo mediante parámetros sin modificar la lógica central del motor de rating |
| **Medida de respuesta** | Nuevo ramo disponible en producción en ≤ 2 semanas-equipo; modificaciones confinadas a configuración y adaptadores |

---

### RQ3 — Disponibilidad / Tolerancia a Fallos

#### ASR-3.1 — Caída del contenedor Redis

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Infraestructura interna (falla de contenedor) |
| **Estímulo** | Contenedor Redis se desconecta inesperadamente durante operación normal |
| **Ambiente** | Sistema en producción, usuarios activos realizando cotizaciones |
| **Artefacto** | BFF Web + Servicio de Cotización + Caché Redis |
| **Respuesta** | El sistema detecta la falla y redirige solicitudes al servicio de perfilamiento directo, manteniendo operación en modo degradado sin pérdida de transacciones activas |
| **Medida de respuesta** | Recuperación automática en < 30 segundos; disponibilidad mensual ≥ 99,9%; cero transacciones activas perdidas |

#### ASR-3.2 — Caída de zona de disponibilidad AWS

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Proveedor cloud (AWS) |
| **Estímulo** | Falla completa de la Zona de Disponibilidad A (us-east-1a) con instancias EKS activas |
| **Ambiente** | Sistema en producción, tráfico distribuido entre Zona A y Zona B en configuración activo-activo |
| **Artefacto** | EKS multi-zona + RDS PostgreSQL con réplica + Amazon MSK |
| **Respuesta** | El balanceador redirige todo el tráfico a Zona B; RDS promueve la réplica a primaria automáticamente; Kafka continúa operando con brokers en Zona B |
| **Medida de respuesta** | RTO ≤ 10 minutos; RPO ≤ 30 segundos; disponibilidad mensual ≥ 99,9% |

---

### RQ4 — Seguridad (Confidencialidad e Integridad)

#### ASR-4.1 — Confidencialidad en transmisión de datos financieros Open Finance

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Actor externo (ataque man-in-the-middle en red pública) |
| **Estímulo** | Intento de interceptar datos financieros del cliente durante el flujo de consentimiento y consulta Open Finance |
| **Ambiente** | Sistema operando normalmente, usuario en flujo activo de cotización de seguro de vida hipotecario |
| **Artefacto** | Adaptador Open Finance + capa de transporte + servicio de tokenización de PII |
| **Respuesta** | El sistema transmite todos los datos financieros cifrados con TLS 1.3 y tokeniza los campos PII antes de cualquier transmisión; solo los servicios autorizados con clave KMS pueden operar sobre los datos originales |
| **Medida de respuesta** | 100% de las transmisiones Open Finance usan TLS 1.3; 100% de los campos PII son tokenizados antes de salir del servicio de perfilamiento; cero datos personales en texto plano en tránsito |

#### ASR-4.2 — Integridad de pólizas emitidas en almacenamiento

| Campo | Descripción |
|---|---|
| **Fuente del estímulo** | Actor interno con credenciales comprometidas |
| **Estímulo** | Intento de modificar el contenido de una póliza emitida y firmada digitalmente, almacenada en S3 |
| **Ambiente** | Sistema en producción, póliza ya emitida con firma electrónica válida del cliente |
| **Artefacto** | Servicio de Emisión & Pólizas + Amazon S3 + AWS KMS + registro de auditoría |
| **Respuesta** | El sistema verifica la firma digital de la póliza en cada lectura; solo las modificaciones realizadas por el servicio de Emisión con token de autorización válido quedan registradas; cualquier intento de alteración directa sobre S3 es detectado y auditado |
| **Medida de respuesta** | 100% de las modificaciones a pólizas emitidas son realizadas por servicios autorizados con token válido; 100% de los intentos de alteración no autorizada son detectados y registrados en el log de auditoría en < 1 segundo |

---

## 2. Guía Jira — Qué hacer con cada escenario

### Historias de arquitectura existentes que cubren los ASR

Estas ya están en Jira. Solo agrega el ID del ASR en la descripción de cada historia como referencia:

| ASR | Historia Jira existente | Épica | Acción |
|---|---|---|---|
| ASR-1.1, ASR-1.2 | SOL-28 `HU-ARQ-07` Optimización de Latencia en Endpoints de Scoring | EP-ARQ-04 | Agregar referencia a ASR-1.1 y ASR-1.2 en la descripción |
| ASR-2.1 | SOL-20 `HU-ARQ-02` Diseño de Abstracciones para Pasarelas de Pago | EP-ARQ-01 | Agregar referencia a ASR-2.1 en la descripción |
| ASR-2.2 | SOL-21 `HU-ARQ-01` Parametrización y Aislamiento Multitenant | EP-ARQ-01 | Agregar referencia a ASR-2.2 en la descripción |
| ASR-3.1, ASR-3.2 | SOL-29 `HU-ARQ-06` Implementación de Tolerancia a Fallos y Failover | EP-ARQ-04 | Agregar referencia a ASR-3.1 y ASR-3.2 en la descripción |
| ASR-4.1 | SOL-23 `HU-ARQ-03` Tokenización de PII y Trazabilidad | EP-ARQ-02 | Agregar referencia a ASR-4.1 en la descripción |

---

### Historias de arquitectura NUEVAS que debes crear en Jira

#### HU-ARQ-08 — Event Bus con Kafka (EP-ARQ-03 · SOL-25)

> **Épica:** `[EP-ARQ-03] Empaquetamiento en Contenedores y Plataforma de Datos`

**Descripción:**
Como plataforma Solventa, quiero que los servicios de Cotización, Siniestros y Pagos publiquen eventos de dominio en un Event Bus con Kafka 3.x (KRaft, sin ZooKeeper) en desarrollo local y Amazon MSK en producción, para garantizar comunicación asíncrona desacoplada entre servicios con persistencia y replay de eventos.

**Criterios de aceptación:**
- El Event Bus corre en Docker Compose (imagen `bitnami/kafka:3.6`, modo KRaft) sin necesidad de ZooKeeper
- Los servicios productores publican eventos usando la misma librería `kafka-python` en todos los ambientes
- En producción el mismo código apunta a Amazon MSK sin cambios (solo configuración de brokers)
- Los eventos se retienen mínimo 7 días para permitir replay
- El sistema procesa ≥ 1.000.000 eventos de telemetría en 10 minutos sin pérdida

**Story points sugeridos:** 8 | **Prioridad:** Alta

---

#### HU-ARQ-09 — Autoescalado horizontal (EP-ARQ-04 · SOL-27)

> **Épica:** `[EP-ARQ-04] Escalabilidad y Desempeño para Alta Concurrencia`

**Descripción:**
Como plataforma Solventa, quiero que los pods del servicio de Cotización & Rating escalen horizontalmente de forma automática en EKS ante incrementos de carga, para garantizar que el sistema pase de 500 a 50.000 cotizaciones/minuto en ≤ 60 segundos durante campañas masivas de socios distribuidores.

**Criterios de aceptación:**
- El Horizontal Pod Autoscaler (HPA) de Kubernetes está configurado para el servicio de Cotización
- El escalado se dispara cuando el uso de CPU supera el 70% por más de 30 segundos
- El tiempo de escalar de 1 a 10 réplicas es ≤ 60 segundos
- El tiempo de reducir réplicas (scale-down) tras bajar la carga es ≤ 5 minutos para evitar oscilaciones
- El experimento de carga con JMeter valida el comportamiento con 50.000 req/min sostenidos 5 minutos

**Story points sugeridos:** 13 | **Prioridad:** Alta

---

#### HU-ARQ-10 — Arquitectura offline sync BFF Móvil (EP-ARQ-03 · SOL-25)

> **Épica:** `[EP-ARQ-03] Empaquetamiento en Contenedores y Plataforma de Datos`

**Descripción:**
Como BFF Móvil de Solventa, quiero que el cliente React Native almacene localmente las pólizas activas del usuario y sincronice los cambios pendientes cuando recupere conectividad, para que el 100% de las consultas de pólizas estén disponibles sin conexión a internet.

**Criterios de aceptación:**
- Las pólizas activas del usuario se almacenan en AsyncStorage cifrado en el dispositivo al hacer login
- La billetera de pólizas (FE-06) es completamente funcional sin conexión: muestra número, vigencia y cobertura
- Al recuperar conectividad, el cliente sincroniza automáticamente sin intervención del usuario en ≤ 10 segundos
- Los datos offline tienen TTL de 24 horas; pasado ese tiempo se muestra alerta de datos desactualizados
- El modo offline no expone PII sensible más allá de lo estrictamente necesario para mostrar la póliza

**Story points sugeridos:** 8 | **Prioridad:** Media

---

#### HU-ARQ-11 — Integridad y auditoría de pólizas emitidas (EP-ARQ-02 · SOL-16)

> **Épica:** `[EP-ARQ-02] Cumplimiento Regulatorio, Privacidad de Datos y Gobierno de IA`

**Descripción:**
Como sistema de emisión de Solventa, quiero que cada póliza emitida tenga una firma digital verificable y un registro de auditoría inmutable, para garantizar que el 100% de las modificaciones sobre pólizas almacenadas sean realizadas únicamente por servicios autorizados y queden trazadas.

**Criterios de aceptación:**
- Cada póliza emitida incluye un hash SHA-256 de su contenido firmado con AWS KMS al momento de la emisión
- El servicio de Emisión verifica la firma en cada lectura; una firma inválida genera alerta inmediata y bloquea la operación
- Cada operación de escritura sobre una póliza genera un registro en el log de auditoría con: servicio, timestamp, token de autorización y hash antes/después
- Los intentos de modificación directa sobre S3 sin pasar por el servicio de Emisión son detectados y registrados en < 1 segundo
- El log de auditoría es inmutable (S3 Object Lock) y se retiene mínimo 5 años por regulación SFC

**Story points sugeridos:** 8 | **Prioridad:** Alta

---

## 3. Capacidad del equipo y velocidad

### Datos base

| Parámetro | Valor |
|---|---|
| Duración del proyecto | 7 semanas (3 ago – 23 sep 2026) |
| Integrantes | 4 personas |
| Dedicación por persona | 12 horas/semana |
| **Capacidad semanal del equipo** | **48 horas/semana** |
| **Capacidad total del proyecto** | **336 horas (7 × 48h)** |
| Semanas ya ejecutadas | 2 (semanas 1 y 2) |
| Horas ya consumidas (est.) | ~96 horas |
| **Horas disponibles restantes** | **~240 horas (semanas 3–7)** |

### Definición de velocidad

Se adopta la convención: **1 Story Point = 2 horas de trabajo**.

| Métrica | Valor |
|---|---|
| Capacidad semanal en SP | 24 SP/semana (48h ÷ 2h/SP) |
| Capacidad total restante | 120 SP (240h ÷ 2h/SP) |
| Factor de carga real (overhead, reuniones, imprevistos) | 80% |
| **Velocidad efectiva por semana** | **~19 SP/semana** |

### Distribución de horas por rol (semanas 3–7)

| Integrante | Rol en pruebas | Horas totales disponibles |
|---|---|---|
| Jazmin Córdoba | Gerencia, usabilidad, entrega | 60h |
| Juan Mejía | Web front, integración API, pagos | 60h |
| Miguel Gómez | Arquitectura, Open Finance, KYC, rendimiento, seguridad | 60h |
| Angie Arandio | Dominio, web back, móvil, pruebas unitarias | 60h |
| **Total** | | **240h** |

### Backlog estimado vs capacidad disponible

| Tipo | Historias | SP estimados | Horas aprox. |
|---|---|---|---|
| Funcionales web (FE-01 a FE-04) | 4 | 28 SP | 56h |
| Funcionales móvil (FE-05 a FE-08) | 4 | 24 SP | 48h |
| Portal socios FE-09 | 1 | 8 SP | 16h |
| Arquitectura HU-ARQ-01 a 07 | 7 | 55 SP | 110h |
| Arquitectura HU-ARQ-08 a 11 | 4 | 37 SP | 74h |
| **Total backlog** | **20** | **152 SP** | **304h** |
| **Capacidad disponible** | | **120 SP** | **240h** |

> **Conclusión:** el backlog completo (152 SP) supera la capacidad disponible (120 SP). Se requiere priorización: las historias de alta prioridad deben completarse en semanas 3–6; las de prioridad media quedan como stretch goals para semana 7.

---

## 4. Resumen de acciones en Jira

| Acción | Cantidad | Detalle |
|---|---|---|
| Actualizar descripción de historias existentes | 5 | Agregar referencia al ID del ASR |
| Crear historias nuevas | 4 | HU-ARQ-08, 09, 10, 11 |
| Épica nueva | 0 | Las 4 nuevas caben en épicas existentes |
| Definir story points en todas las historias | 20 | Usar escala: 1 SP = 2 horas |
| Definir prioridad (Alta/Media/Baja) en todas | 20 | Ver columna prioridad en cada HU-ARQ del README |
| Actualizar velocidad del equipo en el board | 1 | 19 SP/semana efectivos |
