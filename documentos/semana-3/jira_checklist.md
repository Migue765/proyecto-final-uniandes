# Checklist de cambios en Jira — Semana 3

**Convención:** 1 Story Point = 2 horas · Velocidad efectiva = 19 SP/semana
**Capacidad restante:** 120 SP (semanas 3–7)

---

## PASO 1 — Configurar velocidad del equipo en el board

En Jira: **Configuración del tablero → Estimación → Story Points**

- [ ] Definir unidad de estimación: **Story Points**
- [ ] Registrar velocidad del equipo: **19 SP/semana**
- [ ] Registrar capacidad total restante: **120 SP (semanas 3–7)**

---

## PASO 2 — Crear épica nueva

- [ ] **Crear épica `EP-05`**
  - Nombre: `[EP-05] Portal de Socios y Distribución (Embedded)`
  - Descripción: Funcionalidades para onboarding de socios distribuidores, gestión de API keys y catálogo de seguros embebidos vía API

---

## PASO 3 — Crear historias nuevas

### FE-09 — Portal de socios distribuidores
> **Épica:** `EP-05` (la que acabas de crear)
> **Prioridad:** Media · **SP:** 8

**Descripción:**
Como socio distribuidor (banco, aerolínea, e-commerce), quiero acceder a un portal web para gestionar mi integración con Solventa, para registrar mi cuenta, obtener mis API keys, consultar el catálogo de seguros disponibles y monitorear el consumo de mi cuota de llamadas.

**Criterios de aceptación:**
- [ ] El socio puede registrarse con nombre, RUT/NIT, contacto técnico y tipo de integración
- [ ] Al completar el onboarding, el sistema genera automáticamente un par de API keys (producción y sandbox)
- [ ] El portal muestra el catálogo de ramos disponibles con los parámetros de cada producto
- [ ] El socio puede consultar su consumo de API en tiempo real (llamadas del mes, cuota disponible)
- [ ] Las API keys se pueden rotar sin tiempo de inactividad (rotación sin corte)

---

### HU-ARQ-08 — Event Bus con Kafka
> **Épica:** `EP-ARQ-03` (SOL-25)
> **Prioridad:** Alta · **SP:** 8
> **ASR relacionado:** ASR-1.2 (degradación elegante)

**Descripción:**
Como plataforma Solventa, quiero que los servicios de Cotización, Siniestros y Pagos publiquen eventos de dominio en un Event Bus con Kafka 3.x (KRaft, sin ZooKeeper) en desarrollo local y Amazon MSK en producción, para garantizar comunicación asíncrona desacoplada con persistencia y replay de eventos.

**Criterios de aceptación:**
- [ ] Kafka 3.x corre en Docker Compose (imagen `bitnami/kafka:3.6`, modo KRaft) sin ZooKeeper
- [ ] Los servicios usan `kafka-python` como librería en todos los ambientes
- [ ] En producción el mismo código apunta a Amazon MSK solo cambiando variables de entorno
- [ ] Los eventos se retienen mínimo 7 días para permitir replay
- [ ] El sistema procesa ≥ 1.000.000 eventos de telemetría en 10 minutos sin pérdida

---

### HU-ARQ-09 — Autoescalado horizontal
> **Épica:** `EP-ARQ-04` (SOL-27)
> **Prioridad:** Alta · **SP:** 13
> **ASR relacionado:** ASR-3.2 (caída zona AWS)

**Descripción:**
Como plataforma Solventa, quiero que los pods del servicio de Cotización & Rating escalen horizontalmente de forma automática en EKS ante incrementos de carga, para garantizar que el sistema soporte el paso de 500 a 50.000 cotizaciones/minuto en ≤ 60 segundos durante campañas masivas de socios.

**Criterios de aceptación:**
- [ ] HPA (Horizontal Pod Autoscaler) configurado para el servicio de Cotización en EKS
- [ ] El escalado se dispara cuando uso de CPU supera 70% por más de 30 segundos
- [ ] Tiempo de escalar de 1 a 10 réplicas es ≤ 60 segundos
- [ ] Scale-down ocurre en ≤ 5 minutos tras bajar la carga para evitar oscilaciones
- [ ] Experimento con JMeter valida 50.000 req/min sostenidos durante 5 minutos

---

### HU-ARQ-10 — Arquitectura offline sync BFF Móvil
> **Épica:** `EP-ARQ-03` (SOL-25)
> **Prioridad:** Media · **SP:** 8
> **ASR relacionado:** ASR-3.1 (caída Redis)

**Descripción:**
Como BFF Móvil de Solventa, quiero que el cliente React Native almacene localmente las pólizas activas del usuario y sincronice cambios pendientes al recuperar conectividad, para que el 100% de las consultas de pólizas estén disponibles sin conexión a internet.

**Criterios de aceptación:**
- [ ] Las pólizas activas se almacenan en AsyncStorage cifrado al hacer login
- [ ] La billetera de pólizas (FE-06) funciona completamente sin conexión (número, vigencia, cobertura)
- [ ] Al recuperar conectividad, sincronización automática en ≤ 10 segundos sin intervención del usuario
- [ ] Los datos offline tienen TTL de 24 horas; vencido ese tiempo se muestra alerta de datos desactualizados
- [ ] El modo offline no expone PII más allá de lo estrictamente necesario

---

### HU-ARQ-11 — Integridad y auditoría de pólizas emitidas
> **Épica:** `EP-ARQ-02` (SOL-16)
> **Prioridad:** Alta · **SP:** 8
> **ASR relacionado:** ASR-4.2 (integridad almacenamiento)

**Descripción:**
Como sistema de emisión de Solventa, quiero que cada póliza emitida tenga una firma digital verificable y un registro de auditoría inmutable, para garantizar que el 100% de las modificaciones sobre pólizas almacenadas sean realizadas únicamente por servicios autorizados y queden trazadas.

**Criterios de aceptación:**
- [ ] Cada póliza emitida incluye hash SHA-256 firmado con AWS KMS al momento de emisión
- [ ] El servicio verifica la firma en cada lectura; firma inválida genera alerta y bloquea la operación
- [ ] Cada escritura sobre una póliza genera registro en log de auditoría (servicio, timestamp, token, hash antes/después)
- [ ] Los intentos de modificación directa en S3 son detectados y registrados en < 1 segundo
- [ ] El log de auditoría usa S3 Object Lock y se retiene mínimo 5 años (regulación SFC)

---

## PASO 4 — Actualizar historias existentes: agregar referencia ASR + story points + prioridad

### Historias funcionales (FE)

| SOL | Historia | SP | Prioridad | Agregar en descripción |
|---|---|---|---|---|
| SOL-3 | FE-01 Cotización de seguros | 8 | Alta | `Cubre flujo Open Finance de perfilamiento` |
| SOL-4 | FE-02 Suscripción y emisión | 8 | Alta | — |
| SOL-5 | FE-03 Administración de pólizas | 5 | Media | — |
| SOL-6 | FE-04 Gestión y seguimiento de siniestros | 8 | Alta | — |
| SOL-10 | FE-05 Autenticación biométrica | 8 | Alta | `Incluye flujo KYC/AML completo` |
| SOL-11 | FE-06 Billetera de pólizas | 5 | Media | `Relacionada con HU-ARQ-10 (offline sync)` |
| SOL-13 | FE-07 Notificaciones y asistencia | 5 | Media | — |
| SOL-12 | FE-08 Reporte de siniestros con evidencia | 5 | Media | — |

### Historias de arquitectura (HU-ARQ)

| SOL | Historia | SP | Prioridad | Agregar en descripción |
|---|---|---|---|---|
| SOL-21 | HU-ARQ-01 Parametrización Multitenant | 8 | Alta | `Cubre ASR-2.2 (nuevo ramo en ≤ 2 semanas)` |
| SOL-20 | HU-ARQ-02 Abstracciones Pasarelas Pago | 8 | Alta | `Cubre ASR-2.1 (nueva pasarela en < 4h-hombre)` |
| SOL-23 | HU-ARQ-03 Tokenización PII y Trazabilidad | 8 | Alta | `Cubre ASR-4.1 (confidencialidad transmisión Open Finance)` |
| SOL-22 | HU-ARQ-04 Gestión de Consentimientos | 5 | Alta | — |
| SOL-26 | HU-ARQ-05 Persistencia PostgreSQL + Redis | 5 | Media | — |
| SOL-29 | HU-ARQ-06 Tolerancia a Fallos y Failover | 13 | Alta | `Cubre ASR-3.1 (caída Redis) y ASR-3.2 (caída zona AWS)` |
| SOL-28 | HU-ARQ-07 Optimización Latencia Scoring | 8 | Alta | `Cubre ASR-1.1 (scoring carga normal) y ASR-1.2 (proveedor degradado)` |

---

## PASO 5 — Verificar priorización en el backlog

El board debe quedar ordenado así (de mayor a menor prioridad):

**Prioridad Alta (implementar semanas 3–6):**
1. HU-ARQ-07 Latencia scoring (ASR-1.1, 1.2)
2. HU-ARQ-06 Tolerancia a fallos / Failover (ASR-3.1, 3.2)
3. HU-ARQ-03 Tokenización PII (ASR-4.1)
4. HU-ARQ-11 Integridad pólizas (ASR-4.2) ← nueva
5. HU-ARQ-08 Event Bus Kafka ← nueva
6. HU-ARQ-09 Autoescalado horizontal ← nueva
7. HU-ARQ-01 Multitenant / Multirregión (ASR-2.2)
8. HU-ARQ-02 Pasarelas de pago (ASR-2.1)
9. HU-ARQ-04 Gestión de Consentimientos
10. FE-01 Cotización (Open Finance)
11. FE-02 Suscripción y emisión
12. FE-04 Gestión de siniestros web
13. FE-05 Autenticación biométrica

**Prioridad Media (semana 6–7 / stretch goals):**
14. FE-03 Administración de pólizas
15. FE-06 Billetera de pólizas
16. FE-07 Notificaciones
17. FE-08 Reporte siniestros evidencia
18. FE-09 Portal de socios ← nueva
19. HU-ARQ-05 Persistencia PostgreSQL + Redis
20. HU-ARQ-10 Offline sync BFF Móvil ← nueva

---

## Resumen de totales

| Acción | Cantidad |
|---|---|
| Épica nueva a crear | 1 (EP-05) |
| Historias nuevas a crear | 5 (FE-09 + HU-ARQ 08–11) |
| Historias existentes a actualizar (SP + prioridad + ASR) | 15 |
| **Total ítems a tocar en Jira** | **21** |
| Story points backlog total | 152 SP |
| Capacidad restante del equipo | 120 SP |
| SP de alta prioridad (debe entrar sí o sí) | ~102 SP |
| SP de media prioridad (stretch goals) | ~50 SP |
