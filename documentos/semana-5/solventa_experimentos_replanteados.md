# Solventa - Diseño de los cuatro experimentos arquitectónicos prioritarios

- **Versión:** 2.0
- **Fecha:** 13 de septiembre de 2026
- **Estado:** propuesta completa para ratificación y ejecución
- **Fuente canónica de requisitos:** [Los 10 ASR más críticos para el negocio](./catalogo_asr_solventa_replanteado.md)
- **Documento reemplazado conceptualmente:** [Diseño de experimentos v1.0](./solventa_experimentos.pdf)
- **Runbook de E1:** [Ejecución completa del experimento 1](../../docs/experimento-1/EJECUCION.md)

**Equipo responsable:** Jazmin Natalia Córdoba Puerto, Juan Esteban Mejía
Izasa, Miguel Alejandro Gómez Alarcón y Angie Natalia Arandio Niño.

## 1. Propósito y alcance

Este documento formaliza los cuatro experimentos seleccionados de los diez ASR prioritarios de Solventa. Mantiene la estructura del diseño de experimentos v1.0, pero corrige su trazabilidad: cada ensayo se asocia con un único ASR canónico y prueba un riesgo de negocio concreto, no la sola presencia de una tecnología.

| Orden | Experimento | ASR | Riesgo principal que se intenta refutar |
|---:|---|---|---|
| E1 | Elasticidad de cotización de 500 a 50.000 RPM | `ASR-ESC-01` | La plataforma no incorpora capacidad o no completa el pico dentro de latencia y error |
| E2 | Procesamiento de un evento paramétrico masivo | `ASR-EVT-01` | Se pierden eventos aceptados o se duplican Siniestros u órdenes de indemnización |
| E3 | Integridad ante resultados de pago ambiguos | `ASR-FIN-01` | Un timeout o reintento produce doble efecto financiero o pierde una confirmación |
| E4 | Continuidad ante Open Finance degradado | `ASR-EXT-01` | La falla externa derriba la venta o habilita un fallback vencido o no autorizado |

La selección combina impacto, incertidumbre técnica y posibilidad de obtener evidencia repetible sin depender de que un tercero real permita inducir fallas. No significa que los otros seis ASR dejen de ser obligatorios.

## 2. Convenciones de medidas y decisiones pendientes

Las etiquetas conservan el significado del catálogo canónico:

- **[CASO]:** medida explícita del enunciado de Solventa.
- **[DERIVADA]:** combinación directa de medidas del caso.
- **[EQUIPO]:** medida ya introducida por el equipo en entregables anteriores.
- **[PROPUESTA]:** precisión necesaria para hacer el ensayo falsable; debe ratificarse antes de la corrida oficial.
- **[PENDIENTE]:** decisión de negocio o técnica aún abierta; no puede presentarse como criterio aprobado.

Los cuatro experimentos deben declarar el denominador, la ventana temporal, la fuente de verdad y los instantes de inicio y fin. Una medida marcada como propuesta puede usarse en una calibración, pero no convertirse silenciosamente en compromiso del negocio.

## 3. Reglas comunes del banco de pruebas

1. Los contratos, identidades, perfiles, tarifas, consentimientos y operaciones pueden usar datos sintéticos. El recorrido no puede convertirse en un `no-op`: cálculo, serialización, persistencia, deduplicación y transiciones de estado deben seguir siendo deterministas y representativos.
2. Un actor externo puede sustituirse por un simulador controlado, pero el simulador debe conservar la semántica que el ASR necesita probar. El mock reemplaza al tercero, no a la propiedad de infraestructura bajo evaluación.
3. Los generadores y simuladores se ejecutan fuera de los recursos medidos del sistema bajo prueba y publican sus propias métricas. Sus límites no pueden confundirse con límites de Solventa.
4. La infraestructura que implementa la táctica evaluada debe ser real. Por ejemplo, E1 exige autoescalamiento real de pods y nodos; E2 exige retención durable real; E3 exige una restricción de idempotencia real; E4 exige caché, aislamiento y Circuit Breaker reales.
5. Cada experimento usa artefactos inmutables, configuración versionada y reloj sincronizado. La mezcla de datos y el costo sintético se congelan antes de comparar fases.
6. Se ejecutan tres corridas oficiales independientes. Cada corrida debe aprobar por separado; no se promedian percentiles ni se oculta una falla con las otras dos.
7. Todo `429`, timeout, error de conexión, respuesta `5xx` o respuesta `2xx` que incumpla el esquema de negocio cuenta como error.
8. La evidencia mínima incluye carga ofrecida, aceptada, rechazada y completada; percentiles; errores; métricas de infraestructura; eventos o efectos conciliados; configuración; commit; imágenes por digest; y tiempos de cada transición relevante.
9. Una corrida se aborta de forma controlada si continuar pone en riesgo la evidencia, excede las guardas de costo o mantiene una saturación sin recuperación. El aborto no borra los datos ya recogidos.
10. Generadores, simuladores y workers usan roles dedicados de mínimo privilegio y credenciales temporales. Los secretos se resuelven desde el mecanismo administrado correspondiente; nunca se versionan en Git ni se incluyen en JTL, logs, trazas o reportes.

## 4. Estado del laboratorio al redactar este documento

La infraestructura disponible hoy corresponde únicamente al baseline de E1. No debe presentarse como implementación de los cuatro experimentos ni como capacidad de 50.000 RPM.

| Estado | Elementos |
|---|---|
| **Levantado y verificado para el baseline de E1** | API Gateway REST regional con AWS IAM; VPC Link; NLB interno; EKS 1.36; dos nodos fijos `c7i-flex.large`; Cotización y Perfilamiento con dos réplicas iniciales y HPA de 2 a 4; RDS PostgreSQL 15.19 Single-AZ; ElastiCache Redis OSS 7.1 de un nodo con TLS y AUTH; WireMock; CloudWatch; trazado de API Gateway; datos sintéticos y smoke test exitoso |
| **No levantado para E1 completo** | Cuota de ingreso suficiente para aproximadamente 842 RPS ofrecidos; generadores distribuidos; autoescalamiento de nodos; capacidad caliente; dimensionamiento de RDS y Redis para 50.000 RPM; topología final para el pico |
| **No levantado para E2** | Ingreso paramétrico, broker durable, DLQ, consumidores de Claims, inbox/deduplicación, conciliador y servicios internos necesarios para producir el resultado de negocio |
| **No levantado para E3** | Servicio de Pagos con ledger e idempotencia, conciliador, simulador persistente de pasarela y mecanismo de inyección de cortes posteriores al procesamiento |
| **No levantado para E4** | Contrato de fallback gobernado, metadatos de frescura y consentimiento, Bulkhead, Circuit Breaker y simulador de degradación con la matriz completa de fallas |

---

## Experimento 1 - Elasticidad de cotización de 500 a 50.000 RPM

### 1.1 Ficha principal

| Campo | Definición |
|---|---|
| **Título del experimento** | E1. Elasticidad de cotización de 500 a 50.000 solicitudes por minuto |
| **ASR evaluado** | `ASR-ESC-01` - Elasticidad de cotización de 500 a 50.000 RPM |
| **Propósito del experimento** | Validar que el recorrido de cotización multiplique cien veces su carga, incorpore capacidad dentro del tiempo acordado y complete el volumen objetivo sin pérdida silenciosa ni incumplir latencia y error. |
| **Resultados esperados** | **[CASO]** Completar al menos 50.000 cotizaciones en una ventana estable de 60 s y disponer de la capacidad adicional en `<= 60 s`. **[DERIVADA]** Mantener `p95 <= 250 ms` y `p99 <= 500 ms`. **[EQUIPO]** Mantener error técnico `< 1 %` en el pico. **[PROPUESTA]** Ofrecer al menos 50.506 solicitudes/min para poder completar 50.000 aun con hasta 1 % de error, informando por separado ofrecidas, aceptadas, rechazadas y completadas. |
| **Recursos requeridos** | JMeter 5.6.3 distribuido o generador equivalente; 50 socios y perfiles sintéticos; simulador contractual estable; API Gateway; balanceo privado; EKS; HPA; autoscaler de nodos; capacidad caliente; PostgreSQL; Redis; CloudWatch y trazas. La capacidad completa todavía debe dimensionarse a partir del baseline. |
| **Elementos de arquitectura involucrados** | Ingreso de socios, API de Socios, Cotización y Rating, Perfilamiento y Scoring, adaptador de Open Finance/Open Data, Redis, RDS/Aurora, EKS, HPA, plano de nodos y observabilidad. |
| **Actor externo simulado** | Los socios se sustituyen por generadores que usan una identidad IAM temporal controlada y una distribución de carga versionada. Open Finance/Open Data se sustituye por WireMock estable. Los simuladores deben quedar fuera del clúster medido para la corrida final. |
| **Esfuerzo estimado** | **[PROPUESTA]** 32 horas-persona: preparación 14 h, ejecución 8 h y análisis 10 h. No incluye tiempos de aprobación de cuotas ni espera de aprovisionamiento de AWS. |
| **Estado actual** | El baseline real de 500 RPM tiene infraestructura y servicios desplegados. El salto a 50.000 RPM, el autoscaling de nodos y la capacidad de datos para ese pico aún no están implementados ni validados. |

### 1.2 Hipótesis, sensibilidad e incertidumbre

> Si el recorrido usa escalamiento horizontal de pods y nodos, capacidad caliente, límites y depósitos dimensionados, caché no autoritativa y señales de escalamiento oportunas, entonces podrá pasar de 500 a 50.000 RPM y recuperar simultáneamente throughput, latencia y error en no más de 60 s.

| Elemento | Definición |
|---|---|
| **Punto de sensibilidad** | Capacidad inicial; señal y umbral del HPA; tiempo de aprovisionamiento de nodos; `requests/limits`; máximo de réplicas; capacidad del balanceador y API Gateway; depósitos HTTP/Redis/PostgreSQL; aciertos de caché; costo CPU por solicitud; distribución por socio; capacidad del generador. |
| **ASR e historia asociada** | Fuente canónica: `ASR-ESC-01`. El mapeo uno-a-uno a una historia Jira nueva está pendiente de aprobación; la referencia histórica `SOL-43` no sustituye el ASR replanteado. |
| **Nivel de incertidumbre** | **Muy alto.** El baseline prueba 500 RPM con nodos fijos. No existe evidencia de capacidad cien veces mayor, escalamiento de nodos, suficiencia de RDS/Redis ni oferta real de 842 RPS por el generador. |
| **Hipótesis que invalidaría el ensayo** | Asumir que HPA agrega nodos, multiplicar réplicas sin medir capacidad por pod, cambiar el cálculo sintético entre fases o tratar 500 RPM como prueba del objetivo final. |

### 1.3 Variables y fases del ensayo

| Tipo | Variable |
|---|---|
| **Independiente** | Tasa ofrecida: baseline de 500 RPM, escalones intermedios dimensionados y transición final a al menos 50.506 RPM ofrecidos. |
| **Dependientes** | Cotizaciones completadas por minuto, p50/p95/p99, error por clase, tiempo de elasticidad, réplicas deseadas/actuales/Ready, nodos Ready, CPU, memoria, conexiones, cache hit/miss, evictions y costo estimado por cotización. |
| **Controladas** | Contrato, mezcla y semilla de datos, 50 socios, cálculo sintético, versión de imágenes, TTL de caché, configuración de HPA/autoscaler, región, ventanas y política de reintento del cliente, que será cero durante la medición de capacidad. |
| **Fuentes de verdad** | JTL del generador; métricas de API Gateway y balanceador; Kubernetes; RDS; Redis; logs estructurados sin cuerpos ni secretos; y manifiesto firmado de configuración. |

Fases propuestas:

1. **Baseline:** ejecutar tres corridas a 500 RPM para medir capacidad por pod, latencia, error y consumo de RDS/Redis.
2. **Modelo de capacidad:** calcular la capacidad segura por réplica y dependencia dejando margen operativo; no extrapolar linealmente cuando aparezca contención.
3. **Preparación del pico:** elevar cuotas, desplegar generadores distribuidos, incorporar autoscaler de nodos y capacidad caliente, y redimensionar datos.
4. **Escalera de carga:** ejecutar escalones crecientes y detenerse ante saturación. Los escalones exactos se fijan con la medición de capacidad, no por intuición.
5. **Transición oficial:** estabilizar en 500 RPM, fijar la carga de ensayo final y medir el primer instante desde el cual una ventana completa de 60 s satisface throughput, latencia y error.
6. **Sostenimiento y enfriamiento:** mantener el pico durante la duración ratificada, volver a 500 RPM y comprobar recuperación estable sin pérdida de solicitudes.

### 1.4 Criterios de aceptación y refutación

| Medida | Criterio por corrida |
|---|---|
| Carga ofrecida | `>= 50.506 solicitudes/min` **[PROPUESTA]** y evidencia de que el generador no está saturado |
| Throughput de negocio | `>= 50.000 cotizaciones válidas completadas/min` **[CASO]** |
| Latencia estable | `p95 <= 250 ms` y `p99 <= 500 ms` **[DERIVADA]** |
| Error técnico | `< 1 %` **[EQUIPO]**; todos los errores se clasifican |
| Tiempo de elasticidad | `<= 60 s` desde que se fija la carga hasta el inicio de la primera ventana completa que cumple simultáneamente throughput, latencia y error **[PROPUESTA]** |
| Integridad | Cero solicitudes aceptadas que desaparezcan sin respuesta o estado terminal |
| Saturación | Ninguna saturación sostenida de nodos, conexiones, memoria o almacenamiento; umbrales exactos antes de la corrida **[PENDIENTE]** |
| Aislamiento por socio | Distribución y métricas por socio obligatorias; criterio cuantitativo de equidad **[PENDIENTE]** |

El ASR se refuta si falla cualquier umbral obligatorio, si el generador no demuestra la carga ofrecida, si la capacidad tarda más de 60 s o si la plataforma limita el tráfico sin contabilizarlo. Aprobar solo el baseline permite afirmar capacidad a 500 RPM, no elasticidad a 50.000 RPM.

### 1.5 Patrones de arquitectura asociados

| Patrón | Aplicación en el experimento |
|---|---|
| **P1 - Caché de perfiles con lectura anticipada** | Reduce consultas y llamadas externas durante el pico, sin convertir Redis en fuente autoritativa. |
| **P4 - Mamparo de aislamiento** | Separa depósitos y cuotas por dependencia y socio para evitar que una saturación consuma todo el recorrido. |
| **P12 - Autoescalado con comprobaciones de salud** | Añade pods sanos y capacidad de nodos; excluye instancias no Ready de la ruta. |
| **Microservicios por contexto de dominio** | Permite escalar Cotización y Perfilamiento sin replicar todos los contextos. |
| **Backpressure y load shedding explícito** | Protege dependencias cuando se alcanza un límite; todo rechazo debe medirse y cuenta como error para el criterio de negocio. |

### 1.6 Tácticas de arquitectura asociadas

| Táctica | Aplicación verificable |
|---|---|
| **Replicar horizontalmente** | Escalar pods de Cotización y Perfilamiento de acuerdo con RPS, concurrencia o CPU calibrada. |
| **Escalar el plano de nodos** | Agregar nodos mediante Karpenter, Cluster Autoscaler o EKS Auto Mode; el HPA por sí solo no cumple esta táctica. |
| **Mantener capacidad caliente** | Reservar capacidad suficiente para absorber el intervalo previo al alta de nodos. |
| **Reducir demanda computacional** | Usar caché y precálculo sin cambiar el cálculo sintético entre fases. |
| **Controlar y aislar recursos** | Definir cuotas, pools, límites, prioridades y distribución multi-AZ. |
| **Detectar saturación** | Medir carga ofrecida/aceptada/completada, latencia, error, CPU, memoria, conexiones, cache hit/miss y nodos/pods Ready. |

### 1.7 Componentes involucrados

| Componente o microservicio | Propósito y comportamiento esperado | Tecnología asociada |
|---|---|---|
| Generadores de socios | Ofrecer la tasa declarada, conservar la mezcla y medir su propia saturación | JMeter 5.6.3 distribuido o equivalente |
| API Gateway | Autenticar, aplicar políticas y admitir la tasa sin ocultar limitaciones | Amazon API Gateway REST, AWS IAM |
| Balanceo privado | Distribuir únicamente a destinos saludables | VPC Link, NLB/ALB interno según diseño aprobado |
| Cotización y Rating | Componer la prima con cálculo determinista y escalar de forma independiente | Python 3.11, Flask, Gunicorn, EKS |
| Perfilamiento y Scoring | Resolver el perfil por caché/fuente controlada y escalar independientemente | Python 3.11, Flask, Gunicorn, EKS |
| Redis | Servir perfiles vigentes con latencia estable y sin evictions no explicadas | ElastiCache Redis OSS 7.x |
| PostgreSQL | Mantener tarifas y datos transaccionales sin agotar conexiones | Amazon RDS/Aurora PostgreSQL 15 |
| Adaptador y proveedor simulado | Conservar el contrato externo estable y evitar que el tercero real sesgue la medición | httpx, WireMock |
| Autoscaling | Aumentar pods y nodos dentro del tiempo objetivo | HPA más autoscaler de nodos por seleccionar |
| Observabilidad | Correlacionar ingreso, servicios, datos y decisiones de escalamiento | CloudWatch, métricas Kubernetes y trazas |

### 1.8 Conectores involucrados

| Conector | Comportamiento deseado | Tecnología asociada |
|---|---|---|
| Generadores -> API Gateway | Firmar, ofrecer y contabilizar tráfico de 50 socios | HTTPS REST, SigV4, TLS |
| API Gateway -> Balanceo -> Cotización | Transportar el pico sin cuello oculto ni pérdida de códigos de respuesta | VPC Link, HTTP persistente |
| Cotización -> Perfilamiento | Respetar el presupuesto interno durante el escalamiento | HTTP persistente, httpx |
| Cotización/Perfilamiento -> PostgreSQL | Usar pools acotados y exponer saturación | TLS, SQL, psycopg |
| Perfilamiento -> Redis | Resolver hits y misses con pools acotados | TLS, RESP, redis-py |
| Perfilamiento -> Adaptador -> WireMock | Usar contrato determinista; no amplificar el pico | HTTP, httpx, WireMock |
| HPA/autoscaler -> EKS/EC2 | Convertir señales observables en pods y nodos Ready | Kubernetes Metrics API y servicio de autoscaling elegido |

### 1.9 Tecnologías y justificación

| Categoría | Tecnología | Justificación |
|---|---|---|
| Lenguaje y framework | Python 3.11, Flask, Gunicorn | Mantiene los servicios instrumentados ya implementados para el baseline. |
| Plataforma | Docker, Amazon EKS, HPA y autoscaler de nodos | Permite medir elasticidad real de cómputo; el autoscaler de nodos está pendiente. |
| Ingreso | API Gateway, VPC Link y balanceo interno | Ejerce el camino externo real y sus cuotas. |
| Datos | RDS/Aurora PostgreSQL y ElastiCache Redis | Permite detectar límites de persistencia, pools y caché administrada. |
| Carga y mocks | JMeter, WireMock | Genera la carga reproducible y aísla dependencias externas. |
| Observabilidad | CloudWatch, métricas Kubernetes y trazas | Permite medir el reloj de elasticidad y localizar el cuello de botella. |

### 1.10 Distribución de actividades y esfuerzo

| Integrante | Tareas a realizar | Esfuerzo propuesto |
|---|---|---:|
| Jazmin Natalia Córdoba Puerto | Coordinar umbrales, ventana, riesgo, costo y acta de resultados | 5 h |
| Juan Esteban Mejía Izasa | Versionar contratos/datos y preparar los generadores distribuidos y WireMock | 8 h |
| Miguel Alejandro Gómez Alarcón | Dimensionar cuotas, HPA, autoscaler, capacidad caliente y observabilidad | 11 h |
| Angie Natalia Arandio Niño | Ejecutar corridas, validar respuestas y conciliar carga ofrecida/completada | 8 h |
| **Total** |  | **32 h** |

---

## Experimento 2 - Procesamiento confiable de un evento paramétrico masivo

### 2.1 Ficha principal

| Campo | Definición |
|---|---|
| **Título del experimento** | E2. Recepción, procesamiento y conciliación de un millón de eventos paramétricos |
| **ASR evaluado** | `ASR-EVT-01` - Procesamiento confiable de un evento paramétrico masivo |
| **Propósito del experimento** | Validar que una ráfaga con duplicados, reentregas y desorden se conserve, procese y concilie hasta resultados terminales sin duplicar Siniestros u órdenes de indemnización, mientras venta y consulta siguen activas. |
| **Resultados esperados** | **[CASO]** Absorber al menos 1.000.000 de eventos en `<= 10 min`, con contrapresión y sin pérdida. **[PROPUESTA]** Dentro de `<= 15 min` después del fin del ingreso, el 100 % de eventos válidos aceptados llega a un resultado terminal; cada inválido queda rechazado o en una cola reparable auditable. **[PROPUESTA]** Cero Siniestros u órdenes de indemnización duplicados por un mismo evento lógico. |
| **Recursos requeridos** | Productor sintético determinista; ingreso autenticado; buffer/broker durable; particiones; consumidores; inbox; outbox; retry y DLQ; Claims; Pagos; persistencia; conciliador; carga de control para venta; CloudWatch y métricas de lag. Ninguno de estos componentes específicos de E2 está levantado todavía. |
| **Elementos de arquitectura involucrados** | Adaptador IoT/Paramétricos, validador de eventos/callbacks, cola de entrada paramétrica, Event Bus y DLQ, Evaluación y Liquidación, Claims, Órdenes Idempotentes, Transacciones y Conciliación, persistencia de Siniestros/Pagos y observabilidad. |
| **Actor externo simulado** | El proveedor climático, de vuelos o telemetría se reemplaza por un productor con semilla fija capaz de generar eventos únicos, duplicados, desorden, ráfagas y reentregas. La pasarela de indemnización se reemplaza por un ledger simulado consultable. |
| **Esfuerzo estimado** | **[PROPUESTA]** 28 horas-persona: preparación 12 h, ejecución 7 h y análisis 9 h. No incluye el aprovisionamiento inicial del broker si requiere aprobación de cuotas. |
| **Estado actual** | Diseño propuesto. La infraestructura y los servicios de E2 no están desplegados; EKS, RDS y observabilidad de E1 son activos reutilizables, no evidencia de este ASR. |

### 2.2 Hipótesis, sensibilidad e incertidumbre

> Si el ingreso conserva durablemente cada evento aceptado, el broker aplica contrapresión, los consumidores son idempotentes y el sistema concilia cada identidad lógica contra un resultado de negocio, entonces un millón de eventos podrá absorberse en diez minutos sin pérdida ni efectos duplicados.

| Elemento | Definición |
|---|---|
| **Punto de sensibilidad** | Número de particiones; clave de partición; capacidad y retención del broker; tamaño de lote; tasa del productor; límite de lag; cantidad de consumidores; tiempo de procesamiento; commits de offsets; pools de datos; política de retry/DLQ; velocidad de drenaje. |
| **ASR e historia asociada** | Fuente canónica: `ASR-EVT-01`. La asociación histórica del experimento v1.0 con ASR de rendimiento/batch queda eliminada. El mapeo Jira nuevo está pendiente. |
| **Nivel de incertidumbre** | **Muy alto.** Recibir un mensaje no demuestra su efecto. Se desconoce si el diseño mantiene identidad, durabilidad e idempotencia hasta Siniestros y Pagos ni si el backlog converge. |
| **Hipótesis que invalidaría el ensayo** | Contar solo mensajes publicados, confirmar offsets antes del efecto durable, ignorar DLQ/rechazos, comparar únicamente filas internas o no medir duplicados en la orden de indemnización. |

### 2.3 Variables y fases del ensayo

| Tipo | Variable |
|---|---|
| **Independientes** | Tasa de ingreso hasta 1.000.000/10 min; proporción versionada de duplicados, reentregas, desorden e inválidos; pausa controlada de consumidores; concurrencia de tráfico online. |
| **Dependientes** | Ofrecidos, admitidos, persistidos, rechazados, DLQ, resultados terminales, lag por partición, tiempo de drenaje, reintentos, Siniestros únicos, órdenes únicas, latencia/error del tráfico online y saturación. |
| **Controladas** | Semilla y distribución de eventos, `externalEventId`, clave de partición, reglas paramétricas, versión de pólizas, cálculo de liquidación, recursos, imágenes y política de retry. |
| **Fuentes de verdad** | Manifiesto del productor; log/almacenamiento de entrada aceptada; offsets y métricas del broker; inbox; tablas de Siniestros/Pagos; ledger de indemnización simulado; DLQ; reporte de conciliación. |

Fases propuestas:

1. Sembrar pólizas sintéticas y generar un manifiesto con el resultado esperado por `externalEventId`.
2. Ejecutar control sin fallas y confirmar la relación uno-a-uno entre identidad lógica y resultado.
3. Iniciar tráfico online de control a una tasa ratificada y estabilizar sus percentiles.
4. Ofrecer el millón de eventos durante diez minutos con la mezcla congelada de únicos, duplicados, desorden e inválidos.
5. Pausar consumidores durante una ventana controlada para ejercer contrapresión y reanudarlos sin perder lo aceptado.
6. Drenar el backlog y conciliar manifiesto, ingreso, inbox, Siniestros, órdenes de indemnización, ledger y DLQ.
7. Repetir tres veces desde un conjunto limpio de identificadores, sin borrar evidencia de corridas anteriores.

### 2.4 Criterios de aceptación y refutación

| Medida | Criterio por corrida |
|---|---|
| Ingreso | `>= 1.000.000` eventos aceptados en `<= 10 min` **[CASO]** |
| Pérdida | Cero eventos válidos aceptados sin resultado terminal o clasificación reparable |
| Duplicidad | Cero Siniestros y cero órdenes de indemnización duplicados por `externalEventId` **[PROPUESTA]** |
| Convergencia | 100 % de válidos aceptados terminales en `<= 15 min` después del fin del ingreso **[PROPUESTA, PENDIENTE de ratificación]** |
| Inválidos | 100 % rechazado explícitamente o enviado a DLQ reparable con causa y correlación |
| Contrapresión | La pausa aumenta lag sin pérdida; al reanudar, el lag converge a cero dentro del plazo |
| Tráfico online | Continúa activo; tasa y degradación máxima frente al control **[PENDIENTE]** |
| Contabilidad | `ofrecidos = no admitidos + aceptados`; `aceptados = terminales + reparables pendientes`, sin categorías silenciosas |

El ASR se refuta ante un evento aceptado perdido, un solo efecto de negocio duplicado, una identidad sin conciliación, un backlog que no converge o evidencia incompatible entre productor, broker y dominios.

### 2.5 Patrones de arquitectura asociados

| Patrón | Aplicación en el experimento |
|---|---|
| **P8 - Publicación y suscripción de eventos de dominio** | Desacopla ingreso y consumo, retiene eventos y permite relectura. |
| **Buffer durable** | Absorbe la ráfaga sin exigir que Claims y Pagos procesen a la misma tasa instantánea. |
| **Consumidor idempotente e Inbox** | Deduplica por `externalEventId` antes de producir un efecto. |
| **Transactional Outbox** | Publica hechos de dominio sin una brecha entre commit local y mensajería. |
| **P4 - Mamparo de aislamiento** | Evita que consumidores o conciliación agoten los recursos de venta. |
| **Retry con DLQ reparable** | Retiene fallas recuperables con causa y herramienta de reproceso auditado. |

### 2.6 Tácticas de arquitectura asociadas

| Táctica | Aplicación verificable |
|---|---|
| **Aplicar contrapresión** | Reducir o pausar admisión antes de perder mensajes; contabilizar rechazos. |
| **Particionar y paralelizar** | Distribuir por clave de negocio estable sin romper el orden requerido por póliza/evento. |
| **Conservar lo aceptado** | Persistir durablemente antes del acuse y mantener retención suficiente para el peor backlog. |
| **Prevenir duplicados** | Aplicar restricción única e inbox antes de crear Siniestro u orden. |
| **Retener y reintentar** | Confirmar offset solo después del efecto durable; enviar fallas agotadas a DLQ. |
| **Escalar por lag** | Aumentar consumidores por profundidad/edad del backlog, no solo por CPU. |
| **Conciliar extremo a extremo** | Comparar eventos aceptados con resultados terminales, no solo con offsets. |

### 2.7 Componentes involucrados

| Componente o microservicio | Propósito y comportamiento esperado | Tecnología asociada |
|---|---|---|
| Productor paramétrico | Emitir la población determinista y probar su tasa | Python/Java o JMeter; ejecución separada |
| Ingreso IoT/Paramétrico | Autenticar, validar esquema e identificar cada evento | API Gateway y adaptador dedicado |
| Broker durable | Retener, particionar y exponer lag/offsets | Amazon MSK/Kafka u opción durable aprobada; por desplegar |
| Event Bus y DLQ | Transportar hechos y aislar fallas agotadas | Topics/colas versionados y DLQ |
| Claims - Evaluación y Liquidación | Determinar cobertura y crear un único Siniestro por identidad | Servicio en EKS; por implementar |
| Pagos - Órdenes Idempotentes | Crear una única orden de indemnización por resultado elegible | Servicio en EKS; por implementar |
| Inbox/Outbox | Cerrar brechas de deduplicación y publicación | PostgreSQL, restricciones únicas |
| Conciliador | Clasificar aceptados, terminales, rechazados y reparables | Worker de conciliación |
| Ledger de pasarela simulado | Registrar efectos externos observables por referencia | Simulador persistente controlado |
| Observabilidad | Medir tasa, lag, edad, drenaje, duplicados y saturación | CloudWatch y exportadores del broker |

### 2.8 Conectores involucrados

| Conector | Comportamiento deseado | Tecnología asociada |
|---|---|---|
| Productor -> Ingreso | Ofrecer eventos únicos/duplicados/desordenados y obtener acuse inequívoco | HTTPS, contrato versionado |
| Ingreso -> Broker | Confirmar solo después de aceptación durable | Productor Kafka o conector durable |
| Broker -> Consumidor Claims | Entrega al menos una vez con clave y correlación preservadas | Consumer group, offsets |
| Claims -> PostgreSQL/Outbox | Persistir inbox, Siniestro y evento de salida en transacción local | SQL, psycopg |
| Outbox -> Broker -> Pagos | Publicar la orden sin duplicar el resultado | Kafka/MSK, clave lógica |
| Pagos -> Ledger simulado | Propagar idempotencia y registrar un único efecto | HTTPS, simulador persistente |
| Fallas agotadas -> DLQ -> Reparador | Conservar causa, payload permitido y trazabilidad de reproceso | DLQ y worker controlado |
| Conciliador -> fuentes de verdad | Comparar manifiesto, offsets, bases y ledger | Consultas de solo lectura |

### 2.9 Tecnologías y justificación

| Categoría | Tecnología propuesta | Justificación |
|---|---|---|
| Servicios y workers | Python 3.11 en EKS | Permite instrumentar consumidores, deduplicación y conciliación. |
| Mensajería | Amazon MSK/Kafka o servicio durable equivalente aprobado | Proporciona particiones, retención, relectura y lag observables. La decisión final está pendiente. |
| Persistencia | PostgreSQL 15 | Implementa inbox/outbox, restricciones únicas y fuentes de conciliación. |
| Simulación | Productor determinista y ledger persistente | Elimina dependencia de clima/vuelos/pasarela reales sin perder la semántica relevante. |
| Carga concurrente | JMeter 5.6.3 | Mantiene un journey online de control mientras se procesa el evento masivo. |
| Observabilidad | CloudWatch, métricas del broker y reportes SQL | Correlaciona ingreso, lag, resultados y saturación. |

### 2.10 Distribución de actividades y esfuerzo

| Integrante | Tareas a realizar | Esfuerzo propuesto |
|---|---|---:|
| Jazmin Natalia Córdoba Puerto | Ratificar resultados terminales, ventana de reparación y criterios del tráfico online | 5 h |
| Juan Esteban Mejía Izasa | Implementar productor determinista, contratos y ledger de pasarela simulado | 6 h |
| Miguel Alejandro Gómez Alarcón | Diseñar broker, particiones, autoscaling por lag, observabilidad y guardas de capacidad | 9 h |
| Angie Natalia Arandio Niño | Preparar datos, ejecutar escenarios y construir conciliación extremo a extremo | 8 h |
| **Total** |  | **28 h** |

---

## Experimento 3 - Integridad ante resultados de pago ambiguos

### 3.1 Ficha principal

| Campo | Definición |
|---|---|
| **Título del experimento** | E3. Idempotencia y conciliación de cobros o indemnizaciones con respuesta ambigua |
| **ASR evaluado** | `ASR-FIN-01` - Integridad ante un resultado de pago ambiguo |
| **Propósito del experimento** | Validar que una operación lógica produzca exactamente un efecto financiero cuando la pasarela procesa la solicitud, pero la respuesta se pierde, llega tarde o coincide con reintentos concurrentes. |
| **Resultados esperados** | Sobre 10.000 operaciones lógicas **[EQUIPO]**: **[PROPUESTA]** cero efectos duplicados; **[CASO]** cero confirmaciones perdidas; **[PROPUESTA]** el 100 % de reintentos con la misma clave recupera la misma referencia y resultado; y toda operación ambigua converge a confirmada o rechazada en `<= 60 s` **[EQUIPO, PENDIENTE de ratificación]**. |
| **Recursos requeridos** | Generador concurrente; claves de idempotencia; Pagos/Recaudo; PostgreSQL; restricción única; máquina de estados; adaptador; conciliador; simulador de pasarela con ledger persistente; Toxiproxy o proxy de fallas; Event Bus para hechos; auditoría, CloudWatch y trazas. Estos componentes aún no están levantados para E3. |
| **Elementos de arquitectura involucrados** | Órdenes Idempotentes, Transacciones y Conciliación, adaptador de Pasarelas de Pago, persistencia de Pagos, Event Bus y DLQ, Auditoría y, cuando sea primer cobro, Gestor del Proceso de Emisión. |
| **Actor externo simulado** | La pasarela se reemplaza por un simulador con ledger persistente y consulta por referencia. Debe poder ejecutar primero y cortar después, rechazar, responder tarde y reutilizar una clave. |
| **Esfuerzo estimado** | **[PROPUESTA]** 24 horas-persona: preparación 10 h, ejecución 6 h y análisis 8 h. |
| **Estado actual** | Diseño propuesto. E1 no contiene un servicio financiero; RDS levantado para cotización no constituye evidencia de idempotencia ni conciliación de pagos. |

### 3.2 Hipótesis, sensibilidad e incertidumbre

> Si Pagos registra de forma atómica la clave y el estado local, bloquea efectos concurrentes, propaga la misma referencia externa y consulta o concilia antes de repetir una operación ambigua, entonces cada operación lógica producirá exactamente un efecto en el ledger externo simulado.

| Elemento | Definición |
|---|---|
| **Punto de sensibilidad** | Alcance y vencimiento de la clave; hash del payload; restricción única; orden entre commit y llamada; transiciones permitidas; locks; timeout; cantidad y separación de reintentos; consulta externa; callbacks tardíos; frecuencia del conciliador. |
| **ASR e historia asociada** | Fuente canónica: `ASR-FIN-01`. La referencia histórica `SOL-114` sirve como antecedente, pero el mapeo Jira nuevo y su redacción final están pendientes. |
| **Nivel de incertidumbre** | **Muy alto.** Un timeout no informa si la pasarela ejecutó. La base interna puede parecer correcta mientras el ledger externo contiene dos efectos o una confirmación no fue reconciliada. |
| **Precondición contractual** | El proveedor debe admitir idempotencia o consulta por referencia estable. Sin al menos una de las dos capacidades no puede garantizarse un único efecto después de perder la respuesta. |
| **Hipótesis que invalidaría el ensayo** | Comparar solo registros internos, hacer que el mock falle antes de procesar en todos los casos, no permitir reintentos concurrentes o usar una pasarela simulada sin ledger consultable. |

### 3.3 Variables y matriz de fallas

| Tipo | Variable |
|---|---|
| **Independientes** | Momento del corte; respuesta perdida/tardía; timeout; error transitorio; callback duplicado/desordenado; cantidad y concurrencia de reintentos; reutilización de clave con mismo o distinto payload. |
| **Dependientes** | Efectos por operación lógica en el ledger, estado interno, referencia externa, respuestas por clave, operaciones pendientes, tiempo de convergencia, reintentos, compensaciones y hechos auditables. |
| **Controladas** | Población de 10.000 operaciones, semilla, distribución de fallas, montos sintéticos, claves, versión de contrato, política de retry, configuración, imágenes y reloj. |
| **Fuentes de verdad** | Ledger persistente del simulador; tabla de idempotencia; intentos y estados de Pagos; hechos de auditoría; callbacks; reporte de conciliación. El ledger simulado, no la sola base interna, decide si hubo doble efecto. |

Matriz mínima de fallas:

1. Éxito normal.
2. Rechazo definitivo.
3. Timeout antes de que la pasarela procese.
4. La pasarela procesa y el proxy corta la respuesta.
5. Respuesta exitosa tardía después del timeout local.
6. Dos o más solicitudes concurrentes con la misma clave y el mismo payload.
7. Misma clave con payload diferente, que debe rechazarse de forma explícita.
8. Callback duplicado y callback fuera de orden.
9. Reinicio del servicio después de persistir estado local y antes de publicar el hecho.
10. Conciliación de una operación pendiente mediante consulta por referencia.

### 3.4 Criterios de aceptación y refutación

| Medida | Criterio por corrida |
|---|---|
| Población | 10.000 operaciones lógicas con distribución y semilla registradas **[EQUIPO]** |
| Efecto financiero | Exactamente un efecto en el ledger por operación confirmada; cero efectos para rechazadas definitivas **[PROPUESTA]** |
| Duplicados | Cero cobros o indemnizaciones duplicados |
| Confirmaciones | Cero transacciones confirmadas perdidas **[CASO]** |
| Reintentos equivalentes | 100 % devuelve la misma referencia y resultado terminal para la misma clave y payload **[PROPUESTA]** |
| Clave conflictiva | 100 % de reutilizaciones con payload diferente se rechaza y audita |
| Convergencia | 100 % de ambiguas llega a confirmada o rechazada en `<= 60 s` **[EQUIPO, PENDIENTE]** |
| Trazabilidad | Cada operación correlaciona solicitud lógica, intentos, referencia externa, callbacks, conciliación y efecto |

El ASR se refuta con un solo efecto duplicado, una confirmación perdida, resultados distintos para una misma operación equivalente, un estado interno que contradiga el ledger o una operación que exceda el tiempo ratificado sin estado terminal.

### 3.5 Patrones de arquitectura asociados

| Patrón | Aplicación en el experimento |
|---|---|
| **P5 - Puertos y adaptadores** | El núcleo consume un puerto estable sin depender del contrato particular del simulador o proveedor. |
| **Receptor idempotente por clave de negocio** | Registra una única operación y devuelve el mismo resultado a reintentos equivalentes. |
| **P3 - Tiempo de espera con reintento acotado** | Reintenta solo fallas transitorias y operaciones seguras, con límite, backoff y jitter. |
| **Máquina de estados monotónica** | Impide regresar desde un terminal o aplicar dos transiciones incompatibles. |
| **Transactional Outbox** | Publica el estado financiero sin brecha después del commit local. |
| **P8 - Publicación y suscripción** | Distribuye confirmaciones, auditoría y solicitudes de conciliación sin repetir el efecto sincrónico. |

### 3.6 Tácticas de arquitectura asociadas

| Táctica | Aplicación verificable |
|---|---|
| **Prevenir duplicados** | Restricción única por clave, hash de payload y exclusión de solicitudes concurrentes. |
| **Mantener atomicidad local** | Persistir clave, intento, referencia y transición en una transacción. |
| **Reintentar con seguridad** | Reutilizar la misma clave; reintentar solo cuando el contrato lo permita. |
| **Recuperar resultado ambiguo** | Consultar por referencia antes de emitir una nueva operación y conciliar pendientes. |
| **Procesar callbacks idempotentemente** | Deduplicar y validar transiciones frente a mensajes repetidos o fuera de orden. |
| **Registrar y correlacionar** | Trazar operación, intento, resultado, conciliación y efecto mediante un identificador común. |

### 3.7 Componentes involucrados

| Componente o microservicio | Propósito y comportamiento esperado | Tecnología asociada |
|---|---|---|
| Generador de operaciones | Crear claves/payloads y concurrencia reproducible | JMeter 5.6.3 o harness dedicado |
| Gestor del Proceso de Emisión | Solicitar el primer cobro una sola vez cuando aplique | Servicio de proceso/saga; por implementar |
| Pagos - Órdenes Idempotentes | Admitir, bloquear o reutilizar una operación lógica | Python 3.11, Flask/Gunicorn, EKS |
| Pagos - Transacciones y Conciliación | Mantener estados, consultar ambiguas y converger | Worker y scheduler de conciliación |
| Adaptador de Pasarela | Traducir autorizar, consultar y reversar sin perder la clave | Python 3.11, httpx |
| Pasarela simulada | Ejecutar escenarios y conservar un ledger externo consultable | Simulador dedicado/WireMock más ledger; Toxiproxy |
| PostgreSQL de Pagos | Persistir idempotencia, intentos y outbox con unicidad | RDS/Aurora PostgreSQL 15 |
| Event Bus y DLQ | Transportar hechos y fallas reparables | Tecnología durable por aprobar |
| Auditoría y Reportes | Reconstruir la secuencia completa | Registro append-only e índice consultable |

### 3.8 Conectores involucrados

| Conector | Comportamiento deseado | Tecnología asociada |
|---|---|---|
| Cliente/Emisión -> Pagos | Enviar clave estable y recuperar el mismo resultado | HTTPS REST, header de idempotencia |
| Pagos -> PostgreSQL | Crear/reutilizar clave y persistir transiciones atómicas | TLS, SQL, psycopg |
| Pagos -> Adaptador | Invocar un puerto estable sin duplicar solicitudes en curso | Interfaz interna, HTTP |
| Adaptador -> Proxy -> Pasarela simulada | Propagar clave y permitir corte después del procesamiento | HTTPS, httpx, Toxiproxy |
| Conciliador -> Pasarela | Consultar por referencia antes de repetir una ambigua | HTTPS REST |
| Pasarela -> Callback de Pagos | Entregar resultados tardíos o repetidos con firma simulada verificable | HTTPS webhook |
| Pagos -> Event Bus -> Auditoría | Publicar el resultado con la misma identidad lógica | Outbox, broker durable |

### 3.9 Tecnologías y justificación

| Categoría | Tecnología propuesta | Justificación |
|---|---|---|
| Servicios | Python 3.11, Flask, Gunicorn, httpx | Implementa Pagos, adaptador y conciliador instrumentados. |
| Persistencia | PostgreSQL 15 | Proporciona transacciones, unicidad, locks y outbox. |
| Simulación de proveedor | Simulador con ledger persistente, WireMock cuando aplique y Toxiproxy | Reproduce la ambigüedad crítica de ejecutar antes de cortar la respuesta. |
| Mensajería | Broker durable por aprobar | Conserva hechos de conciliación y auditoría sin redefinir el efecto financiero. |
| Carga y verificación | JMeter y pruebas automatizadas | Genera concurrencia y valida respuestas por clave. |
| Observabilidad | CloudWatch, trazas y consultas de conciliación | Correlaciona intentos internos con el ledger externo. |

### 3.10 Distribución de actividades y esfuerzo

| Integrante | Tareas a realizar | Esfuerzo propuesto |
|---|---|---:|
| Jazmin Natalia Córdoba Puerto | Ratificar estados terminales, fuente contable y plazo de convergencia | 4 h |
| Juan Esteban Mejía Izasa | Implementar adaptador, simulador persistente y contrato de idempotencia | 7 h |
| Miguel Alejandro Gómez Alarcón | Diseñar inyección de fallas, trazas, persistencia y conciliación | 7 h |
| Angie Natalia Arandio Niño | Preparar población, ejecutar concurrencia y conciliar ledger/estados | 6 h |
| **Total** |  | **24 h** |

---

## Experimento 4 - Continuidad ante proveedor Open Finance degradado

### 4.1 Ficha principal

| Campo | Definición |
|---|---|
| **Título del experimento** | E4. Fallback gobernado de perfilamiento ante Open Finance/Open Data lento o indisponible |
| **ASR evaluado** | `ASR-EXT-01` - Continuidad de venta ante proveedor de datos degradado |
| **Propósito del experimento** | Validar que una falla externa sostenida no consuma el presupuesto de cotización ni se propague, y que el journey continúe únicamente cuando exista un perfil en caché vigente, íntegro y autorizado. |
| **Resultados esperados** | **[CASO]** Presupuesto normal por dependencia `<= 120 ms`, timeout duro de 700 ms y disponibilidad del journey `>= 99,9 %` cuando el fallback sea aplicable, sin exceder el presupuesto total. **[EQUIPO]** `p95 < 200 ms` desde caché y cero solicitudes perdidas por timeout externo. **[PROPUESTA]** Cero perfiles vencidos o con consentimiento revocado; toda degradación marca `fallbackUsed`, edad, origen y causa. |
| **Recursos requeridos** | Generador; perfiles sintéticos; consentimiento versionado; Redis; Perfilamiento; Cotización/Rating; adaptador; WireMock; Toxiproxy; timeout; Circuit Breaker; Bulkhead; pools separados; métricas de fallback, frescura y estado del breaker. La versión completa no está levantada. |
| **Elementos de arquitectura involucrados** | API Gateway, Cotización, Rating y Evaluación, Orquestador/Motor de Perfil, Consentimientos y KYC, Redis, adaptador Open Finance/Open Data y observabilidad. |
| **Actor externo simulado** | Open Finance/Open Data se reemplaza por un simulador HTTP contractual con éxito, latencia, 4xx/5xx, timeout, corte, recuperación y versiones de datos. No se requiere intervención del proveedor real. |
| **Esfuerzo estimado** | **[PROPUESTA]** 20 horas-persona: preparación 8 h, ejecución 5 h y análisis 7 h. |
| **Estado actual** | E1 dispone de Redis y WireMock estable para el baseline, pero aún no implementa ni demuestra el contrato completo de frescura/consentimiento, Bulkhead, Circuit Breaker, degradación identificada y matriz de fallas de E4. |

### 4.2 Hipótesis, sensibilidad e incertidumbre

> Si Perfilamiento aplica un presupuesto menor que el presupuesto total, abre el Circuit Breaker ante falla sostenida, aísla la dependencia y permite fallback solo con un perfil vigente, íntegro y asociado a consentimiento válido, entonces la venta continuará sin propagar la degradación externa ni usar datos no autorizados.

| Elemento | Definición |
|---|---|
| **Punto de sensibilidad** | Presupuesto interno; timeout de conexión/lectura; umbral y ventana del breaker; duración de estado abierto; half-open; reintentos; tamaño del Bulkhead/pool; TTL y `validUntil`; versión de consentimiento; tasa de hits; estampida de caché; recuperación del proveedor. |
| **ASR e historia asociada** | Fuente canónica: `ASR-EXT-01`. La referencia histórica `SOL-37` es antecedente de calibración, pero el nuevo ASR evalúa el resultado y no la presencia de Redis/Circuit Breaker. |
| **Nivel de incertidumbre** | **Alto.** Un caché puede preservar latencia y a la vez violar vigencia o consentimiento. Además, esperar el timeout duro de 700 ms antes del fallback es incompatible con un p99 total de 500 ms. |
| **Límite del patrón** | El fallback aplica a proveedores de datos. No puede inventar confirmaciones de pago, firma o KYC ni sustituir una ausencia de consentimiento. |
| **Hipótesis que invalidaría el ensayo** | Precalentar toda la población y ocultarlo, usar perfiles sin metadatos de vigencia, medir solo latencia, tratar respuestas por defecto como datos válidos o esperar 700 ms antes de decidir el fallback. |

### 4.3 Variables y matriz de escenarios

| Tipo | Variable |
|---|---|
| **Independientes** | Latencia del proveedor; 4xx/5xx; timeout; corte; duración de falla; recuperación; estado del caché; frescura; integridad; versión de consentimiento; tasa de solicitudes. |
| **Dependientes** | Éxito del journey, p50/p95/p99, error, llamadas externas, tiempo de apertura/recuperación del breaker, ocupación del Bulkhead, fallback por causa, edad del perfil, usos bloqueados y saturación. |
| **Controladas** | Contrato y semilla, mezcla de perfiles, tasa, versión de código, TTL, presupuesto, política de reintento, consentimiento y cálculo de rating. |
| **Fuentes de verdad** | Registro autoritativo de consentimiento; metadatos/hash del perfil; Redis; contador del simulador; métricas del breaker/Bulkhead; respuesta de cotización; JTL y trazas. |

Matriz mínima:

1. Proveedor sano y caché hit vigente.
2. Proveedor sano y caché miss.
3. Latencia superior al presupuesto normal durante una falla sostenida y caché vigente.
4. Timeout/corte y caché vigente.
5. Error `5xx` y caché vigente.
6. Error `4xx` no reintentable.
7. Caché vencida durante falla externa: respuesta segura y explícita, nunca datos vencidos.
8. Consentimiento revocado durante falla: denegación incluso si existe caché.
9. Recuperación del proveedor y transición controlada `open -> half-open -> closed`.
10. Ráfaga concurrente sobre una misma clave para comprobar que no haya estampida de caché.

Los casos sin fallback válido son pruebas complementarias de seguridad. Deben fallar de forma explícita y dentro del presupuesto, pero no cuentan como solicitudes donde el fallback era aplicable para calcular el `>= 99,9 %`.

### 4.4 Criterios de aceptación y refutación

| Medida | Criterio por corrida |
|---|---|
| Presupuesto normal | La dependencia consume `<= 120 ms` en operación normal **[CASO]** |
| Timeout duro | Nunca supera 700 ms; no se espera este límite antes de un fallback cuando el journey tiene p99 de 500 ms **[CASO más restricción de diseño]** |
| Journey con fallback aplicable | Éxito `>= 99,9 %` sobre la población y ventana declaradas **[CASO, ventana PENDIENTE]** |
| Latencia desde caché | `p95 < 200 ms` **[EQUIPO]** y sin exceder el presupuesto total del journey |
| Pérdida por timeout externo | Cero solicitudes aceptadas perdidas **[EQUIPO]** |
| Gobierno del perfil | Cero usos de perfil vencido, corrupto, de otro sujeto o con consentimiento revocado **[PROPUESTA]** |
| Trazabilidad | 100 % de fallbacks identifica uso, edad, origen, versión de consentimiento y causa **[PROPUESTA]** |
| Aislamiento | La ocupación de la dependencia no agota trabajadores/pools del resto del journey |
| Recuperación | Breaker y tráfico regresan de forma controlada sin ráfaga de reintentos; plazo exacto **[PENDIENTE]** |

El ASR se refuta si la degradación agota el presupuesto, se propaga, produce pérdida silenciosa, usa un perfil no autorizado/vencido o si el porcentaje se calcula mezclando casos donde el fallback no era aplicable. Una prueba corta estima la tasa de éxito de su población; no demuestra por sí sola un SLO mensual de 99,9 %.

### 4.5 Patrones de arquitectura asociados

| Patrón | Aplicación en el experimento |
|---|---|
| **P5 - Puertos y adaptadores** | Aísla el contrato externo y permite simular estados sin cambiar el núcleo. |
| **P1 - Caché temporal no autoritativa** | Conserva perfiles vigentes con procedencia y autorización; nunca sustituye la fuente de verdad de consentimiento. |
| **Circuit Breaker** | Evita seguir consumiendo presupuesto ante falla sostenida y prueba la recuperación con half-open. |
| **P4 - Mamparo de aislamiento** | Separa workers/pools de la dependencia para que su saturación no agote la cotización. |
| **P3 - Timeout y reintento acotado** | Limita espera y reintenta solo dentro del presupuesto restante y con jitter. |
| **Fallback gobernado** | Decide con frescura, integridad, procedencia y consentimiento, no solo con existencia en caché. |

### 4.6 Tácticas de arquitectura asociadas

| Táctica | Aplicación verificable |
|---|---|
| **Limitar el tiempo de espera** | Definir budgets internos compatibles con el p99 total y un timeout duro como guarda final. |
| **Aislar la falla** | Bulkhead/pools separados y Circuit Breaker impiden que la dependencia agote recursos. |
| **Mantener redundancia temporal segura** | Usar perfil cacheado solo si `validUntil`, hash/procedencia y versión de consentimiento son válidos. |
| **Reintentar de forma presupuestada** | Reintentar únicamente transitorios y solo si queda tiempo; evitar tormentas. |
| **Degradar explícitamente** | Marcar `fallbackUsed`, causa, edad y origen en respuesta/telemetría. |
| **Detectar y recuperar** | Medir breaker, latencia, errores, ocupación, recuperación y estampida por clave. |

### 4.7 Componentes involucrados

| Componente o microservicio | Propósito y comportamiento esperado | Tecnología asociada |
|---|---|---|
| Generador de cotizaciones | Ejecutar la matriz con mezcla y tasa reproducibles | JMeter 5.6.3 |
| API Gateway/Cotización | Mantener ingreso y presupuesto extremo a extremo | API Gateway, servicio en EKS |
| Rating y Evaluación | Calcular la prima con origen de perfil explícito | Python 3.11, Flask/Gunicorn |
| Orquestador/Motor de Perfil | Validar consentimiento y frescura antes de usar el fallback | Python 3.11, Flask/Gunicorn |
| Consentimientos y KYC | Resolver la versión autorizativa aplicable | Servicio/registro autoritativo; por implementar para E4 |
| Redis | Almacenar temporalmente perfil, procedencia, versión y `validUntil` | ElastiCache Redis OSS 7.x |
| Adaptador Open Finance/Open Data | Aplicar timeout, Circuit Breaker, Bulkhead y normalización | httpx y librería de resiliencia instrumentada |
| Proveedor simulado | Reproducir éxito, demoras, fallas y recuperación | WireMock y Toxiproxy |
| Observabilidad | Correlacionar resultado, fallback y estado de la dependencia | CloudWatch, métricas y trazas |

### 4.8 Conectores involucrados

| Conector | Comportamiento deseado | Tecnología asociada |
|---|---|---|
| Generador -> API Gateway -> Cotización | Medir el journey completo y conservar códigos/esquemas | HTTPS REST, SigV4 |
| Cotización/Rating -> Perfilamiento | Propagar presupuesto y correlación | HTTP persistente, httpx |
| Perfilamiento -> Consentimientos | Validar versión vigente antes de caché o proveedor | API interna/consulta autoritativa |
| Perfilamiento -> Redis | Leer perfil y metadatos de gobierno de forma atómica | TLS, RESP, redis-py |
| Perfilamiento -> Adaptador | Transmitir deadline; no multiplicar reintentos | HTTP interno |
| Adaptador -> Toxiproxy -> WireMock | Inyectar latencia/corte y observar solicitudes reales | HTTP, Toxiproxy, WireMock |
| Servicios -> Observabilidad | Emitir origen, edad, causa, breaker y presupuesto consumido | Métricas, logs estructurados y trazas |

### 4.9 Tecnologías y justificación

| Categoría | Tecnología propuesta | Justificación |
|---|---|---|
| Servicios | Python 3.11, Flask, Gunicorn, httpx | Instrumenta budgets, metadatos y llamadas del recorrido. |
| Caché | ElastiCache Redis OSS 7.x | Ejerce el fallback sobre caché administrada real. |
| Simulación/fallas | WireMock y Toxiproxy | Reproduce contrato, latencia, corte y recuperación sin depender del proveedor. |
| Resiliencia | Circuit Breaker, Bulkhead, deadlines y retry acotado | Implementa la propiedad que el experimento debe comprobar. |
| Carga | JMeter 5.6.3 | Ejecuta poblaciones etiquetadas y recoge percentiles/errores. |
| Observabilidad | CloudWatch, métricas y trazas | Demuestra presupuesto consumido, estado del breaker y uso seguro del fallback. |

### 4.10 Distribución de actividades y esfuerzo

| Integrante | Tareas a realizar | Esfuerzo propuesto |
|---|---|---:|
| Jazmin Natalia Córdoba Puerto | Ratificar vigencia, ventana del 99,9 %, casos no aplicables y comunicación de degradación | 4 h |
| Juan Esteban Mejía Izasa | Implementar contrato del adaptador, WireMock/Toxiproxy y escenarios de recuperación | 5 h |
| Miguel Alejandro Gómez Alarcón | Configurar budgets, Circuit Breaker, Bulkhead, métricas y análisis de saturación | 6 h |
| Angie Natalia Arandio Niño | Preparar perfiles/consentimientos, ejecutar matriz y verificar usos indebidos | 5 h |
| **Total** |  | **20 h** |

---

## 5. Decisiones que deben cerrarse antes de las corridas oficiales

| Experimento | Decisión pendiente | Por qué bloquea una conclusión final |
|---|---|---|
| E1 | Duración del pico, escalones, capacidad inicial, aislamiento por socio y costo máximo | Sin estas decisiones no se distingue elasticidad sostenible de una ráfaga breve o costosa |
| E1 | Autoscaler de nodos, capacidad caliente, cuotas y dimensionamiento de datos | La infraestructura actual solo prueba el baseline |
| E2 | Resultado terminal, clave lógica, mezcla de fallas, backlog máximo y plazo de reparación | Sin identidad y conciliación no puede demostrarse ausencia de pérdida/duplicado |
| E2 | Tecnología/topología del broker y tasa online de control | Determinan retención, partición, lag y aislamiento reales |
| E3 | Fuente contable de verdad, estados terminales, precondición de consulta/idempotencia y plazo de 60 s | Sin ellos no hay oráculo para distinguir ambigüedad de duplicado o pérdida |
| E4 | Vigencia máxima, exactitud permitida, ventana del 99,9 %, deadline de fallback y recuperación | Sin gobierno temporal/autorizativo, una respuesta rápida puede ser incorrecta o ilegal |
| Todos | Guardas de costo y saturación, retención de evidencia y responsables de aprobación | Permiten abortar con seguridad y conservar una conclusión auditable |

## 6. Criterio de cierre del programa de experimentos

Cada experimento termina en uno de cuatro estados:

- **Aprobado:** las tres corridas cumplen todos los criterios ratificados y la evidencia se concilia.
- **Refutado:** al menos una corrida incumple un criterio obligatorio y el incumplimiento es atribuible al sistema bajo prueba.
- **Inconcluso:** el generador, simulador, observabilidad o una decisión pendiente impide evaluar el ASR.
- **Aprobación parcial:** solo se ejecutó una fase explícita, como el baseline de 500 RPM de E1; no autoriza afirmar cumplimiento del ASR completo.

El cierre debe registrar configuración, costos, limitaciones y cambios arquitectónicos recomendados. Tener EKS, Redis, PostgreSQL, una cola, un Circuit Breaker o una clave de idempotencia no constituye por sí solo evidencia. La evidencia existe cuando la táctica se ejerce bajo el estímulo, se mide contra la fuente de verdad y produce el resultado exigido por el ASR.
