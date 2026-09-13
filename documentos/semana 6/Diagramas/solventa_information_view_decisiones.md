# Solventa: decisiones de la vista de información

**Diagrama asociado:** [solventa_information_view.drawio](solventa_information_view.drawio)

## 1. Propósito y alcance

Esta vista explica qué información relevante maneja Solventa, qué contexto es su propietario, cómo cruza fronteras, cuál es su sensibilidad y qué reglas gobiernan su ciclo de vida. Complementa las demás vistas:

- El modelo de dominio define conceptos, agregados y reglas del negocio.
- La vista de información muestra propiedad, intercambio, clasificación, linaje y conservación.
- El modelo de componentes muestra qué unidades lógicas procesan esa información.
- La vista de despliegue muestra las tecnologías que la almacenan y protegen.

No es un modelo entidad-relación ni un diseño de tablas. Tampoco prescribe esquemas físicos, índices, particiones o nombres de bases de datos.

El diagrama se lee de izquierda a derecha y utiliza la estructura de integración solicitada:

1. **Fuentes y consumidores:** clientes, socios y proveedores externos que originan o reciben información.
2. **Controles de entrada y fachadas:** autenticación, API Gateway, BFF Web, BFF Móvil, API de Socios y validadores de datos, eventos y callbacks.
3. **Event Bus y colas:** canales asíncronos para familias de eventos, reintentos y DLQ.
4. **Servicios y contextos:** capacidades que validan, transforman y son propietarias de la información de dominio.
5. **Repositorios y productos de datos:** persistencia operacional aislada, documentos, registro de auditoría, analítica y caché.

## 2. Convenciones

| Representación | Significado |
|---|---|
| Caja amarilla | Fuente o consumidor de información |
| Caja naranja | Autenticación y autorización de acceso |
| Caja azul clara sin estereotipo | Validador de esquema, calidad, firma o procedencia |
| Caja verde `«queue»` | Cola asíncrona; incluye reintentos y envío a DLQ |
| Caja azul `«component»` | Servicio que procesa información; los nueve contextos son propietarios de sus datos |
| Cilindro o carpeta morada | Almacén lógico o producto derivado de datos |
| Cilindro gris | Caché temporal no autoritativa |
| Rótulo `RESTRINGIDO` | Información cuya exposición puede causar daño significativo o incumplimiento |
| Rótulo `CONFIDENCIAL` | Información contractual, financiera o comercial de acceso limitado |
| Rótulo `INTERNO` | Información operativa no destinada a publicación abierta |
| Línea roja punteada | Flujo con información restringida |
| Línea azul punteada | Solicitud, consulta o contrato de información |
| Línea verde punteada | Publicación o consumo mediante una cola |
| Línea morada continua | Persistencia o proyección hacia un almacén |

Las flechas indican dirección de transferencia, no propiedad compartida ni acceso directo a tablas. Las cajas verdes son siempre colas lógicas; los almacenes se muestran únicamente en morado. El rótulo de cada contexto señala su clasificación máxima, aunque algunos atributos puedan requerir controles menos restrictivos.

API Gateway y los validadores aparecen porque controlan la entrada y la calidad de la información. Gateway enruta únicamente hacia BFF Web, BFF Móvil o API de Socios; estas fachadas invocan los contextos autorizados y evitan exponerlos directamente. Los detalles de VPC, EKS, pods y protocolos internos continúan perteneciendo a la vista de despliegue.

El diagrama muestra los intercambios críticos para compra, emisión, siniestros y pagos. La conexión `hechos auditables` representa publicaciones de todos los servicios hacia su cola, aunque se agrupa visualmente para evitar cruces innecesarios.

Las colas se diseñan por consumidor o propósito para evitar competencia accidental entre dominios. `Resultados de Pago` agrupa visualmente dos suscripciones independientes: una para Siniestros y otra para Pólizas/Cuotas. Esta agrupación reduce ruido en el diagrama, pero no representa una única cola compartida por ambos consumidores.

El Event Bus contiene colas, suscripciones, reintentos y DLQ. El registro de auditoría es persistencia append-only administrada por Cumplimiento y Auditoría; no almacena mensajes pendientes ni sustituye una DLQ. Los modelos de lectura y analítica son un producto lógico opcional y reconstruible, no una base operacional exigida por la vista de despliegue actual.

## 3. Propiedad de la información

| Propietario | Información maestra | Clasificación máxima |
|---|---|---|
| Identidad y Cliente | Cliente, identidad, contacto y consentimiento | Restringido |
| Perfilamiento y Personalización | Perfil de riesgo, señales utilizadas, versión de modelo y explicación | Restringido |
| Producto y Suscripción | Producto, coberturas y reglas versionadas | Interno |
| Distribución | Socio distribuidor, acuerdo, comisión y cuota | Confidencial |
| Cotización | Oferta, coberturas cotizadas y evaluación de riesgo | Confidencial |
| Pólizas | Contrato, coberturas contratadas, beneficiarios, endosos y documento firmado | Restringido por PII; resto confidencial |
| Siniestros | Reporte, evidencias, cadena de custodia, fraude y decisión | Restringido |
| Pagos y Recaudo | Orden, transacción, referencia del proveedor y cuota de prima | Restringido |
| Cumplimiento y Auditoría | Casos KYC/AML/fraude y registros de auditoría | Restringido |

Solo el contexto propietario crea o modifica su información. Los demás contextos reciben identificadores, versiones, instantáneas o eventos mediante contratos; nunca consultan ni actualizan directamente sus tablas.

La caja `Bases transaccionales` representa el patrón común de almacenamiento aislado. No es una base compartida: cada contexto mantiene su propio esquema o base y aplica sus transacciones dentro de esa frontera. Integraciones y Notificaciones procesa referencias y mensajes, pero no es propietario maestro de información de negocio.

## 4. Instantáneas, referencias y linaje

- **Perfilamiento** conserva `perfilId`, fuentes usadas, consentimiento aplicable, versión del modelo, instante de cálculo y datos necesarios para explicar el resultado.
- **Cotización** conserva una instantánea de coberturas, prima, perfil y reglas utilizadas. Un cambio posterior del catálogo o del perfil no modifica una oferta ya calculada.
- **Pólizas** conserva las condiciones aceptadas y el documento firmado. Un cambio posterior en Producto no altera retroactivamente el contrato.
- **Siniestros** referencia la póliza y conserva la cobertura verificada, evidencias con hash, decisiones y evaluaciones que sustentaron la liquidación.
- **Pagos** conserva la referencia de negocio, clave de idempotencia, intentos y respuestas del proveedor. No replica innecesariamente el expediente del siniestro o el contrato.
- **Auditoría** registra actor, acción, recurso, instante, correlación y cadena de hashes sin convertirse en propietario de la información operativa auditada.

Estas instantáneas permiten reproducir decisiones sin depender del estado actual de otra frontera.

## 5. Intercambios principales

| Información o evento | Propietario | Receptor | Semántica |
|---|---|---|---|
| Cliente y consentimiento vigente | Identidad | Perfilamiento | Referencia mínima para autorizar el uso de señales |
| Perfil de riesgo versionado | Perfilamiento | Cotización | Referencia y resultado explicable usados por la oferta |
| Producto y reglas versionadas | Producto | Cotización | Condiciones utilizadas para rating y suscripción |
| Socio y acuerdo vigente | Distribución | Cotización | Origen, productos habilitados y condiciones comerciales |
| Oferta aceptada | Cotización | Pólizas | Instantánea contractual para emisión síncrona |
| Póliza y cobertura vigente | Pólizas | Siniestros | Referencia para validar amparo y límites |
| `PólizaEmitida` | Pólizas | Pagos | Genera cuotas u orden de cobro de forma idempotente |
| `SiniestroAprobado` | Siniestros | Pagos | Genera una orden de indemnización idempotente |
| `PagoConfirmado` / `PagoFallido` | Pagos | Siniestros | Actualiza el estado de liquidación |
| `PagoConfirmado` / `PagoFallido` | Pagos | Pólizas/Cuotas | Actualiza el estado de recaudo |
| Hecho auditable | Todos los contextos | Cumplimiento y Auditoría | Registro inmutable con correlación y versión |
| Verificación KYC/AML | Identidad | Integraciones y proveedor | Solicitud mínima y respuesta normalizada mediante adaptador |
| Cobro o desembolso | Pagos | Integraciones y proveedor | Operación idempotente con referencia externa |
| Firma / ACORD / reaseguro | Pólizas | Integraciones y proveedor | Contrato externo versionado y aislado del dominio |

`CotizaciónAceptada` puede publicarse para auditoría y analítica, pero la emisión se solicita sincrónicamente. El evento no vuelve a ordenar la creación de la póliza.

Los callbacks de proveedores se autentican y validan antes de llegar a Integraciones y Notificaciones. Este contexto adapta el protocolo externo, normaliza el resultado y lo entrega al contexto propietario; los proveedores no invocan directamente Pagos, Pólizas o Identidad.

## 6. Contratos de información

Todo evento debe contener como mínimo:

- `eventId` único.
- `eventType` y `schemaVersion`.
- `aggregateId` y tipo de agregado.
- `occurredAt` en UTC.
- `correlationId` y `causationId`.
- Identificador del productor.
- Carga mínima necesaria para el consumidor.

Los cambios incompatibles exigen una nueva versión del contrato. Los consumidores toleran campos adicionales, validan el esquema y son idempotentes porque la entrega es al menos una vez. Los eventos no transportan documentos, biometría, credenciales, PAN, CVV ni señales crudas si basta una URI autorizada o una referencia.

Cada cola dispone de política de reintentos y DLQ. Reprocesar un mensaje no puede duplicar una póliza, una orden de pago, un desembolso, una notificación ni un registro lógico de auditoría.

## 7. Clasificación y protección

### Restringido

Incluye documentos de identidad, biometría, contacto personal, señales de Open Finance/Open Data, KYC/AML, fraude, evidencias, beneficiarios y referencias de medios de pago. Requiere propósito válido, consentimiento cuando aplique, mínimo privilegio, cifrado, enmascaramiento y trazabilidad de acceso.

### Confidencial

Incluye cotizaciones, primas, contratos, acuerdos, comisiones, siniestros y decisiones económicas. Requiere control de acceso por rol, segregación de funciones y protección contra exposición en logs o exportaciones.

### Interno

Incluye catálogos, tarifas, parámetros, reglas de suscripción, metadatos operativos y contratos de eventos. No se publica sin aprobación del propietario. Una regla puede elevarse a confidencial si revela estrategia comercial o actuarial.

Los secretos técnicos, tokens de acceso y llaves criptográficas no son información de dominio. Se administran mediante Secrets Manager y KMS según la vista de despliegue.

## 8. Privacidad y minimización

- El consentimiento registra alcance, finalidad, vigencia, otorgamiento y revocación.
- Autenticación valida identidad, roles y scopes técnicos; Identidad y Cliente conserva y decide la vigencia del consentimiento de negocio.
- Perfilamiento usa únicamente fuentes cubiertas por un consentimiento vigente.
- La revocación impide usos futuros, sin borrar evidencia necesaria para demostrar tratamientos previos legítimos.
- Los consumidores reciben solo los atributos necesarios para su finalidad.
- Analítica y pruebas usan datos anonimizados, seudonimizados o sintéticos cuando sea posible.
- Pagos almacena tokens y referencias del proveedor; Solventa no conserva PAN ni CVV.
- Logs, trazas y DLQ no deben exponer cargas restringidas sin enmascaramiento.

## 9. Ciclo de vida y retención

1. **Creación:** validar calidad, procedencia, finalidad y consentimiento.
2. **Uso:** propagar clasificación, propietario, versión y correlación.
3. **Conservación:** aplicar la política contractual, fiscal, aseguradora y regulatoria correspondiente.
4. **Archivo:** restringir modificación y acceso cuando la información deja de ser operativa.
5. **Disposición:** eliminar o anonimizar al vencer la retención, salvo bloqueo por investigación, litigio o regulación.

No se fijan períodos numéricos en esta vista porque deben ser aprobados por negocio, legal y cumplimiento. Cada categoría requiere una tabla de retención implementable y verificable. Evidencias, documentos firmados y auditoría pueden estar sujetos a retención legal y bloqueo de eliminación.

## 10. Integridad, disponibilidad y recuperación

- Las operaciones monetarias usan `idempotencyKey` y una restricción única o mecanismo equivalente.
- Los registros de auditoría son append-only y encadenan hashes para detectar alteraciones.
- Evidencias y documentos conservan hash, versión, metadatos de origen y cadena de custodia.
- RDS/Aurora mantiene persistencia aislada por dominio, cifrado, backups y PITR.
- S3 conserva evidencias y documentos con cifrado, versionado, retención y réplica.
- Redis es caché temporal; nunca es la única fuente de información crítica.
- Los modelos de lectura y analítica son proyecciones opcionales y reconstruibles desde contratos gobernados del Event Bus; no sustituyen al `system of record` ni obligan a desplegar un almacén analítico en esta etapa.
- La réplica regional y los procedimientos de failover deben satisfacer los RPO/RTO aprobados y probarse periódicamente.

La tecnología concreta se muestra en la vista de despliegue; aquí se documentan las propiedades que esa tecnología debe garantizar.

## 11. Calidad de datos

- Identificadores globalmente únicos y tipos explícitos para dinero, fechas y porcentajes.
- Instantes en UTC y zona horaria conservada cuando tenga significado legal.
- Moneda obligatoria en todo valor monetario.
- Catálogos y reglas con versión y vigencia temporal.
- Referencias externas acompañadas por proveedor y estado de verificación.
- Validaciones de completitud, unicidad, rango y transición de estado en el contexto propietario.
- Métricas de frescura, completitud, errores de esquema y mensajes en DLQ.

## 12. Trazabilidad con los recorridos del caso

1. **Cotización embebida:** acuerdo, producto, consentimiento y perfil versionado producen una oferta explicable.
2. **Suscripción y emisión:** la oferta aceptada se convierte en una instantánea contractual y un documento firmado.
3. **Siniestro asistido:** la póliza, evidencia, fraude y decisión forman un expediente trazable.
4. **Siniestro paramétrico:** el evento externo validado se correlaciona con póliza, regla paramétrica y decisión.
5. **Vida hipotecaria personalizada:** las señales consentidas conservan procedencia, versión de modelo y explicación.
6. **Ciclo de vida de póliza:** endosos, renovaciones, cancelaciones, cuotas y pagos preservan historial y vigencia.

## 13. Decisiones pendientes de gobierno

- Aprobar la matriz definitiva de retención por país, producto y tipo documental.
- Definir residencia y transferencia transfronteriza de datos.
- Establecer responsables de negocio y custodios técnicos por conjunto de información.
- Definir SLA de calidad, frescura y corrección para fuentes externas.
- Acordar el proceso de derechos del titular, anonimización y excepciones por retención legal.
- Precisar qué reglas actuariales deben clasificarse como confidenciales.

## 14. Glosario

| Término | Definición |
|---|---|
| System of record | Propietario autoritativo de un conjunto de información |
| PII | Información que identifica o puede identificar a una persona |
| PAN | Número principal de una tarjeta de pago |
| CVV | Código de verificación de una tarjeta; no debe almacenarse |
| Linaje | Procedencia, transformaciones, reglas y versiones que originaron un dato |
| Instantánea | Copia inmutable del estado relevante para reconstruir una decisión |
| PITR | Recuperación de una base de datos a un punto específico en el tiempo |
| RPO | Pérdida máxima de datos aceptable medida en tiempo |
| RTO | Tiempo máximo objetivo para recuperar el servicio |
| Retención legal | Conservación obligatoria que suspende temporalmente la eliminación |