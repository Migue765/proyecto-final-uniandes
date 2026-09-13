# Solventa: decisiones del modelo de dominio

**Diagrama asociado:** [solventa_domain_model.drawio](solventa_domain_model.drawio)

## 1. Propósito

El modelo representa los conceptos, reglas y relaciones principales del negocio asegurador de Solventa. Usa elementos de UML y Domain-Driven Design (DDD) para mostrar contextos delimitados, agregados, entidades, objetos de valor y eventos de dominio.

Es un modelo conceptual y tecnológico-agnóstico. Por eso no incluye API, microservicios, bases de datos, AWS, EKS, colas ni proveedores concretos; esos elementos pertenecen a las vistas de componentes y despliegue.

## 2. Correcciones frente a la base

La base inicial era útil como inventario, pero mezclaba responsabilidades y dejaba incompletos varios ciclos de vida. El nuevo modelo corrige lo siguiente:

- `Ramo` se modela como **Producto de Seguro**, con coberturas y reglas de suscripción propias.
- `Prima` deja de ser una entidad aislada. Se distingue entre la prima calculada o contratada y la **Cuota de Prima** cobrable.
- `Pago` se separa en **Orden de Pago** y **Transacción**, lo que permite reintentos e idempotencia sin duplicar cobros o indemnizaciones.
- `Póliza` incorpora coberturas contratadas, beneficiarios y endosos.
- `Siniestro` incorpora evidencias, evaluación de fraude y decisión de liquidación.
- `Cotización` conserva una instantánea de coberturas y de la evaluación de riesgo usada para calcularla.
- `Consentimiento` pertenece al agregado Cliente y conserva su historial de otorgamiento o revocación.
- `Perfilamiento y Personalización` se separa de Identidad y Cliente porque tiene modelos, fuentes, ritmos de cambio y necesidades de escalamiento propios.
- `Perfil de Riesgo` es una raíz independiente y versionada dentro de ese contexto, porque sus versiones pueden sustentar evaluaciones de distintas cotizaciones y deben ser reconstruibles para actuaría y regulación.
- La auditoría no se modela como hija exclusiva de Póliza; es una capacidad transversal dentro de Cumplimiento y Auditoría.
- Se añaden objetos de valor para evitar atributos primitivos ambiguos, por ejemplo `Dinero`, `Periodo` y `DocumentoIdentidad`.
- Se identifican eventos de dominio coherentes con la arquitectura asíncrona del despliegue.

## 3. Contextos delimitados

| Contexto | Responsabilidad |
|---|---|
| Identidad y Cliente | Identidad del cliente, contacto y consentimientos para acceder a sus datos. |
| Perfilamiento y Personalización | Enriquece señales consentidas de Open Finance y Open Data y produce perfiles de riesgo versionados para ofertas y decisiones explicables. |
| Producto y Suscripción | Definición del producto, coberturas y reglas para aceptar o rechazar riesgos. |
| Cotización | Cálculo y vigencia de una oferta concreta para un cliente. |
| Pólizas | Contrato emitido, coberturas contratadas, beneficiarios, endosos y vigencia. |
| Siniestros | Reporte, evidencia, análisis, decisión y liquidación de un siniestro. |
| Pagos y Recaudo | Cobro de primas e indemnizaciones mediante órdenes idempotentes y transacciones. |
| Distribución | Socios B2B y acuerdos que determinan productos, vigencia y comisión. |
| Cumplimiento y Auditoría | Casos KYC, AML o fraude y registro inmutable de acciones relevantes. |

Los objetos de valor no se presentan en un bloque separado: aparecen como tipos de los atributos que los utilizan. Del mismo modo, los eventos relevantes se nombran directamente sobre las líneas verdes entre productor y consumidor. Esto evita tratar un catálogo auxiliar como si fuera otro contexto delimitado.

## 4. Agregados y consistencia

Una raíz de agregado es el único punto por el que se modifica su conjunto de entidades. La composición UML, representada con rombo relleno, se usa únicamente cuando la parte pertenece de manera exclusiva al agregado y su ciclo de vida está gobernado por la raíz. No significa necesariamente borrado físico, porque las políticas de auditoría y retención pueden exigir conservar información histórica.

El rombo hueco de agregación UML no se utiliza. Su semántica de pertenencia débil no añade una regla de consistencia o ciclo de vida suficientemente precisa para este modelo DDD; cuando no existe composición se prefiere una asociación normal.

Las raíces principales son:

- `Cliente`
- `Perfil de Riesgo`
- `Producto de Seguro`
- `Cotización`
- `Póliza`
- `Siniestro`
- `Orden de Pago`
- `Cuota de Prima`
- `Socio Distribuidor`
- `Caso de Cumplimiento`
- `Registro de Auditoría`

`Registro de Auditoría` es una raíz independiente e inmutable. Se relaciona con un caso de cumplimiento mediante una asociación normal, no mediante composición, porque también puede registrar acciones de otros contextos y su ciclo de vida no depende del caso.

## 5. Relaciones entre contextos

### Notación UML + DDD

- `«aggregate root»`: límite de consistencia y punto de acceso al agregado.
- `«entity»`: elemento con identidad propia dentro del dominio.
- `«value object»`: valor inmutable sin identidad propia.
- `◆—` Composición UML: parte exclusiva cuyo ciclo de vida está gobernado por la raíz.
- `——` Asociación UML: relación estructural estable; las multiplicidades indican cardinalidad.
- Línea punteada verde con flecha: coordinación mediante un evento de dominio.
- Línea punteada roja con flecha: derivación o apertura de un caso de cumplimiento.
- `◇—` Agregación UML con rombo hueco: no se usa porque no aporta una regla de ciclo de vida útil para este modelo.

No se usa el rombo hueco de agregación UML. Los colores verde y rojo son una extensión documentada de este modelo, no una convención cromática definida por UML. Las dependencias punteadas no llevan multiplicidades; estas se reservan para asociaciones y composiciones.

En asociaciones y composiciones, el verbo se presenta en el centro de la línea y cada multiplicidad se ubica junto al extremo al que describe. Por ejemplo, `Cliente 1 — solicita — 0..* Cotización`. Las multiplicidades no forman parte del nombre de la relación.

Ninguna relación entre contextos implica acceso directo a la persistencia de otro contexto.

Relaciones principales:

- Un cliente solicita cotizaciones.
- Un cliente puede tener perfiles de riesgo versionados y actúa como tomador de pólizas bajo el supuesto actual.
- Perfilamiento solo utiliza fuentes cubiertas por un consentimiento vigente; la referencia al consentimiento y el linaje detallado se preservan en sus registros internos, aunque no se expanden como entidades en este diagrama.
- Un producto define las condiciones usadas por muchas cotizaciones.
- Una evaluación de riesgo se sustenta en una versión de perfil de riesgo.
- Una cotización aceptada puede originar una póliza.
- Una póliza corresponde a un producto y a un cliente tomador.
- Una póliza ampara muchos siniestros y genera cuotas de prima.
- Un siniestro aprobado puede generar una orden de indemnización.
- Una cuota vencida o programada puede generar órdenes de cobro.
- Una orden de indemnización publica `PagoConfirmado` o `PagoFallido` para actualizar el estado del siniestro.
- Una orden de cobro publica `PagoConfirmado` o `PagoFallido` para actualizar el estado de la cuota de prima.
- Un socio distribuidor puede originar cotizaciones B2B.
- Un acuerdo de distribución habilita uno o más productos.
- Clientes o siniestros pueden originar casos de cumplimiento.

## 6. Reglas de negocio visibles

- Una cotización tiene fecha de expiración y no puede aceptarse después de vencer.
- Una póliza conserva las condiciones contratadas aunque el producto cambie posteriormente.
- Un siniestro solo se liquida después de una decisión aprobatoria.
- Una orden de pago utiliza una clave de idempotencia.
- Las transacciones pertenecen a una orden y permiten registrar intentos y respuestas del proveedor.
- El resultado de una orden de pago se comunica mediante eventos; el consumidor determina si actualiza un siniestro o una cuota según la referencia y el tipo de orden.
- Los consentimientos pueden revocarse sin eliminar su trazabilidad.
- Los registros de auditoría son inmutables y pueden encadenarse mediante hashes.

## 7. Elementos intencionalmente excluidos

- Tecnología e infraestructura.
- Interfaces de usuario y BFF.
- Contratos HTTP o esquemas de eventos completos.
- Flujo detallado de tareas humanas del siniestro.
- Algoritmos de scoring, fraude o cálculo actuarial.
- Proveedores externos concretos.

Estos aspectos deben cubrirse mediante vistas de componentes, despliegue, secuencia, estados y BPMN.

## 8. Supuestos por validar con negocio

- Si una póliza puede tener varios tomadores o asegurados distintos del cliente principal.
- Si todas las líneas requieren beneficiarios o solo ciertos productos.
- Si una decisión de siniestro puede revisarse y, por tanto, requiere versionado o varias decisiones.
- Si la cuota de prima debe pertenecer al agregado Póliza o conservar autonomía para soportar alto volumen de recaudo.
- Si los socios distribuidores pueden emitir directamente o únicamente originar cotizaciones.
- Cuáles cambios deben manejarse como endoso y cuáles exigen cancelar y emitir una nueva póliza.

## 9. Trazabilidad con el caso Solventa

El modelo se contrastó con `MISW4501-202614-Proyecto (1).pdf`. Sus nueve contextos delimitados cubren las capacidades de identidad y consentimiento, perfilamiento y personalización, producto y suscripción, cotización, pólizas, siniestros, pagos y recaudo, distribución, y cumplimiento y auditoría.

El caso no prescribe estas fronteras ni el uso de DDD. La separación propuesta busca localizar cambios de rating, nuevas fuentes de datos, nuevos productos y cambios regulatorios, y mantener explícita la propiedad de los datos y de las reglas de negocio.