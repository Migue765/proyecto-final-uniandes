# Solventa: decisiones de la vista funcional

**Diagrama asociado:** [solventa_functional_view.drawio](solventa_functional_view.drawio)

## 1. Propósito

La vista funcional muestra cómo los actores acceden a Solventa, qué funciones ejecuta cada microservicio y cómo avanzan los recorridos mediante solicitudes síncronas, eventos y persistencia. Su foco es el comportamiento observable del sistema, no la infraestructura física ni el detalle interno de clases.

La estructura sigue la convención del ejemplo suministrado: canales a la izquierda, acceso y atributos significativos de arquitectura (ASR), plataforma de mensajería, microservicios y almacenes de datos.

## 2. Convenciones

| Representación | Significado |
|---|---|
| Contenedor azul claro | Canales y actores |
| Caja azul `component` | Microservicio o workload desplegable |
| Cuadrado blanco sobre el borde | Puerto (`Port`) de comunicación del componente |
| Círculo negro con barra (`●|`) | Indicador compuesto colocado sobre la línea; la barra forma parte visible del símbolo y señala el extremo receptor |
| Caja naranja | ASR, control transversal o sistema externo |
| Caja verde `queue` | Cola o suscripción asíncrona con retry y DLQ |
| Cilindro o carpeta morada | Base de datos o almacén administrado |
| Cilindro gris | Caché temporal no autoritativa |
| Línea azul continua | Solicitud síncrona con respuesta inmediata (`«sync»`), normalmente HTTPS/REST |
| Línea verde punteada | Publicación o consumo asíncrono de evento (`«event»`) mediante bus, cola o suscripción |
| Línea morada continua | Persistencia directa realizada por el propietario de la información (`«persistence»`) |
| Línea morada punteada | Construcción asíncrona de una proyección o modelo de lectura (`«projection»`) |
| Línea naranja punteada | Aplicación transversal de seguridad, certificado, firma o telemetría (`«security»` / `«telemetry»`) |
| Línea gris continua | Acceso a caché temporal no autoritativa (`«cache»`) |

Las líneas no usan puntas de flecha. La dirección se lee desde el puerto cuadrado del componente emisor hacia el indicador negro compuesto `●|`, colocado sobre la misma línea junto al puerto cuadrado del componente receptor: `□────────●|□`. El círculo y su barra se representan como una sola marca visual; el tramo posterior llega al puerto receptor. Esta regla se aplica a componentes, actores, controles ASR, colas, sistemas externos y almacenes de datos; ninguna relación termina directamente sobre la caja completa.

Los colores y patrones anteriores son una convención de esta vista, no una equivalencia normativa de UML. Por ello, cada relación conserva una etiqueta funcional y se recomienda incluir el estereotipo indicado cuando el diagrama se consulte sin color o se imprima en escala de grises.

Una cola se define por propósito o consumidor; no se conectan colas directamente entre sí. Los eventos se publican desde el productor y cada consumidor recibe una suscripción independiente.

### 2.1. Uso de puertos compartidos

Un puerto UML representa un punto lógico de interacción, no necesariamente un puerto TCP. Varias relaciones pueden compartirlo cuando exponen o consumen el mismo contrato, emplean la misma tecnología y tienen la misma modalidad de comunicación. Por ejemplo, varios consumidores pueden invocar una única API de consentimiento, o varios productores pueden publicar en el mismo destino de mensajería.

No se debe compartir un puerto cuando las relaciones representan contratos o modalidades diferentes. En particular, las solicitudes síncronas, suscripciones de eventos, persistencia, caché y controles ASR deben modelarse mediante puertos separados aunque la implementación utilice el mismo listener de red.

La vista separa por modalidad los puertos de Pólizas, Claims, Pagos, Perfilamiento y Validación de entradas. También separa las interfaces receptoras de Adaptadores externos, Claims, Cumplimiento, Gateway, Pólizas y Rating y ofertas. Un mismo puerto puede seguir atendiendo varios consumidores cuando comparten contrato y modalidad; no se crea un puerto distinto por consumidor.

## 3. Actores y acceso

| Actor | Fachada | Funciones principales |
|---|---|---|
| Web App | BFF Web | Cliente, consentimiento, cotización, pólizas y siniestros |
| Móvil App | BFF Móvil | Biometría, billetera offline, evidencia y FNOL |
| Socio embedded | API de Socios | Originación B2B, acuerdo, producto y consentimiento |
| Operación / Cumplimiento | Acceso controlado | Casos, fraude, auditoría y reportes |

API Gateway valida el token emitido mediante OIDC/OAuth 2.0 y enruta únicamente a BFF Web, BFF Móvil o API de Socios. Las fachadas adaptan la experiencia del canal, pero no contienen reglas actuariales, de siniestros o pagos.

## 4. Microservicios

Los once cuadros azules corresponden exactamente a los containers de aplicación de la vista de despliegue: tres fachadas y ocho workloads funcionales.

| Container | Microservicio | Funciones representadas |
|---|---|---|
| BFF Web | BFF Web | Componer respuestas para web y operación |
| BFF Móvil | BFF Móvil | Soportar biometría, evidencia y operación offline |
| API Socios | API de Socios | Versionar contratos, aplicar cuotas y aislar socios |
| Identidad | Consentimiento y KYC | Gestionar cliente, consentimiento y verificación |
| Cotización | Rating y ofertas | Cotizar, evaluar riesgo, calcular prima y aceptar oferta |
| Pólizas | Suscripción, emisión y ciclo de vida | Emitir, firmar, endosar, renovar y cancelar |
| Perfilamiento | Personalización y perfil de riesgo | Obtener señales, calcular scoring y explicar el resultado |
| Siniestros | Claims | Recibir FNOL, custodiar evidencia, evaluar y liquidar |
| Pagos | Cobros, pagos y recaudo | Crear órdenes idempotentes, ejecutar y conciliar |
| Cumplimiento | Fraude, analítica y auditoría | Evaluar fraude, escalar casos, auditar y reportar |
| Integraciones | Adaptadores externos | Normalizar proveedores, firmas, pagos, IoT y notificaciones |

Producto/Suscripción y Distribución siguen siendo fronteras lógicas en dominio y componentes, pero no aparecen como workloads separados porque el despliegue actual incorpora sus funciones en Rating y ofertas, Pólizas y API de Socios.

## 5. Comunicación síncrona

Se usa interacción síncrona cuando el actor necesita respuesta dentro del mismo recorrido:

- Las fachadas consultan Identidad, Cotización, Pólizas y Claims.
- Rating y ofertas obtiene el perfil vigente antes de decidir una oferta.
- Perfilamiento valida el consentimiento en Identidad.
- La aceptación de la oferta solicita decisión y emisión a Pólizas.
- Claims valida cobertura en Pólizas y solicita evaluación de fraude a Cumplimiento.
- Identidad, Perfilamiento, Pólizas y Pagos usan Adaptadores externos para aislar proveedores.

Las llamadas a terceros aplican timeout, reintento limitado, circuit breaker y degradación definida por negocio.

## 6. Comunicación asíncrona

| Cola o suscripción | Productor | Consumidor | Resultado funcional |
|---|---|---|---|
| Perfil | Perfilamiento | Rating y ofertas | Recalcular o actualizar el rating |
| Órdenes de pago | Pólizas / Claims | Pagos | Crear cobro o indemnización idempotente |
| Paramétricos | Validación de entradas | Claims | Automatizar el inicio o evaluación del siniestro |
| Resultados de pago | Pagos | Claims / Pólizas | Actualizar liquidación o cuota |
| Notificaciones | Pólizas / Pagos | Adaptadores externos | Despachar correo, SMS o push |
| Hechos auditables | Todos los workloads | Cumplimiento | Registrar, correlacionar y analizar actividad |

La entrega es al menos una vez. Los consumidores deben ser idempotentes y validar `eventId`, `schemaVersion`, `correlationId` y `causationId`. Cada cola aplica retry y DLQ sin convertir la DLQ en un almacén de auditoría.

### 6.1. Hechos auditables frente a métricas, logs y trazas

Los **hechos auditables** son evidencia funcional de acciones relevantes para el negocio, la seguridad o el cumplimiento. Permiten responder quién realizó una acción, qué cambió, sobre qué entidad, cuándo ocurrió y cuál fue el resultado. Algunos ejemplos son otorgar o revocar un consentimiento, emitir o cancelar una póliza, aprobar un siniestro, confirmar un pago o modificar información sensible. Se publican como eventos en la cola **Hechos auditables** y Cumplimiento los conserva en el Registro de Auditoría append-only, con controles de integridad, acceso y retención regulatoria.

Las **métricas, logs y trazas** son señales técnicas de observabilidad utilizadas para operar y diagnosticar el sistema:

| Señal | Pregunta principal | Ejemplos | Uso habitual |
|---|---|---|---|
| Métricas | ¿Cómo se comporta el sistema en conjunto? | Latencia, tasa de errores, solicitudes por segundo, profundidad de cola, uso de CPU | Tableros, alertas, capacidad y SLO/SLA |
| Logs | ¿Qué informó un componente durante su ejecución? | Error de validación, timeout de proveedor, inicio de un proceso, detalle técnico controlado | Diagnóstico, soporte y análisis de incidentes |
| Trazas | ¿Cómo recorrió una solicitud los componentes? | Spans de Gateway, BFF, microservicios, colas y adaptadores asociados a un `traceId` | Localizar latencia y fallos en recorridos distribuidos |

La diferencia principal es el propósito: un hecho auditable demuestra una acción de negocio y puede tener valor legal o regulatorio; una señal de observabilidad explica la salud y ejecución técnica del sistema. Un mismo recorrido puede producir ambos, pero uno no sustituye al otro. Por ejemplo, la emisión de una póliza genera un hecho auditable estable y, al mismo tiempo, métricas de latencia, logs técnicos y una traza distribuida. Las señales técnicas pueden muestrearse, agregarse o vencer según la política operativa; los hechos auditables requieren retención, inmutabilidad e integridad acordes con la regulación.

Ambos pueden compartir `correlationId` para facilitar la investigación, pero deben mantenerse separados. El Registro de Auditoría no almacena volcados de logs, y los logs no deben utilizarse como evidencia autoritativa ni contener secretos o datos personales innecesarios.

## 7. Datos

- **RDS/Aurora transaccional:** representa bases o esquemas aislados por dominio; no es una base compartida.
- **S3 Documentos y Evidencias:** conserva documentos firmados, evidencia, hash, versión, retención y cadena de custodia.
- **Registro de Auditoría:** persistencia append-only con correlación y hash encadenado.
- **Modelos de Lectura/Analítica:** proyecciones seudonimizadas, opcionales y reconstruibles.
- **Redis:** caché temporal; nunca constituye la única fuente de información crítica.

Solo el microservicio propietario modifica su información. Otros workloads reciben referencias, instantáneas o eventos y no acceden directamente a sus tablas.

## 8. Recorridos funcionales

1. **Cotización embebida:** Socio → API de Socios → Rating y ofertas → Perfilamiento → Identidad/consentimiento → oferta.
2. **Suscripción y emisión:** oferta aceptada → Pólizas → firma → `PólizaEmitida` → orden de cobro → notificación.
3. **Siniestro asistido:** Web/Móvil → Claims → Pólizas/cobertura → Cumplimiento/fraude → `SiniestroAprobado` → Pagos.
4. **Siniestro paramétrico:** proveedor IoT → validación de firma/esquema → cola Paramétricos → Claims → Pagos → notificación.
5. **Vida hipotecaria personalizada:** Rating → Perfilamiento → consentimiento → Open Finance/Open Data → scoring explicable → oferta.
6. **Ciclo de vida de póliza:** Pólizas → endoso/renovación/cancelación → cuotas y Pagos → ACORD/reaseguro → auditoría.

## 9. ASR transversales

- **Seguridad:** OIDC/OAuth 2.0, JWT, roles, scopes, MFA, TLS/mTLS y firma de callbacks.
- **Privacidad:** consentimiento vigente, finalidad, minimización y trazabilidad del tratamiento.
- **Disponibilidad:** multi-AZ, retry, DLQ, degradación y circuit breaker para terceros.
- **Escalabilidad:** colas para absorber picos y escalamiento independiente de workloads.
- **Observabilidad:** métricas, logs, trazas y `correlationId` de extremo a extremo.
- **Integridad:** idempotencia monetaria, validación de esquema, timestamp, hash y no repudio.

## 10. Alineación con otras vistas

- Los nombres de los once workloads coinciden con `solventa_deployment_view.drawio`.
- Las responsabilidades internas y contratos provienen de `solventa_component_model.drawio`.
- Los términos y propietarios de información se apoyan en `solventa_domain_model.drawio`.
- Las colas, clasificaciones y almacenes mantienen la semántica de `solventa_information_view.drawio`.

La vista funcional no introduce un nuevo microservicio, una base compartida ni un evento que contradiga las demás vistas.