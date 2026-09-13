# Solventa: decisiones del modelo de componentes

**Diagrama asociado:** [solventa_component_model.drawio](solventa_component_model.drawio)

## 1. Propósito y nivel de abstracción

Esta vista muestra cómo las capacidades del dominio se implementan mediante componentes lógicos, qué interfaces ofrecen y cómo colaboran. Se ubica entre el modelo de dominio y la vista de despliegue:

- El modelo de dominio define conceptos, agregados y reglas.
- El modelo de componentes asigna responsabilidades e interfaces.
- La vista de despliegue muestra dónde se ejecutan los componentes y qué infraestructura los soporta.

Por ello no se representan VPC, zonas de disponibilidad, EKS, RDS, Redis, S3 ni regiones AWS. Tampoco se detallan clases, tablas, endpoints HTTP o manifiestos de Kubernetes.

## 2. Convenciones

| Representación | Significado |
|---|---|
| Contenedor con título de color | Contexto delimitado y frontera de responsabilidad |
| `«component»` | Componente lógico con una responsabilidad cohesionada |
| `«port»` | Interfaz ofrecida por el contexto; no implica un protocolo concreto |
| Línea continua con flecha | Solicitud síncrona que necesita respuesta inmediata |
| Línea verde punteada | Publicación o consumo asíncrono de un evento |
| Event Bus + DLQ | Canal de distribución, reintento y aislamiento de eventos |
| Integraciones | Puertos y adaptadores que aíslan protocolos y proveedores externos |

Una línea conectada a un componente o puerto representa una dependencia con el elemento completo, no con una propiedad o texto cercano.

## 3. Fronteras y componentes

| Contexto | Componentes | Responsabilidad principal |
|---|---|---|
| Identidad y Cliente | Gestión de Cliente; Consentimientos y KYC | Onboarding, contacto, autenticación de negocio y autorización del uso de datos |
| Perfilamiento y Personalización | Orquestador de Perfil; Motor de Perfil | Enriquecimiento consentido, scoring, explicación, versionado y reprocesamiento batch |
| Producto y Suscripción | Catálogo de Productos; Motor de Suscripción | Coberturas, condiciones, vigencia, reglas de aceptación y elegibilidad |
| Distribución | Gestión de Socios; Acuerdos y Originación B2B | Aislamiento por socio, productos habilitados, comisiones y originación embebida |
| Cotización | Gestión de Cotización; Rating y Evaluación | Creación de oferta, cálculo de prima, vigencia, evaluación y aceptación |
| Pólizas | Emisión y Documentos; Ciclo de Vida | Firma, emisión, endosos, renovación, cancelación y generación de cuotas |
| Siniestros | Reporte y Evidencias; Evaluación y Liquidación | FNOL, evidencia, cobertura, fraude, siniestros asistidos y paramétricos |
| Pagos y Recaudo | Órdenes Idempotentes; Transacciones y Conciliación | Cobros, indemnizaciones, intentos, webhooks y conciliación |
| Cumplimiento y Auditoría | Casos y Fraude; Auditoría y Reportes | KYC/AML, fraude, escalamiento, registro inmutable y reportes regulatorios |

Cada contexto conserva datos propios mediante adaptadores de persistencia internos. Ningún componente consulta directamente las tablas de otro contexto.

## 4. Fachadas por canal

- **BFF Web:** compone información para venta asistida, administración de pólizas, operación, socios y tableros.
- **BFF Móvil:** soporta tareas breves, biometría, evidencia, geolocalización, notificaciones y sincronización offline.
- **API de Socios:** expone contratos versionados, autenticación por alcance, cuotas y aislamiento por distribuidor.

Las fachadas no contienen reglas actuariales, de suscripción, de siniestros ni de pagos. Adaptan contratos y coordinan respuestas para el canal.

## 5. Comunicación síncrona

Se usa comunicación síncrona cuando el recorrido necesita una respuesta dentro del presupuesto de latencia:

- Canales hacia Identidad, Cotización, Pólizas y Siniestros.
- API de Socios hacia Distribución, y Distribución hacia Cotización.
- Cotización hacia Perfilamiento y Producto/Suscripción.
- Perfilamiento hacia Identidad para validar consentimiento y hacia Integraciones para obtener señales.
- Pólizas hacia Producto/Suscripción y Firma.
- Siniestros hacia Pólizas para validar cobertura y hacia Cumplimiento para evaluar fraude.
- Pagos hacia el adaptador de pasarela para cobrar o desembolsar.

Cada llamada externa aplica timeout, reintento limitado, circuit breaker y degradación definida por negocio. No se encadenan dependencias externas sin controlar el presupuesto total del recorrido.

## 6. Comunicación por eventos

| Evento | Productor | Consumidores principales |
|---|---|---|
| `PerfilActualizado` | Perfilamiento | Cotización, cumplimiento y modelos de lectura |
| `CotizaciónAceptada` | Cotización | Auditoría y consumidores analíticos |
| `PólizaEmitida` | Pólizas | Pagos, siniestros, cumplimiento y notificaciones |
| `SiniestroReportado` | Siniestros | Cumplimiento, auditoría y automatizaciones |
| `SiniestroAprobado` | Siniestros | Pagos |
| `PagoConfirmado` / `PagoFallido` | Pagos | Siniestros, cuotas de prima y notificaciones |
| `EventoParamétricoValidado` | Integraciones | Siniestros |

El bus entrega al menos una vez. Los consumidores deben ser idempotentes, registrar la versión del contrato y propagar identificadores de correlación. La DLQ conserva mensajes que agotaron sus reintentos.

La emisión de la póliza se solicita sincrónicamente después de aceptar la cotización para cumplir el recorrido de decisión y emisión. `CotizaciónAceptada` se publica además como hecho de negocio para auditoría y consumidores futuros; no vuelve a ordenar la emisión y, por tanto, no crea una segunda póliza.

## 7. Puertos y adaptadores externos

- **Open Finance / Open Data:** normaliza señales financieras y públicas consentidas.
- **KYC / AML:** encapsula verificación de identidad y listas restrictivas.
- **Pasarelas de Pago:** abstrae cobro, desembolso y webhooks firmados.
- **Firma y Notificación:** gestiona firma electrónica, no repudio, documentos y avisos.
- **IoT / Paramétricos:** valida y normaliza eventos de clima, vuelos o telemetría.
- **ACORD / Reaseguro:** traduce el modelo interno a estándares sectoriales y contratos de reaseguradoras.

Cambiar un proveedor debe requerir sustituir su adaptador, no modificar los componentes consumidores.

## 8. Recorridos críticos cubiertos

1. **Cotización embebida:** Socio → API de Socios → Distribución → Cotización → Perfilamiento y Producto/Suscripción.
2. **Suscripción y emisión:** Cotización aceptada → Pólizas → Firma → orden de cobro → póliza emitida.
3. **Siniestro asistido:** BFF Móvil/Web → Siniestros → Pólizas → Cumplimiento/Fraude → Pagos.
4. **Siniestro paramétrico:** IoT/Paramétricos → Event Bus → Siniestros → Pagos → notificación.
5. **Vida hipotecaria personalizada:** Cotización → Perfilamiento → consentimiento → Open Finance/Open Data → Rating/Suscripción.
6. **Ciclo de vida:** Pólizas → endosos/renovación/cancelación → Pagos, Reaseguro, Cumplimiento y Auditoría.

## 9. Atributos de calidad

- **Latencia:** BFF y componentes de dominio evitan saltos innecesarios; Perfilamiento puede degradar fuentes externas sin exceder el journey.
- **Escalabilidad:** Cotización, Perfilamiento, eventos paramétricos y Pagos pueden escalar independientemente.
- **Disponibilidad:** los eventos absorben picos y desacoplan consumidores; las llamadas síncronas aíslan fallos de terceros.
- **Seguridad:** Identidad gobierna consentimiento; los adaptadores limitan la exposición de credenciales y datos sensibles.
- **Facilidad de modificación:** productos, rating, fraude, canales y proveedores quedan localizados en componentes distintos.
- **Facilidad de integración:** puertos estables, contratos versionados y adaptadores evitan propagar cambios externos.

## 10. Decisiones y trade-offs

**Componentes por capacidad, no por tabla.** Reduce acoplamiento semántico y localiza cambios, pero exige contratos y disciplina sobre las fronteras.

**Híbrido síncrono/asíncrono.** Mantiene respuestas inmediatas en compra y consulta, y desacopla pagos, siniestros paramétricos, auditoría y consumidores futuros. Introduce consistencia eventual e idempotencia.

**BFF por experiencia.** Permite evolucionar web y móvil por separado, a costa de mantener dos fachadas y evitar duplicación de reglas de negocio.

**Adaptadores externos centralizados.** Facilitan reemplazar proveedores y aplicar resiliencia uniforme. Deben escalar y aislarse para no convertirse en un cuello de botella.

## 11. Alineación con otras vistas

- Los nueve grupos corresponden a los contextos de `solventa_domain_model.drawio`.
- BFF Web, BFF Móvil, API de Socios, Perfilamiento, Cotización, Pólizas, Siniestros, Pagos, Cumplimiento, Integraciones y Event Bus se materializan en `solventa_deployment_view.drawio`.
- Producto/Suscripción y Distribución aparecen como fronteras lógicas explícitas. Su decisión de despliegue puede mantenerse dentro de workloads existentes o evolucionar a unidades independientes cuando el volumen y el equipo lo justifiquen.

## 12. Trazabilidad con el caso Solventa

La vista se contrastó con `MISW4501-202614-Proyecto (1).pdf`. Cubre los seis recorridos obligatorios y las integraciones con Open Finance, Open Data, KYC/AML, pagos, firma, notificaciones, IoT, reaseguradoras y ACORD.

El caso no obliga a usar este nivel de descomposición. Los límites propuestos deben validarse mediante pruebas de carga, resiliencia, caos, seguridad y reemplazo de adaptadores, utilizando las metas medibles del enunciado.

## 13. Glosario

| Término | Definición |
|---|---|
| API | Interfaz de programación consumida mediante un contrato estable |
| BFF | Backend for Frontend; fachada especializada para un canal |
| DLQ | Dead-Letter Queue; cola de eventos que agotaron sus reintentos |
| FNOL | First Notice of Loss; primer aviso de un siniestro |
| KYC | Know Your Customer; verificación de identidad del cliente |
| AML | Anti-Money Laundering; controles contra lavado de activos |
| ACORD | Estándares de intercambio de información del sector asegurador |
| IoT | Internet of Things; fuentes de telemetría y eventos conectados |
| Puerto | Interfaz definida por el núcleo para comunicarse sin depender de una implementación |
| Adaptador | Implementación que traduce un puerto hacia un proveedor o tecnología concreta |
| Idempotencia | Propiedad que evita efectos duplicados al repetir una operación |