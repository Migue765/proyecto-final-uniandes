# Solventa: decisiones de diseño de la vista de despliegue

**Diagrama asociado:** [solventa_deployment_view.drawio](solventa_deployment_view.drawio)

## 1. Propósito y alcance

Esta vista presenta el despliegue lógico de Solventa sobre AWS. Explica los canales de acceso, los puntos de entrada, los workloads principales, la persistencia, la comunicación asíncrona, la observabilidad, la entrega de software y la recuperación ante desastres.

No describe en detalle los procesos de negocio. Por ejemplo, los estados, validaciones y actividades humanas del proceso de siniestros deben documentarse mediante diagramas BPMN, de secuencia, estados o componentes.

La vista combina elementos de despliegue y contenedores para comunicar la arquitectura sin entrar en subredes, tablas de rutas, grupos de seguridad o manifiestos de Kubernetes.

## 2. Canales y punto de entrada

**Decisión:** ofrecer tres canales de consumo: cliente web, aplicación móvil y socios integrados.

**Razón:** cada canal tiene necesidades y ritmos de evolución distintos. Los socios requieren contratos estables y versionados, mientras que web y móvil necesitan respuestas adaptadas a sus interfaces.

**Decisión:** centralizar la entrada en Amazon API Gateway con WAF, OAuth 2.0/JWT, limitación de solicitudes y versionado.

**Razón:** concentra autenticación, protección frente a ataques comunes, cuotas y gobierno de las API. El versionado evita romper las integraciones de socios cuando cambia el contrato.

**Consecuencia:** API Gateway es un componente crítico y requiere monitoreo, configuración reproducible y políticas consistentes.

## 3. Entrada privada a EKS

**Decisión:** usar una integración privada de Amazon API Gateway HTTP API mediante VPC Link V2 hacia el listener de un ALB interno.

**Razón:** API Gateway requiere VPC Link V2 para alcanzar un ALB privado. El ALB distribuye las solicitudes hacia BFF Web, BFF Móvil o API Socios sin exponer directamente los workloads a Internet. TLS protege el tráfico y ACM administra los certificados.

**Decisión:** desplegar AWS Load Balancer Controller dentro de EKS para observar los recursos Kubernetes `Ingress` y crear o actualizar el ALB, sus listeners, reglas y target groups. El controller administra la configuración, pero no forma parte del recorrido de cada solicitud.

**Decisión:** utilizar target groups de tipo IP, de modo que el ALB enrute directamente a los pods registrados por los servicios Kubernetes.

**Consecuencia:** las rutas de API Gateway, el VPC Link, las reglas del ALB y los recursos `Ingress` deben mantenerse coordinados. El VPC Link, el HTTP API y el ALB deben pertenecer a la misma cuenta AWS, y las subredes privadas deben estar correctamente etiquetadas para el descubrimiento del ALB interno.

## 4. EKS y alta disponibilidad

**Decisión:** desplegar los workloads en un clúster EKS privado y distribuir sus réplicas entre varias AZ.

**Razón:** Kubernetes permite despliegue homogéneo, escalamiento y recuperación de contenedores. La distribución multi-AZ reduce el impacto de la caída de una zona.

**Decisión:** utilizar HPA, PodDisruptionBudget e IRSA.

**Razón:** HPA ajusta la capacidad; PodDisruptionBudget conserva un mínimo de réplicas durante interrupciones; IRSA otorga permisos AWS específicos a cada workload.

**Consecuencia:** se deben definir recursos, métricas de escalamiento, réplicas mínimas y políticas IAM de mínimo privilegio.

## 5. BFF y API para socios

**Decisión:** usar BFF separados para web y móvil, además de una API dedicada a socios.

**Razón:** cada fachada adapta respuestas, autenticación y composición de datos a su consumidor sin trasladar esa responsabilidad a los dominios.

**Consecuencia:** aumenta la cantidad de componentes, pero disminuye el acoplamiento entre los canales y los servicios de negocio.

## 6. Separación por dominios

**Decisión:** separar Identidad, Perfilamiento y Personalización, Cotización y Rating, Pólizas, Integraciones, Siniestros, Pagos y Cumplimiento en workloads independientes.

**Razón:** cada dominio tiene reglas, datos, riesgos y necesidades de escalabilidad diferentes.

**Consecuencia:** aumentan las comunicaciones distribuidas y la necesidad de contratos claros, observabilidad y tolerancia a fallos.

**Decisión:** ejecutar Perfilamiento y Personalización como workload independiente, propietario de perfiles de riesgo versionados.

**Razón:** el caso exige perfil y precio personalizado en `p95 <= 400 ms`, al menos 20.000 perfilamientos y ofertas hipotecarias por hora y el reprocesamiento batch de 10 millones de perfiles en menos de dos horas sin afectar el tráfico en línea. Separarlo permite escalar y desplegar esta carga sin acoplarla a Identidad ni a Cotización.

**Consecuencia:** Cotización solicita un perfil de riesgo válido mediante un contrato síncrono; Perfilamiento valida el consentimiento con Identidad, obtiene señales externas mediante Integraciones y publica `PerfilActualizado`. Los procesos online y batch comparten las reglas del dominio, pero deben usar recursos y políticas de escalamiento diferenciados para evitar competencia por capacidad.

## 7. Comunicación síncrona y asíncrona

**Decisión:** usar comunicación síncrona para solicitudes que requieren respuesta inmediata, como cotizar, obtener un perfil de riesgo válido, validar consentimiento, consultar pólizas o evaluar fraude.

**Decisión:** usar un Event Bus con DLQ para eventos de perfilamiento, pólizas, siniestros, pagos y fuentes externas.

**Razón:** los eventos desacoplan emisores y consumidores, permiten reintentos y facilitan operaciones que no requieren una respuesta inmediata. La DLQ conserva mensajes que no pudieron procesarse.

**Consecuencia:** los consumidores deben tolerar duplicados, manejar reintentos y mantener compatibilidad entre versiones de eventos.

## 8. Pagos sin duplicados

**Decisión:** procesar `OrdenPago` de forma idempotente.

**Razón:** un evento puede entregarse más de una vez. Pagos debe reconocer una orden ya procesada y evitar cobros o desembolsos duplicados.

**Consecuencia:** se necesita una clave de idempotencia, persistencia del resultado y una restricción única o mecanismo equivalente.

## 9. Dominio de Siniestros

**Decisión:** mantener Siniestros como dominio independiente con base de datos propia, almacenamiento de evidencias, evaluación de fraude y coordinación asíncrona con Pagos.

**Razón:** maneja datos personales, documentos, decisiones económicas y posibles intentos de fraude.

**Decisión:** almacenar evidencias en S3 con cifrado, versionado y retención; usar KMS y Secrets Manager para claves y credenciales; registrar decisiones de fraude y auditoría.

**Consecuencia:** las reglas de acceso, cadena de custodia, retención, revisión humana y estados del siniestro deben detallarse en vistas complementarias.

## 10. Persistencia por dominio

**Decisión:** cada dominio es propietario de sus datos en RDS/Aurora y no accede directamente a las tablas de otro dominio.

**Razón:** reduce acoplamiento, permite evolucionar esquemas independientemente y establece una responsabilidad clara sobre la información.

**Decisión:** configurar RDS/Aurora en modo multi-AZ, con cifrado KMS, respaldos y PITR.

**Consecuencia:** los intercambios entre dominios deben realizarse mediante API o eventos. Las consultas transversales requieren integración o modelos de lectura.

Perfilamiento conserva versiones del perfil, fuentes utilizadas, versión del modelo y marcas temporales necesarias para reconstruir una decisión. Cotización solo guarda la referencia y la instantánea mínima utilizada en la oferta; no modifica los datos de Perfilamiento.

## 11. Caché, documentos y seguridad

**Decisión:** usar ElastiCache Redis multi-AZ para datos temporales y caché.

**Razón:** reduce latencia y carga sobre la persistencia. En Perfilamiento almacena temporalmente perfiles de riesgo para responder dentro del presupuesto de latencia y aplicar una degradación controlada cuando Open Finance u Open Data no están disponibles. Redis no debe ser la única fuente de información crítica ni puede eludir la validación del consentimiento.

**Decisión:** usar S3 para evidencias y documentos, con versionado y retención.

**Decisión:** usar KMS para claves de cifrado y Secrets Manager para contraseñas, tokens y credenciales, incluyendo rotación.

**Consecuencia:** los workloads deben aplicar IAM de mínimo privilegio y no almacenar secretos en código, imágenes o archivos de configuración.

## 12. Integraciones externas

**Decisión:** concentrar el acceso a Open Finance, Open Data, KYC/AML, pagos, firma, IoT y reaseguradoras en el servicio de Integraciones. Perfilamiento consume Open Finance y Open Data únicamente a través de estos adaptadores.

**Razón:** evita que cada dominio implemente protocolos externos y centraliza adaptadores, tiempos de espera, caché, circuit breakers y validación de webhooks.

**Consecuencia:** Integraciones debe aislar fallos de terceros, evitar convertirse en un punto único de saturación y autenticar los webhooks recibidos.

## 13. Observabilidad

**Decisión:** centralizar métricas, logs, trazas y alertas de EKS y del Event Bus.

**Razón:** una arquitectura distribuida necesita correlacionar solicitudes y eventos para diagnosticar fallos y medir objetivos de servicio.

**Consecuencia:** se deben propagar identificadores de correlación, proteger datos sensibles en logs y establecer alertas accionables.

## 14. DevSecOps y entrega

**Decisión:** utilizar CI/CD con escaneo, firma de imágenes, ECR y despliegue GitOps hacia EKS.

**Razón:** garantiza trazabilidad de artefactos, despliegues reproducibles y controles de seguridad antes de ejecutar una imagen.

**Consecuencia:** EKS debe aceptar únicamente imágenes autorizadas y la configuración declarativa debe versionarse y auditarse.

## 15. Recuperación ante desastres

**Decisión:** representar una segunda región AWS separada de la región principal.

**Razón:** multi-AZ protege frente a la caída de una zona, pero no frente a la indisponibilidad completa de una región.

La región secundaria contiene:

- RDS/Aurora como réplica secundaria.
- S3 con evidencias replicadas.
- ECR y configuración replicados.
- EKS con workloads en espera.
- Pruebas periódicas de restauración.

**Consecuencia:** se necesitan replicación entre regiones, procedimientos probados y una estrategia para promover los recursos secundarios.

> **Supuesto por validar:** `RTO <= 5 min` y `RPO <= 30 s` son objetivos exigentes. Requieren replicación continua, capacidad en espera, failover automatizado y pruebas periódicas. Si estas capacidades no se implementan, deben definirse objetivos alcanzables.

## 16. Convenciones visuales

| Representación | Significado |
|---|---|
| Azul | Contenedor o workload |
| Verde | Canal asíncrono |
| Morado | Datos gestionados |
| Amarillo | Servicios AWS, seguridad y sistemas externos |
| Línea continua | Interacción síncrona o acceso directo |
| Línea punteada verde | Eventos o replicación |
| Línea punteada roja | Telemetría |
| Línea punteada azul | Despliegue de artefactos |

## 17. Glosario de siglas y términos

| Sigla o término | Definición | Función en Solventa |
|---|---|---|
| **ACM** | AWS Certificate Manager | Administra los certificados TLS utilizados por API Gateway y el ALB. |
| **ALB** | Application Load Balancer | Recibe tráfico privado desde API Gateway y lo distribuye hacia los servicios publicados por EKS. |
| **AWS Load Balancer Controller** | Controller de Kubernetes para Elastic Load Balancing | Observa recursos `Ingress` o `Service` y crea o actualiza el ALB, sus reglas y target groups; no procesa las solicitudes de negocio. |
| **AML** | Anti-Money Laundering | Controles externos para detectar lavado de activos durante la validación de clientes y operaciones. |
| **API** | Application Programming Interface | Contrato mediante el cual canales, socios y servicios intercambian solicitudes y respuestas. |
| **AWS** | Amazon Web Services | Plataforma cloud donde se despliega la solución. |
| **AZ** | Availability Zone | Ubicación aislada dentro de una región AWS. Las réplicas multi-AZ mantienen disponibilidad ante la caída de una zona. |
| **BFF** | Backend for Frontend | Fachada especializada que adapta las API a las necesidades del cliente web o móvil. |
| **CI/CD** | Continuous Integration / Continuous Delivery | Automatiza validación, construcción, escaneo y entrega de nuevas versiones. |
| **DLQ** | Dead-Letter Queue | Conserva eventos que agotaron sus reintentos para poder analizarlos y reprocesarlos. |
| **DR** | Disaster Recovery | Estrategia de recuperación en una región secundaria cuando la región principal no está disponible. |
| **ECR** | Elastic Container Registry | Registro de AWS que almacena las imágenes de contenedor escaneadas y firmadas. |
| **EKS** | Elastic Kubernetes Service | Servicio administrado de Kubernetes donde se ejecutan los BFF y microservicios de Solventa. |
| **HPA** | Horizontal Pod Autoscaler | Aumenta o reduce automáticamente el número de réplicas de un workload según su carga. |
| **HTTPS** | Hypertext Transfer Protocol Secure | Protocolo HTTP protegido con TLS para cifrar las comunicaciones. |
| **IAM** | Identity and Access Management | Define identidades, roles y permisos para acceder a recursos de AWS con mínimo privilegio. |
| **IoT** | Internet of Things | Dispositivos y fuentes externas que pueden aportar señales para riesgo, monitoreo o eventos paramétricos. |
| **IRSA** | IAM Roles for Service Accounts | Asigna a cada workload de EKS permisos AWS específicos sin compartir credenciales estáticas. |
| **JWT** | JSON Web Token | Token firmado que transporta identidad y permisos entre el usuario, API Gateway y los servicios. |
| **KMS** | Key Management Service | Administra las claves utilizadas para cifrar bases de datos, evidencias y otros datos. |
| **KYC** | Know Your Customer | Proceso de identificación y validación del cliente antes de permitir operaciones sensibles. |
| **OAuth 2.0** | Open Authorization 2.0 | Protocolo de autorización usado para conceder acceso controlado a las API. |
| **PITR** | Point-in-Time Recovery | Permite restaurar una base de datos a un instante anterior dentro del período de retención. |
| **RDS** | Relational Database Service | Servicio administrado de bases de datos relacionales utilizado para la persistencia de los dominios. |
| **RPO** | Recovery Point Objective | Máxima pérdida de datos aceptable medida en tiempo; el diagrama propone hasta 30 segundos. |
| **RTO** | Recovery Time Objective | Tiempo máximo esperado para recuperar el servicio; el diagrama propone hasta 5 minutos. |
| **S3** | Simple Storage Service | Almacena evidencias y documentos con cifrado, versionado, retención y réplica regional. |
| **TLS** | Transport Layer Security | Cifra las comunicaciones HTTPS y permite verificar la identidad del servidor. |
| **WAF** | Web Application Firewall | Filtra tráfico malicioso y ataques web antes de que alcancen las API. |
| **VPC Link V2** | Enlace privado administrado de API Gateway | Permite que API Gateway integre un HTTP API con el listener de un ALB privado dentro de una VPC. |
| **GitOps** | Gestión declarativa de despliegues mediante Git | Mantiene la configuración versionada y sincroniza el estado aprobado con EKS. |
| **PodDisruptionBudget** | Política de disponibilidad de Kubernetes | Conserva una cantidad mínima de réplicas durante mantenimientos o interrupciones voluntarias. |
| **Event Bus** | Canal central de eventos | Desacopla productores y consumidores de eventos de pólizas, siniestros, pagos y fuentes externas. |
| **Idempotencia** | Propiedad que produce el mismo resultado ante solicitudes repetidas | Evita que la misma `OrdenPago` genere más de un desembolso. |

## 18. Aspectos excluidos de esta vista

Para conservar la legibilidad, esta vista no detalla:

- VPC, subredes públicas y privadas, tablas de rutas y NAT Gateway.
- Grupos de seguridad, Network ACL y endpoints privados.
- Estados y tareas humanas del proceso de siniestros.
- Contratos completos de API y esquemas de eventos.
- Manifiestos de Kubernetes y configuración detallada de escalamiento.
- Procedimientos operativos completos de failover y restauración.

Estos aspectos deben documentarse en vistas complementarias de red, procesos, componentes, secuencias y operación.

## 19. Trazabilidad con el caso Solventa

Las decisiones de esta vista se contrastaron con `MISW4501-202614-Proyecto (1).pdf`. En particular, el diagrama representa los tres canales requeridos, el perfilamiento en línea, la integración con fuentes externas, los siniestros asistidos y paramétricos, los flujos idempotentes de dinero, el aislamiento de datos, la operación multi-AZ y la recuperación multi-región.

La vista no afirma que microservicios, Kubernetes o arquitectura orientada a eventos sean obligatorios en el caso. Son decisiones del equipo que deben validarse con experimentos de latencia, escalabilidad, disponibilidad, seguridad, facilidad de modificación y facilidad de integración.