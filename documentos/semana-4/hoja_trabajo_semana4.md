# Hoja de Trabajo — Arquitectura, Patrones y Experimentos

**Universidad de los Andes · Maestría en Ingeniería de Software · MISW4501**
**Proyecto Integrador — Grupo 2 · Solventa**
**Semana 4 · 30 de agosto de 2026**

| Integrante | Rol |
|---|---|
| Jazmin Natalia Córdoba Puerto | Gerente — Usabilidad y entrega |
| Juan Esteban Mejía Izasa | Web front, integración API, pagos |
| Miguel Alejandro Gómez Alarcón | Arquitectura, Open Finance, KYC, rendimiento, seguridad |
| Angie Natalia Arandio Niño | Dominio, web back, móvil, pruebas unitarias |

---

## Contenido de este documento

| Sección | Contenido |
|---|---|
| §1 | Contexto y atributos de calidad que dirigen el diseño |
| §2 | Modelos de arquitectura: vista funcional, de despliegue y de información |
| §3 | Diseño detallado — patrones aplicados y su razonamiento frente a cada ASR |
| §4 | Decisiones de arquitectura y alternativas descartadas |
| §5 | Propuesta de experimentos de arquitectura |
| §6 | Refinamiento de la estrategia de pruebas |
| §7 | Plan de trabajo y estado del tablero |

---

## 1. Contexto y atributos de calidad que dirigen el diseño

Solventa es una aseguradora digital nativa en la nube construida sobre Finanzas Abiertas y Datos Abiertos. Su promesa de negocio —cotizar, suscribir, emitir y pagar siniestros de forma casi instantánea, embebiendo el seguro en el punto de necesidad del cliente— impone exigencias que no se resuelven eligiendo bien un framework, sino decidiendo bien la estructura del sistema.

El diseño que se presenta en este documento no parte de una preferencia tecnológica sino de los nueve escenarios de calidad (ASR) definidos en la semana 3. Cada decisión estructural que se documenta a continuación existe porque hay al menos un ASR que la exige.

| ASR | Atributo | Medida de respuesta | Consecuencia arquitectural |
|---|---|---|---|
| ASR-1.1 | Latencia | p95 < 200 ms con 500 req/min | Caché de perfiles, cálculo asíncrono de lo no crítico |
| ASR-1.2 | Latencia bajo degradación | p95 < 200 ms desde caché, 0% de pérdida | Circuit breaker, timeout agresivo, degradación elegante |
| ASR-2.1 | Modificabilidad | Nueva pasarela en < 4 horas-hombre, 0 cambios en el núcleo | Puertos y adaptadores, inversión de dependencias |
| ASR-2.2 | Modificabilidad | Nuevo ramo en ≤ 2 semanas, 0 cambios en el motor de rating | Configuración externalizada, motor parametrizado |
| ASR-3.1 | Disponibilidad | Recuperación < 30 s, ≥ 99,9% | Fallback a fuente primaria, health checks, bulkhead |
| ASR-3.2 | Disponibilidad multi-zona | RTO ≤ 10 min, RPO ≤ 30 s | Despliegue activo-activo multi-AZ, réplica con promoción |
| ASR-3.3 | Continuidad offline | 100% de consultas sin conexión, sync ≤ 10 s | Cliente offline-first, almacenamiento local cifrado |
| ASR-4.1 | Confidencialidad | 100% TLS 1.3, 0 PII en texto plano | Tokenización de PII, cifrado en tránsito y reposo |
| ASR-4.2 | Integridad | Alerta de alteración no autorizada < 1 s | Firma digital, almacenamiento inmutable, auditoría |

**Restricciones que acotan el espacio de diseño**

- Contenedores obligatorios para todos los microservicios; nada se instala en el sistema anfitrión.
- PostgreSQL como almacenamiento transaccional primario; no se admite una base NoSQL en ese rol.
- Cumplimiento de Ley 1581 de 2012, Decreto 1297 de 2022, Circular Externa 004 de 2024 y PCI-DSS.
- Consentimiento revocable con efecto en menos de 5 minutos.
- Expansión a México, Chile y Perú dentro de 36 meses, lo que obliga a que la regionalización sea configuración y no una bifurcación del código.

---

## 2. Modelos de arquitectura

### 2.1 Vista funcional

La vista funcional muestra cómo se descompone el sistema en componentes y cómo colaboran para atender los recorridos de negocio. La estructura es de cuatro capas más una plataforma de datos transversal.

![Figura 1. Vista funcional de la arquitectura de Solventa](diagramas/imagenes/vista_funcional.png)

**Capa de canales.** Tres consumidores con necesidades distintas: el portal web en Angular, la aplicación móvil nativa en Kotlin y los sistemas de socios distribuidores que consumen la API B2B. Son deliberadamente delgados: no contienen reglas de negocio, porque una regla que vive en el canal debe reimplementarse en cada canal nuevo.

**Capa Edge.** Concentra lo que debe ocurrir antes de que una petición toque lógica de negocio: filtrado de tráfico malicioso en el WAF, y en el API Gateway la autenticación, la limitación de tasa por cliente y por socio, y la terminación TLS. Situar esto en el borde evita que cada servicio reimplemente controles de seguridad, que es la principal fuente de inconsistencias de seguridad en arquitecturas de microservicios.

**Capa BFF.** Un backend por canal. El BFF Web compone respuestas orientadas a pantallas amplias con muchos datos por petición; el BFF Móvil compone respuestas compactas y además gestiona el protocolo de sincronización offline. Sin esta capa, o bien el núcleo se contamina con formatos específicos de canal, o bien el móvil paga el costo de recibir cargas útiles pensadas para web.

**Núcleo de negocio.** Siete servicios delimitados por contexto de dominio: Cotización y Rating, Perfilamiento y Scoring, Suscripción y Emisión, Pólizas, Siniestros, Pagos y Recaudo, y Consentimientos y Auditoría. La frontera de cada servicio coincide con una frontera de lenguaje del negocio, no con una capa técnica. Los servicios se comunican de forma síncrona solo cuando el resultado es necesario para responder al usuario; el resto de la colaboración ocurre por eventos.

**Plataforma de datos.** PostgreSQL para lo transaccional, Redis como caché de perfiles de riesgo, Kafka como bus de eventos de dominio y almacenamiento de objetos con bloqueo de escritura para documentos y auditoría.

**Adaptadores externos.** Cada proveedor externo —Open Finance, Open Data, KYC/AML, pasarelas de pago y firma electrónica— se alcanza exclusivamente a través de un adaptador que traduce entre el modelo del proveedor y el modelo de dominio de Solventa. Ningún servicio del núcleo conoce el formato de un proveedor.

### 2.2 Vista de despliegue

La vista de despliegue muestra dónde se ejecuta cada componente y qué mecanismos de redundancia lo protegen.

![Figura 2. Vista de despliegue en AWS con redundancia multi-zona y región de recuperación](diagramas/imagenes/vista_despliegue.png)

**Distribución activo-activo.** Los nodos de EKS están repartidos entre dos zonas de disponibilidad y ambas reciben tráfico simultáneamente. No es una configuración activo-pasivo: si una zona cae, la capacidad de la otra ya está caliente y sirviendo peticiones, lo que hace que el tiempo de recuperación dependa del tiempo de detección del balanceador y no del tiempo de arranque de instancias. Esta es la decisión que hace alcanzable el RTO de 10 minutos del ASR-3.2.

**Datos.** RDS PostgreSQL opera en configuración multi-AZ con réplica en espera y promoción automática. La replicación síncrona hacia la zona B es lo que sostiene el RPO de 30 segundos. Redis y los brokers de Kafka también están replicados entre zonas.

**Región de recuperación.** Una réplica de lectura entre regiones hacia us-west-2 y replicación entre regiones del almacenamiento de objetos cubren el escenario de pérdida completa de la región principal. Este escenario está fuera del alcance de los experimentos del Proyecto Final 1, pero se documenta porque condiciona decisiones de diseño que sí se toman ahora, como no depender de identificadores generados localmente por instancia.

**Servicios regionales.** El servicio de gestión de llaves cifra los datos en reposo y firma las pólizas emitidas; el almacenamiento de objetos con bloqueo de escritura garantiza que un registro de auditoría no pueda alterarse ni siquiera con credenciales administrativas; la observabilidad centralizada recoge métricas y trazas distribuidas de todos los servicios.

### 2.3 Vista de información

La vista de información muestra las entidades de dominio, cómo se clasifican sus datos según sensibilidad y dónde se persiste cada clase.

![Figura 3. Vista de información: entidades, clasificación de datos y almacenamiento](diagramas/imagenes/vista_informacion.png)

**Entidades de dominio.** El cliente es la entidad raíz. De él dependen su perfil de riesgo, sus consentimientos y sus cotizaciones. Una cotización origina una póliza; una póliza ampara siniestros y genera pagos. Los socios distribuidores originan cotizaciones por el canal B2B, lo que significa que el modelo debe soportar una cotización sin cliente registrado previamente.

**Clasificación de datos.** El sistema clasifica los datos en tres niveles y el nivel determina el tratamiento, no la preferencia del desarrollador:

| Nivel | Contenido | Tratamiento |
|---|---|---|
| Restringido | Información personal identificable, datos financieros de Open Finance, datos de medios de pago | Tokenizado antes de persistirse; el dato original solo existe en el servicio de tokenización, cifrado con llave gestionada |
| Confidencial | Pólizas, siniestros, consentimientos | Cifrado en reposo; los documentos además firmados digitalmente |
| Interno | Catálogos de ramos, tarifas, parámetros de configuración | Sin cifrado especial; su exposición no genera daño |

Esta clasificación es la que hace verificable el ASR-4.1: la afirmación «cero datos personales en texto plano» solo se puede comprobar si antes se declaró qué cuenta como dato personal.

**Persistencia.** PostgreSQL guarda el estado transaccional; Redis guarda perfiles de riesgo con vencimiento de 15 minutos, lo que acota la ventana de exposición de datos derivados; el almacenamiento de objetos guarda documentos firmados y el registro de auditoría en modo de solo escritura; Kafka retiene los eventos de dominio 7 días para permitir su reproceso.

---

## 3. Diseño detallado — patrones aplicados y su razonamiento

Esta sección documenta cada patrón estructural adoptado. Para cada uno se indica el problema concreto que resuelve, el ASR que lo motiva, cómo se aplica en Solventa y qué se sacrifica al adoptarlo. Un patrón sin contrapartida declarada suele ser un patrón que no se entendió.

### 3.1 Tabla resumen

| # | Patrón | ASR que atiende | Componente donde se aplica |
|---|---|---|---|
| P1 | Caché de perfiles con lectura anticipada | ASR-1.1, ASR-1.2 | Perfilamiento y Scoring · Redis |
| P2 | Interruptor de circuito | ASR-1.2, ASR-3.1 | Adaptadores externos |
| P3 | Tiempo de espera acotado con reintento y espera creciente | ASR-1.2 | Adaptadores externos |
| P4 | Mamparo de aislamiento | ASR-3.1 | Núcleo de negocio |
| P5 | Puertos y adaptadores | ASR-2.1 | Adaptadores externos · núcleo |
| P6 | Estrategia con configuración externalizada | ASR-2.2 | Cotización y Rating |
| P7 | Backend por canal | ASR-3.3 | Capa BFF |
| P8 | Publicación y suscripción de eventos de dominio | ASR-1.2, ASR-2.1 | Event Bus |
| P9 | Tokenización de datos sensibles | ASR-4.1 | Consentimientos · Perfilamiento |
| P10 | Almacenamiento inmutable con firma digital | ASR-4.2 | Pólizas · auditoría |
| P11 | Cliente con prioridad al modo desconectado | ASR-3.3 | App móvil · BFF Móvil |
| P12 | Autoescalado con comprobaciones de salud | ASR-3.2 | EKS |

### 3.2 P1 — Caché de perfiles con lectura anticipada

**Problema.** El cálculo del perfil de riesgo requiere consultar Open Finance y Open Data. Esas consultas tardan cientos de milisegundos en el mejor caso. Si la cotización espera esa consulta de forma sincrónica, el objetivo de 200 ms del ASR-1.1 es inalcanzable por construcción: ninguna optimización interna compensa una llamada de red externa a un tercero.

**Aplicación.** El servicio de Perfilamiento consulta primero Redis. Si el perfil está presente y vigente, responde desde caché. Si no, consulta al proveedor externo, responde y almacena el resultado con vencimiento de 15 minutos. Para los clientes que llegan por un socio distribuidor con campaña programada, el perfil se precalcula en lote antes de la campaña.

**Razonamiento frente al ASR.** El ASR-1.1 exige p95 menor a 200 ms con 500 peticiones por minuto. Con una tasa de acierto de caché del 80% —conservadora para una ventana de 15 minutos en un flujo de cotización donde el usuario itera sobre planes— el percentil 95 queda determinado por el camino de caché y no por el camino externo. El ASR-1.2 va más lejos: exige que bajo degradación del proveedor el sistema siga respondiendo en 200 ms, lo que solo es posible si el perfil cacheado puede servir como respuesta válida y no solo como optimización.

**Contrapartida aceptada.** Un perfil cacheado puede estar hasta 15 minutos desactualizado. Para un scoring de seguro esto es tolerable: la situación financiera de una persona no cambia de forma material en ese intervalo. No sería tolerable para un saldo de cuenta, y por eso el caché se aplica al perfil derivado y nunca al dato financiero crudo.

### 3.3 P2 — Interruptor de circuito

**Problema.** Cuando un proveedor externo se degrada, el modo de falla más dañino no es que responda con error, sino que responda lento. Las peticiones se acumulan, los hilos del servicio se agotan esperando, y un problema de un proveedor se convierte en la caída completa de Solventa.

**Aplicación.** Cada adaptador externo está envuelto en un interruptor con tres estados. En estado cerrado las peticiones fluyen normalmente. Cuando la proporción de fallos o de respuestas por encima del umbral de tiempo supera el 50% en una ventana móvil, el interruptor abre y las peticiones siguientes fallan de inmediato sin tocar la red, activando la ruta de degradación. Tras un intervalo, el interruptor pasa a semiabierto y deja pasar un número reducido de peticiones de prueba.

**Razonamiento frente al ASR.** El ASR-1.2 describe exactamente este escenario: 5.000 peticiones concurrentes con el proveedor respondiendo por encima de 700 ms, y exige 0% de peticiones perdidas. Sin interruptor, las peticiones se pierden por agotamiento de recursos. Con interruptor, la petición no se pierde: se atiende por la ruta degradada usando el perfil cacheado. La diferencia entre cumplir y no cumplir el ASR-1.2 no está en la velocidad del sistema sino en su capacidad de dejar de esperar a tiempo.

**Contrapartida aceptada.** Durante la apertura del interruptor, clientes cuyo perfil no está en caché reciben una cotización preliminar en lugar de una definitiva. Se prefiere una respuesta aproximada e inmediata sobre una respuesta exacta que no llega.

### 3.4 P3 — Tiempo de espera acotado con reintento y espera creciente

**Problema.** Un tiempo de espera mal calibrado anula el interruptor de circuito. Si el tiempo de espera del cliente supera el del usuario, el usuario abandona antes de que el sistema decida.

**Aplicación.** Cada llamada externa tiene un tiempo de espera explícito, derivado hacia atrás desde el presupuesto de latencia total: si el objetivo extremo a extremo es 200 ms, el adaptador de Open Finance no puede tener un tiempo de espera de 3 segundos. Los reintentos se aplican solo a operaciones idempotentes, con espera creciente y un componente aleatorio para no sincronizar a todos los clientes en la misma reintentada.

**Razonamiento frente al ASR.** Es el patrón que hace operativo el presupuesto de latencia del ASR-1.1. Un presupuesto de latencia que no se traduce en tiempos de espera configurados es una intención, no un mecanismo.

**Contrapartida aceptada.** Tiempos de espera agresivos aumentan la proporción de respuestas degradadas cuando la red está lenta pero funcional. Se acepta porque el ASR prioriza responder a tiempo sobre responder con el dato más fresco.

### 3.5 P4 — Mamparo de aislamiento

**Problema.** Servicios que comparten un mismo depósito de conexiones o de hilos se hunden juntos. Si Siniestros agota el depósito de conexiones a la base de datos, Cotización deja de responder aunque no tenga ningún problema propio.

**Aplicación.** Cada servicio tiene depósitos de recursos separados por dependencia: un depósito de conexiones para PostgreSQL, otro para Redis, otro por cada adaptador externo. En Kubernetes, cada servicio tiene límites propios de CPU y memoria.

**Razonamiento frente al ASR.** El ASR-3.1 exige disponibilidad de 99,9% con recuperación en menos de 30 segundos ante la caída de Redis. Sin aislamiento, la caída de Redis propaga la saturación a las conexiones de PostgreSQL y la recuperación deja de depender solo de Redis. Con aislamiento, el fallo queda confinado y la ruta de respaldo hacia PostgreSQL tiene recursos disponibles para operar.

**Contrapartida aceptada.** Se desperdicia capacidad: recursos reservados para una dependencia inactiva no se prestan a otra. Es el costo directo de que un fallo no se propague.

### 3.6 P5 — Puertos y adaptadores

**Problema.** El ASR-2.1 exige integrar una pasarela de pagos nueva en menos de 4 horas-hombre y sin modificar ningún servicio del núcleo. Si el servicio de Pagos conoce el formato de la pasarela, cada pasarela nueva obliga a modificarlo, probarlo y desplegarlo.

**Aplicación.** El núcleo define un puerto —una interfaz expresada en el lenguaje del dominio: autorizar cobro, confirmar cobro, reversar cobro— y no conoce ninguna implementación. Cada pasarela se integra escribiendo un adaptador que implementa ese puerto y traduce entre el modelo de la pasarela y el del dominio. La selección del adaptador ocurre por configuración según el país. Integrar una pasarela nueva es escribir una clase nueva y agregar una entrada de configuración: cero archivos modificados en el núcleo.

**Razonamiento frente al ASR.** La medida de respuesta del ASR-2.1 —«cero cambios en servicios del núcleo»— es una afirmación verificable sobre el diagrama de dependencias, no sobre la buena voluntad del equipo. La inversión de dependencias es lo que la vuelve estructuralmente cierta: el núcleo no puede depender de una pasarela porque la flecha de dependencia apunta al revés.

**Contrapartida aceptada.** Hay una capa de indirección adicional y un modelo de dominio que mantener en paralelo a los modelos de los proveedores. Para un sistema con un solo proveedor sería sobrecosto injustificado; con cinco categorías de proveedores externos y expansión a cuatro países, se paga solo.

### 3.7 P6 — Estrategia con configuración externalizada

**Problema.** El ASR-2.2 exige lanzar un ramo nuevo en dos semanas sin tocar la lógica central del motor de rating. Un motor con las reglas de cada ramo escritas en código requiere modificar, probar y desplegar el motor por cada ramo.

**Aplicación.** El motor de rating no conoce ramos: conoce cómo evaluar un árbol de reglas y cómo componer factores. Las reglas de cada ramo, sus factores, coberturas y parámetros viven en configuración versionada, no en el código. Añadir el seguro de mascota es cargar una definición nueva. Lo mismo aplica a la regionalización: los parámetros de México son una configuración, no una bifurcación del código.

**Razonamiento frente al ASR.** El objetivo de negocio de expandirse a tres países en 36 meses y el ASR-2.2 apuntan a la misma propiedad estructural: la variabilidad del negocio debe estar en los datos y no en el código. Si está en el código, cada variación cuesta un ciclo de despliegue y el plazo de dos semanas se consume en el proceso, no en el trabajo.

**Contrapartida aceptada.** Una configuración mal formada puede romper el motor en ejecución, un error que un compilador habría detectado. Se mitiga validando la definición contra un esquema al cargarla y ejecutando un juego de casos de referencia antes de activarla.

### 3.8 P7 — Backend por canal

**Problema.** Web y móvil tienen necesidades opuestas. Web puede recibir cargas útiles grandes en una sola petición; móvil necesita cargas pequeñas, tolerancia a red intermitente y un protocolo de sincronización. Un backend único termina sirviendo mal a ambos.

**Aplicación.** Dos backends: el BFF Web compone vistas ricas agregando varios servicios del núcleo en una respuesta; el BFF Móvil entrega cargas mínimas, gestiona el protocolo de sincronización con el almacenamiento local del dispositivo y resuelve conflictos.

**Razonamiento frente al ASR.** El ASR-3.3 exige que el 100% de las consultas de póliza funcionen sin conexión y que la sincronización tome 10 segundos o menos. Eso requiere lógica de sincronización con estado, versiones y resolución de conflictos, que no tiene ningún sentido en el canal web. Ponerla en un backend compartido obligaría al canal web a cargar con complejidad que no usa.

**Contrapartida aceptada.** Hay lógica de composición duplicada entre los dos BFF. Se acepta porque la alternativa —un backend que sirve a ambos— acopla la evolución de los dos canales: cada cambio para móvil obliga a re-probar web.

### 3.9 P8 — Publicación y suscripción de eventos de dominio

**Problema.** La emisión de una póliza dispara efectos en varios servicios: notificar al cliente, actualizar la administración de pólizas, registrar auditoría, alimentar tableros regulatorios. Si Emisión llama sincrónicamente a los cuatro, su latencia es la suma de las cuatro y su disponibilidad el producto de las cuatro.

**Aplicación.** Emisión publica un evento de dominio y termina. Los servicios interesados se suscriben y reaccionan a su ritmo. El bus retiene los eventos 7 días, lo que permite reprocesar cuando un consumidor estuvo caído o cuando se corrige un error de procesamiento.

**Razonamiento frente al ASR.** Sostiene el ASR-1.2 al sacar del camino crítico todo lo que no es necesario para responderle al usuario, y refuerza el ASR-2.1: agregar un consumidor nuevo —por ejemplo, un tablero regulatorio para un país nuevo— no requiere tocar el productor.

**Contrapartida aceptada.** Consistencia eventual. Durante un intervalo breve la póliza existe pero el tablero aún no la refleja. Es aceptable para efectos secundarios; no lo sería para el cobro de la prima, que por eso permanece sincrónico dentro de la transacción de emisión.

### 3.10 P9 — Tokenización de datos sensibles

**Problema.** El ASR-4.1 exige cero datos personales en texto plano en tránsito, y la regulación exige poder revocar un consentimiento con efecto en menos de 5 minutos. Si el dato personal está copiado en las bases de siete servicios, revocar significa borrarlo en siete lugares y demostrarlo.

**Aplicación.** Un único servicio custodia los datos sensibles. El resto del sistema opera sobre tokens que no tienen valor si se filtran. Un servicio que necesita el dato original debe solicitarlo presentando autorización, y cada solicitud queda registrada. Revocar un consentimiento es invalidar la capacidad de destokenizar, lo que surte efecto de inmediato en todo el sistema sin tocar siete bases de datos.

**Razonamiento frente al ASR.** Convierte la afirmación del ASR-4.1 en algo demostrable: para verificar que no hay información personal en texto plano basta con inspeccionar el tráfico y los volcados de las bases y comprobar que solo aparecen tokens. Con el dato replicado, la verificación tendría que ser exhaustiva sobre todo el sistema.

**Contrapartida aceptada.** El servicio de tokenización es un punto único de falla y un salto adicional de latencia en las operaciones que requieren el dato original. Se mitiga porque el camino crítico de cotización opera sobre el perfil derivado y no necesita destokenizar.

### 3.11 P10 — Almacenamiento inmutable con firma digital

**Problema.** El ASR-4.2 exige detectar en menos de 1 segundo cualquier alteración no autorizada de una póliza emitida, incluyendo alteraciones hechas con credenciales internas comprometidas. Un control basado en permisos no sirve: se asume que el atacante ya tiene los permisos.

**Aplicación.** Al emitirse, cada póliza se firma con una llave gestionada y se almacena en un contenedor con bloqueo de escritura que impide la modificación y el borrado durante el periodo de retención, incluso para cuentas administrativas. Cada lectura verifica la firma. Cada escritura genera un registro de auditoría inmutable con el servicio, el momento y la huella antes y después.

**Razonamiento frente al ASR.** El control no depende de que el atacante carezca de permisos, sino de que la plataforma de almacenamiento no acepte la operación. Esto cambia la naturaleza de la garantía: pasa de ser una política a ser una propiedad del sistema.

**Contrapartida aceptada.** El periodo de retención inmutable implica costo de almacenamiento que no se puede liberar anticipadamente, y errores legítimos no se corrigen borrando sino emitiendo un documento compensatorio. Es exactamente el comportamiento que la regulación espera de una aseguradora.

### 3.12 P11 — Cliente con prioridad al modo desconectado

**Problema.** El ASR-3.3 exige que el 100% de las consultas de póliza estén disponibles sin conexión. Un cliente que consulta al servidor y muestra un error cuando no hay red no puede cumplirlo, por rápido que sea el servidor.

**Aplicación.** La app trata el almacenamiento local cifrado como su fuente de lectura y la red como un mecanismo de actualización en segundo plano. Las pólizas se sincronizan al iniciar sesión y se conservan con vigencia de 24 horas. Las acciones ejecutadas sin conexión se encolan y se envían en orden al recuperar conectividad.

**Razonamiento frente al ASR.** La medida «100% de consultas disponibles sin conexión» solo es alcanzable si la ausencia de red es el caso normal y no la excepción. Esta es una decisión de diseño del cliente que no se puede añadir después: reordena de dónde lee la aplicación.

**Contrapartida aceptada.** Datos potencialmente desactualizados, resolución de conflictos y datos sensibles en el dispositivo. Se mitiga con vigencia de 24 horas, aviso visible al vencerse, precedencia del servidor ante conflicto y cifrado del almacenamiento local limitado a lo mínimo necesario para mostrar la póliza.

### 3.13 P12 — Autoescalado con comprobaciones de salud

**Problema.** El ASR-3.2 exige RTO de 10 minutos ante la pérdida de una zona. Si la recuperación depende de arrancar instancias nuevas, el tiempo lo determina el arranque en frío.

**Aplicación.** Los pods se distribuyen entre zonas con reglas de antiafinidad, de modo que ninguna zona concentra todas las réplicas de un servicio. Cada pod expone comprobaciones de vitalidad y de disponibilidad, y el balanceador retira de rotación al que no responde. El autoescalador horizontal reacciona al uso de CPU con umbral del 70% y ventana de 30 segundos, con reducción lenta para evitar oscilaciones.

**Razonamiento frente al ASR.** Al mantener capacidad activa en ambas zonas, la recuperación se reduce al tiempo de detección más el de redistribución, ambos del orden de decenas de segundos. El autoescalado cubre el segundo efecto de perder una zona: la zona superviviente recibe el doble de tráfico y debe crecer.

**Contrapartida aceptada.** Se paga capacidad ociosa en operación normal, del orden del doble de la estrictamente necesaria. Es el precio explícito de un RTO de minutos.

---

## 4. Decisiones de arquitectura y alternativas descartadas

Documentar lo que se descartó y por qué es tan informativo como documentar lo elegido.

| # | Decisión adoptada | Alternativas evaluadas | Razón del descarte |
|---|---|---|---|
| D1 | Microservicios por contexto de dominio | Monolito modular | El monolito habría simplificado el desarrollo en 8 semanas, pero impide escalar de forma independiente el servicio de scoring, que es el único con exigencia de latencia de 200 ms y el único con picos de 10× |
| D2 | PostgreSQL como almacenamiento transaccional | Base documental como primaria | Restricción dura del proyecto; además la emisión requiere transacciones con garantías fuertes entre póliza, pago y consentimiento |
| D3 | Kafka como bus de eventos | Cola de mensajes tradicional | La retención y la relectura de eventos son necesarias para reprocesar y para incorporar consumidores nuevos sin coordinación con el productor |
| D4 | Dos BFF, uno por canal | BFF único compartido | La lógica de sincronización offline es específica de móvil; compartirla acopla la evolución de ambos canales |
| D5 | Tokenización centralizada | Cifrado a nivel de campo en cada servicio | El cifrado por campo replica el dato en siete bases y hace que revocar un consentimiento en menos de 5 minutos sea inverificable |
| D6 | Multi-AZ activo-activo | Activo-pasivo con recuperación | Un esquema pasivo hace que el RTO dependa del arranque en frío, lo que pone en riesgo el objetivo de 10 minutos del ASR-3.2 |
| D7 | Kotlin nativo para móvil | Framework multiplataforma | El acceso a biometría, cámara con validación de nitidez y almacenamiento seguro del dispositivo es de primera clase en nativo; el onboarding biométrico es el recorrido de mayor riesgo técnico |
| D8 | Angular para web | Alternativa basada en biblioteca | Decisión del equipo del 19 de agosto; el marco de trabajo completo aporta enrutamiento, formularios e internacionalización integrados, relevantes para los cuatro locales objetivo |

---

## 5. Propuesta de experimentos de arquitectura

### 5.1 Marco de experimentación

Un experimento de arquitectura no es una prueba de software. Una prueba verifica que el sistema hace lo que se especificó; un experimento verifica que una decisión de diseño produce la propiedad de calidad que se le atribuyó. Cada experimento de esta sección se formula como una hipótesis falsable: se define de antemano qué resultado la refutaría, porque un experimento que no puede fracasar no aporta información.

**Estructura común de cada experimento**

| Campo | Contenido |
|---|---|
| Propósito | Qué decisión de diseño se está poniendo a prueba |
| Hipótesis | Afirmación falsable derivada del ASR |
| Montaje | Cómo se construye el escenario |
| Respuesta esperada | Qué debe observarse si la hipótesis es correcta |
| Criterio de refutación | Qué observación obligaría a revisar el diseño |
| Tecnologías | Herramientas necesarias |
| Esfuerzo | Horas-hombre estimadas |

### 5.2 EXP-01 — Latencia del motor de scoring en carga normal

| Campo | Contenido |
|---|---|
| **ASR** | ASR-1.1 · Patrón P1 (caché de perfiles) |
| **Propósito** | Verificar que la estrategia de caché de perfiles permite sostener el objetivo de latencia bajo la carga nominal, y establecer la tasa de acierto de caché real |
| **Hipótesis** | Con 500 peticiones por minuto sostenidas y una tasa de acierto de caché igual o superior al 80%, el percentil 95 del tiempo de respuesta del endpoint de cotización se mantiene por debajo de 200 ms y el percentil 99 por debajo de 400 ms |
| **Montaje** | Entorno en contenedores con el servicio de Cotización, el de Perfilamiento, PostgreSQL y Redis. Un simulador reemplaza al proveedor Open Finance con una latencia fija de 300 ms. Se genera carga durante 10 minutos con una distribución de clientes que produce la tasa de acierto objetivo |
| **Respuesta esperada** | p95 < 200 ms · p99 < 400 ms · tasa de acierto ≥ 80% · 0 errores |
| **Criterio de refutación** | Si el p95 supera 200 ms con la tasa de acierto en el objetivo, el problema no está en el caché sino en el procesamiento interno, y obliga a revisar el diseño del motor de rating |
| **Tecnologías** | JMeter · Docker Compose · simulador HTTP con latencia controlada · Redis · métricas de latencia por percentil |
| **Esfuerzo** | 10 horas-hombre |
| **Prioridad** | Alta — se ejecuta en el Proyecto Final 1 |

### 5.3 EXP-02 — Degradación elegante ante proveedor externo lento

| Campo | Contenido |
|---|---|
| **ASR** | ASR-1.2 · Patrones P2 y P3 (interruptor de circuito, tiempos de espera) |
| **Propósito** | Verificar que el interruptor de circuito convierte una degradación del proveedor externo en respuestas degradadas y no en peticiones perdidas |
| **Hipótesis** | Con el proveedor Open Finance respondiendo por encima de 700 ms y una carga de 10× la nominal, el interruptor abre en menos de 10 segundos y el sistema mantiene el p95 por debajo de 200 ms sirviendo desde caché, con 0% de peticiones perdidas por agotamiento de recursos |
| **Montaje** | Mismo entorno del EXP-01. Se inyecta latencia creciente en el proveedor simulado hasta superar el umbral, sosteniendo el pico de carga. Se instrumenta el estado del interruptor para registrar la transición |
| **Respuesta esperada** | Interruptor abierto en < 10 s · p95 < 200 ms durante la degradación · 0% de peticiones perdidas · retorno a estado cerrado tras normalizar el proveedor |
| **Criterio de refutación** | Peticiones perdidas por agotamiento del depósito de conexiones indicaría que los tiempos de espera están mal calibrados frente al presupuesto de latencia, o que falta aislamiento por mamparo |
| **Tecnologías** | JMeter · simulador con inyección de latencia · biblioteca de interruptor de circuito · métricas de estado del interruptor |
| **Esfuerzo** | 12 horas-hombre |
| **Prioridad** | Alta — se ejecuta en el Proyecto Final 1 |

### 5.4 EXP-03 — Recuperación ante caída del caché

| Campo | Contenido |
|---|---|
| **ASR** | ASR-3.1 · Patrones P2 y P4 (interruptor, mamparo) |
| **Propósito** | Verificar que la pérdida del caché degrada el rendimiento sin interrumpir el servicio ni perder transacciones en curso |
| **Hipótesis** | Al detener el contenedor de Redis durante operación normal, el sistema detecta la falla y redirige al perfilamiento directo en menos de 30 segundos, sin perder ninguna transacción activa y manteniendo disponibilidad por encima del 99,9% en la ventana medida |
| **Montaje** | Carga sostenida nominal. Se detiene el contenedor de Redis a mitad del ensayo y se reinicia dos minutos después. Se registran latencia, errores y transacciones completadas durante todo el ciclo |
| **Respuesta esperada** | Recuperación < 30 s · 0 transacciones perdidas · degradación de latencia acotada y transitoria · recuperación automática al volver el caché |
| **Criterio de refutación** | Errores propagados a operaciones que no dependen del caché indicaría que el aislamiento por mamparo no está funcionando |
| **Tecnologías** | Docker Compose · JMeter · métricas de disponibilidad y de tasa de error |
| **Esfuerzo** | 8 horas-hombre |
| **Prioridad** | Alta — se ejecuta en el Proyecto Final 1 |

### 5.5 EXP-04 — Confidencialidad de los datos de Open Finance

| Campo | Contenido |
|---|---|
| **ASR** | ASR-4.1 · Patrón P9 (tokenización) |
| **Propósito** | Verificar que ningún dato personal circula ni se persiste en texto plano fuera del servicio de tokenización |
| **Hipótesis** | En el recorrido completo de cotización con Open Finance, el 100% de las transmisiones usa TLS 1.3, el 100% de los campos personales sale tokenizado del servicio de perfilamiento y la inspección de las bases de datos y de los mensajes del bus no revela ningún dato personal en texto plano |
| **Montaje** | Se ejecuta el recorrido completo. Se captura el tráfico entre servicios, se vuelcan las tablas de PostgreSQL y los mensajes de los temas de Kafka, y se buscan patrones de datos personales conocidos sembrados como cebo |
| **Respuesta esperada** | 0 coincidencias de datos personales fuera del servicio de tokenización · TLS 1.3 en el 100% de las conexiones · registro de auditoría con una entrada por cada destokenización |
| **Criterio de refutación** | Una sola coincidencia en un volcado o en un mensaje del bus refuta la hipótesis e identifica el punto exacto de fuga |
| **Tecnologías** | OWASP ZAP · captura de tráfico · consultas de verificación sobre PostgreSQL · consumidor de inspección de Kafka · datos cebo |
| **Esfuerzo** | 12 horas-hombre |
| **Prioridad** | Alta — se ejecuta en el Proyecto Final 1 |

### 5.6 EXP-05 — Costo de integrar una pasarela de pagos nueva

| Campo | Contenido |
|---|---|
| **ASR** | ASR-2.1 · Patrón P5 (puertos y adaptadores) |
| **Propósito** | Medir empíricamente el costo de la modificabilidad que el diseño promete, en lugar de afirmarlo |
| **Hipótesis** | Un integrante que no participó en el diseño del módulo de pagos puede integrar una pasarela nueva en menos de 4 horas-hombre, sin modificar ningún archivo de los servicios del núcleo |
| **Montaje** | Se define una pasarela ficticia con un contrato distinto al de la existente. Un integrante distinto al autor del módulo implementa el adaptador. Se cronometra el trabajo y se mide con control de versiones qué archivos se tocaron |
| **Respuesta esperada** | < 4 horas-hombre · 0 archivos modificados fuera del directorio de adaptadores y de la configuración · pruebas del núcleo pasando sin cambios |
| **Criterio de refutación** | Cualquier modificación necesaria en un servicio del núcleo refuta el ASR-2.1 y señala una fuga de abstracción en la definición del puerto |
| **Tecnologías** | Repositorio con registro de cambios por archivo · simulador de pasarela · cronometraje del trabajo |
| **Esfuerzo** | 6 horas-hombre |
| **Prioridad** | Media — se ejecuta si hay holgura |

### 5.7 EXP-06 — Continuidad del cliente móvil sin conexión

| Campo | Contenido |
|---|---|
| **ASR** | ASR-3.3 · Patrones P7 y P11 (backend por canal, cliente offline-first) |
| **Propósito** | Verificar que la billetera de pólizas es plenamente funcional sin red y que la sincronización posterior cumple el objetivo de tiempo |
| **Hipótesis** | Con la sesión iniciada y las pólizas sincronizadas, el 100% de las consultas de póliza responde sin conexión, y al recuperar conectividad la sincronización completa en 10 segundos o menos sin intervención del usuario |
| **Montaje** | Dispositivo o emulador Android con la app instalada y sesión iniciada. Se activa el modo avión, se ejecuta el conjunto de consultas de la billetera y se registran los resultados. Se restaura la conectividad y se cronometra la sincronización. Se verifica además que el almacenamiento local esté cifrado |
| **Respuesta esperada** | 100% de consultas resueltas sin red · sincronización ≤ 10 s · aviso de datos desactualizados al superar 24 horas · almacenamiento local ilegible fuera de la app |
| **Criterio de refutación** | Cualquier consulta que requiera red refuta la hipótesis; una sincronización por encima de 10 s obliga a revisar el protocolo del BFF Móvil |
| **Tecnologías** | Emulador Android · Espresso · control de conectividad del emulador · inspección del almacenamiento local |
| **Esfuerzo** | 10 horas-hombre |
| **Prioridad** | Media — se ejecuta si hay holgura |

### 5.8 EXP-07 — Integridad de las pólizas emitidas

| Campo | Contenido |
|---|---|
| **ASR** | ASR-4.2 · Patrón P10 (almacenamiento inmutable con firma) |
| **Propósito** | Verificar que una alteración con credenciales válidas es rechazada por la plataforma y detectada en el plazo exigido |
| **Hipótesis** | Un intento de modificar directamente una póliza emitida en el almacenamiento de objetos, usando credenciales administrativas, es rechazado por el bloqueo de escritura y queda registrado en el log de auditoría en menos de 1 segundo |
| **Montaje** | Se emite una póliza y se verifica su firma. Se intenta sobrescribirla y borrarla con credenciales administrativas. Se mide el tiempo entre el intento y la aparición de la entrada de auditoría. Se intenta además alterar el propio registro de auditoría |
| **Respuesta esperada** | Escritura y borrado rechazados por la plataforma · entrada de auditoría en < 1 s · verificación de firma detectando cualquier alteración · registro de auditoría inalterable |
| **Criterio de refutación** | Si la sobrescritura tiene éxito, la configuración de retención es incorrecta; si el registro tarda más de 1 segundo, la ruta de auditoría es demasiado lenta y debe pasar a un camino sincrónico |
| **Tecnologías** | Almacenamiento de objetos con bloqueo de escritura · servicio de llaves para firma · cliente administrativo · verificación de huellas |
| **Esfuerzo** | 8 horas-hombre |
| **Prioridad** | Media — se ejecuta si hay holgura |

### 5.9 EXP-08 — Costo de configurar un ramo nuevo

| Campo | Contenido |
|---|---|
| **ASR** | ASR-2.2 · Patrón P6 (estrategia con configuración externalizada) |
| **Propósito** | Verificar que un ramo nuevo es un cambio de configuración y no un cambio de código |
| **Hipótesis** | Un ramo no contemplado en el diseño inicial queda disponible en el flujo de cotización mediante configuración, sin modificar la lógica del motor de rating |
| **Montaje** | Se define un ramo nuevo con factores y coberturas distintos a los existentes. Se carga su definición y se ejecuta una cotización de extremo a extremo. Se verifica con control de versiones qué archivos se modificaron |
| **Respuesta esperada** | Ramo disponible en el flujo · 0 archivos de lógica del motor modificados · validación de esquema rechazando definiciones mal formadas |
| **Criterio de refutación** | Cualquier cambio en el motor de rating refuta el ASR-2.2 |
| **Tecnologías** | Configuración versionada · validación por esquema · casos de referencia del motor |
| **Esfuerzo** | 6 horas-hombre |
| **Prioridad** | Baja — se difiere al Proyecto Final 2 |

### 5.10 EXP-09 — Pérdida de una zona de disponibilidad

| Campo | Contenido |
|---|---|
| **ASR** | ASR-3.2 · Patrón P12 (multi-AZ activo-activo con autoescalado) |
| **Propósito** | Verificar los objetivos de tiempo y de punto de recuperación ante la pérdida completa de una zona |
| **Hipótesis** | Ante la pérdida de una zona, el balanceador redirige el tráfico a la zona superviviente, la réplica de base de datos se promueve automáticamente, y el servicio se restablece con RTO ≤ 10 minutos y RPO ≤ 30 segundos |
| **Montaje** | Se induce la falla de una zona bajo carga sostenida. Se registra el momento de la falla, el de la detección, el de la promoción de la réplica y el del restablecimiento. Se comparan las transacciones confirmadas antes de la falla con las presentes después |
| **Respuesta esperada** | RTO ≤ 10 min · RPO ≤ 30 s · autoescalado absorbiendo el tráfico redirigido · 0 transacciones confirmadas perdidas |
| **Criterio de refutación** | Un RTO superior indicaría que el esquema opera de hecho como activo-pasivo; pérdida de transacciones confirmadas indicaría que la replicación no es síncrona |
| **Tecnologías** | Servicio de inyección de fallas de la nube · métricas de disponibilidad · verificación de consistencia transaccional |
| **Esfuerzo** | 14 horas-hombre |
| **Prioridad** | Baja — se difiere al Proyecto Final 2 por dependencia de infraestructura de nube con costo |

### 5.11 Resumen de esfuerzo y planificación

| Experimento | ASR | Esfuerzo | Prioridad | Cuándo |
|---|---|---|---|---|
| EXP-01 Latencia en carga normal | ASR-1.1 | 10 h | Alta | Semana 5 |
| EXP-02 Degradación elegante | ASR-1.2 | 12 h | Alta | Semana 5 |
| EXP-03 Caída del caché | ASR-3.1 | 8 h | Alta | Semana 6 |
| EXP-04 Confidencialidad Open Finance | ASR-4.1 | 12 h | Alta | Semana 6 |
| EXP-05 Pasarela de pagos nueva | ASR-2.1 | 6 h | Media | Semana 7 si hay holgura |
| EXP-06 Continuidad offline móvil | ASR-3.3 | 10 h | Media | Semana 7 si hay holgura |
| EXP-07 Integridad de pólizas | ASR-4.2 | 8 h | Media | Semana 8 si hay holgura |
| EXP-08 Ramo nuevo por configuración | ASR-2.2 | 6 h | Baja | Proyecto Final 2 |
| EXP-09 Pérdida de zona | ASR-3.2 | 14 h | Baja | Proyecto Final 2 |
| **Total comprometido en el Proyecto Final 1** | | **42 h** | | |
| **Total del programa completo** | | **86 h** | | |

Las 42 horas comprometidas equivalen a 21 puntos de historia con la convención del equipo de 1 punto igual a 2 horas. Esa cifra está contenida dentro de los 42 puntos de historia asignados a las historias de arquitectura en el alcance del Proyecto Final 1, porque la construcción del mecanismo y la ejecución del experimento que lo valida son parte de la misma historia.

---

## 6. Refinamiento de la estrategia de pruebas

La estrategia de pruebas versión 2.0, entregada en la semana 3, se refina en tres puntos como consecuencia del diseño detallado de este documento.

### 6.1 Cambios respecto a la versión 2.0

| # | Cambio | Motivo |
|---|---|---|
| 1 | Se incorpora el nivel de **prueba de arquitectura** como categoría propia, distinta de la prueba de integración | Un experimento de arquitectura valida una propiedad de calidad, no una funcionalidad; mezclarlo con las pruebas de integración oculta que su criterio de éxito es una medida y no una aserción de igualdad |
| 2 | Se alinean los objetivos de cobertura con el backlog descompuesto de 62 historias | La versión 2.0 se escribió contra un backlog de 20 historias; los umbrales por componente se redistribuyen según el nuevo reparto |
| 3 | Se elimina toda referencia residual al stack anterior en los documentos fuente | Los entregables ya se migraron a Angular y Kotlin nativo, pero los archivos fuente en el repositorio conservan referencias al stack descartado, lo que arrastra el error a cada versión nueva |

### 6.2 Niveles de prueba consolidados

| Nivel | Qué verifica | Herramientas | Criterio |
|---|---|---|---|
| Unitaria | Lógica de una unidad aislada | pytest (backend) · Jasmine y Karma (web) · JUnit 5 y MockK (móvil) | 80% de líneas en backend · 70% en clientes |
| Módulo | Un servicio completo con sus dependencias simuladas | pytest con dobles de prueba | Todos los criterios de aceptación de las historias del servicio |
| Integración | Colaboración real entre servicios | pytest con contenedores de prueba · Postman | Recorridos de cotización, emisión y siniestro completos |
| Extremo a extremo | Recorrido de usuario en el cliente real | Playwright (web) · Espresso (móvil) | Los dos recorridos críticos del alcance del Proyecto Final 1 |
| **Arquitectura** | Que una decisión de diseño produce la propiedad de calidad atribuida | JMeter · OWASP ZAP · inyección de fallas | La medida de respuesta del ASR correspondiente |
| Rendimiento | Comportamiento bajo carga | JMeter | Objetivos de percentil de los ASR de latencia |
| Seguridad | Ausencia de vulnerabilidades conocidas y de fuga de datos | OWASP ZAP · inspección de volcados | 0 hallazgos críticos · 0 datos personales en texto plano |
| Internacionalización | Comportamiento por locale | Pruebas parametrizadas por locale | 4 locales: CO, MX, CL, PE |

### 6.3 Relación entre experimentos y pruebas

Los experimentos de la sección §5 no reemplazan a las pruebas: las anteceden. Un experimento responde «¿esta decisión de diseño produce la propiedad que necesito?». Una prueba responde «¿esta propiedad sigue presente después del último cambio?». Por eso cada experimento que resulte satisfactorio deja como residuo una prueba automatizada que lo vuelve a ejecutar de forma continua: el EXP-01 se convierte en una prueba de rendimiento periódica, y el EXP-04 en una verificación de seguridad dentro del proceso de integración.

---

## 7. Plan de trabajo y tablero

### 7.1 Estado del proyecto

| Semana | Foco | Estado |
|---|---|---|
| 1 (3–9 ago) | Acta de constitución y backlog inicial | Completada |
| 2 (10–16 ago) | Visión de arquitectura, EDT y estrategia de pruebas | Completada |
| 3 (17–23 ago) | Escenarios de calidad, historias de usuario y frameworks | Completada · corregida en esta entrega |
| 4 (24–30 ago) | Modelos de arquitectura, patrones y diseño de experimentos | Esta entrega |
| 5 (31 ago–6 sep) | Ejecución de EXP-01 y EXP-02 · construcción del núcleo de cotización | Planificada |
| 6 (7–13 sep) | Ejecución de EXP-03 y EXP-04 · cliente web | Planificada |
| 7 (14–20 sep) | Cliente móvil · experimentos de holgura | Planificada |
| 8 (21–27 sep) | Integración, cierre y presentación final | Planificada |

### 7.2 Compromiso por sprint

Con una velocidad efectiva de 19 puntos de historia por semana y 76 puntos disponibles para las semanas 5 a 8, el compromiso es el siguiente:

| Semana | Historias comprometidas | SP |
|---|---|---|
| 5 | HU-ARQ-05, HU-ARQ-07, FE-05.2, FE-01.1 | 18 |
| 6 | HU-ARQ-06, FE-01.2, FE-01.3 | 18 |
| 7 | HU-ARQ-03, HU-ARQ-08, FE-01.4 | 19 |
| 8 | FE-02.1, FE-02.4, FE-02.5, FE-06.1, FE-06.2, FE-07.1, FE-07.2 | 21 |
| **Total** | **17 historias** | **76** |

El detalle completo del backlog de 62 historias, el cálculo de la capacidad del equipo y el criterio de corte de alcance están en el documento de historias de usuario versión 2.0 que acompaña esta entrega.

### 7.3 Correcciones aplicadas a la entrega de la semana 3

| Observación recibida | Corrección | Dónde verificarla |
|---|---|---|
| Se esperaba la lista completa de historias, no solo 20 | Backlog descompuesto a 62 historias; promedio de 7,6 a 3,7 SP por historia | Documento de historias de usuario v2.0, §4 |
| No se encontró evidencia del cálculo de capacidad | Cálculo paso a paso incorporado dentro del entregable | Documento de historias de usuario v2.0, §2 |
| Backlog de 152 SP con solo 20 historias | Re-estimación de abajo hacia arriba a 229 SP y corte explícito de alcance | Documento de historias de usuario v2.0, §3 y §5 |

### 7.4 Tablero

El tablero del proyecto en Jira refleja el backlog descompuesto, con épicas, estimación en puntos de historia, prioridad y la asociación de cada historia de arquitectura con su ASR.

**Tablero Jira:** https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/boards
**Backlog:** https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/backlog
**Repositorio:** https://github.com/Migue765/proyecto-final-uniandes
