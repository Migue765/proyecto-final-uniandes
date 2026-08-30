---portada
institucion: Universidad de los Andes
facultad: Facultad de Ingeniería · Departamento de Ingeniería de Sistemas y Computación
programa: Maestría en Ingeniería de Software
curso: MISW4501 — Proyecto Final
titulo: Entrega Semana 4
subtitulo: Modelos de arquitectura, patrones de diseño, experimentos, estrategia de pruebas y plan de trabajo
proyecto: Proyecto Solventa — Aseguradora digital sobre Finanzas Abiertas
entrega: Documento único de entrega
grupo: Grupo 2
integrantes: Jazmin Natalia Córdoba Puerto ~ Gerente del proyecto — Usabilidad y entrega|Juan Esteban Mejía Izasa ~ Web front, integración de APIs y pagos|Miguel Alejandro Gómez Alarcón ~ Arquitectura, Open Finance, KYC, rendimiento y seguridad|Angie Natalia Arandio Niño ~ Dominio, web back, móvil y pruebas unitarias
fecha: Bogotá D.C. · 30 de agosto de 2026
---

## Mapa de la entrega

Este documento contiene **la totalidad de los entregables de la semana 4**. Cada ítem de la rúbrica se encuentra completo dentro de estas páginas; no se remite a archivos externos para ningún contenido calificable.

| # | Ítem de la rúbrica | Puntos | Dónde está en este documento |
|---|---|---|---|
| 1 | **Hoja de trabajo: modelos de arquitectura, patrones detallados y experimentos** | **70** | |
| 1a | Modelos de arquitectura — vista funcional, de despliegue y de información | 20 | §2, con las tres figuras embebidas |
| 1b | Diseño detallado con patrones y razonamiento, en relación con los ASR | 30 | §3: vista de asignación de patrones, matriz de trazabilidad patrón→táctica→componente→ASR, estructura de los patrones críticos y los doce patrones en detalle. §4: decisiones y alternativas descartadas |
| 1c | Propuesta de experimentos — propósito, respuesta esperada, tecnologías y esfuerzo | 20 | §5 (ocho experimentos que cubren los nueve ASR) |
| 2 | **Refinamiento de la estrategia de pruebas** | **10** | §6 |
| 3 | **Actualización del plan de trabajo y tablero** | **10** | §7: qué es un punto de historia, cálculo de la capacidad del equipo paso a paso, distribución del esfuerzo por integrante, compromiso por sprint y estado del tablero |
| 4 | **Video con evidencias** | **10** | §8, con el enlace y el guion completo por presentador |
| — | *Corrección de la entrega de la semana 3* | *Reentrega* | §9, con remisión al documento de historias de usuario v2.0 |

**Documento que acompaña esta entrega.** El backlog completo de 62 historias de usuario con sus criterios de aceptación, el cálculo de la capacidad del equipo y el corte de alcance entre Proyecto Final 1 y 2 están en `historias_de_usuario_v2.docx`, que constituye la corrección del entregable de la semana 3. En §9 se resume qué se corrigió y dónde verificarlo.

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

### 3.2 Marco: patrón, táctica y su relación con el ASR

Los tres conceptos operan en niveles distintos y conviene no confundirlos, porque el profesor evalúa la relación entre ellos:

| Concepto | Qué es | Ejemplo en Solventa |
|---|---|---|
| **Atributo de calidad (ASR)** | La propiedad que el sistema debe exhibir, expresada como escenario medible | ASR-1.1: p95 < 200 ms con 500 req/min |
| **Táctica** | Una decisión de diseño elemental que influye sobre un atributo de calidad. Es el «qué se hace» | Mantener múltiples copias de datos computados |
| **Patrón** | Una composición de tácticas con una estructura conocida y contrapartidas documentadas. Es el «cómo se materializa» | Cache-Aside, que compone esa táctica con una política de vencimiento y una de escritura |

La cadena de razonamiento que sigue este documento es siempre la misma: **un ASR exige una propiedad → esa propiedad se consigue con una o varias tácticas → esas tácticas se materializan en un patrón → ese patrón se asigna a componentes concretos → un experimento mide si funcionó.**

### 3.3 Vista de asignación de patrones

Esta vista muestra dónde vive cada patrón dentro de la arquitectura. Las anotaciones entre llaves indican el patrón que gobierna ese componente o esa capa.

![Figura 4. Asignación de los doce patrones sobre los componentes de la arquitectura](diagramas/imagenes/vista_patrones.png)

Tres observaciones sobre la asignación:

1. **Los patrones de disponibilidad se concentran en la frontera con lo externo.** El interruptor de circuito, el tiempo de espera acotado y el adaptador viven todos en la capa de adaptadores, porque es ahí donde el sistema deja de controlar lo que ocurre. Ningún servicio del núcleo implementa resiliencia frente a terceros: la hereda de la frontera.
2. **El mamparo es transversal al núcleo y no un componente.** No aparece como una caja porque no lo es: es la política de que cada servicio tenga depósitos de recursos separados por dependencia. Se representa como propiedad de la capa.
3. **La tokenización es el único componente del núcleo dibujado en color de frontera.** Es deliberado: aunque se ejecuta dentro del núcleo, actúa como frontera de custodia, y esa dualidad es lo que hace verificable el ASR-4.1.

### 3.4 Matriz de trazabilidad

Cada fila se lee así: el patrón materializa esas tácticas, vive en esos componentes, existe para satisfacer ese ASR, y ese experimento comprueba si lo consigue.

| Patrón | Tácticas que materializa | Componentes donde vive | ASR | Experimento |
|---|---|---|---|---|
| **P1** Cache-Aside | Mantener múltiples copias de datos computados · Reducir la demanda computacional en el camino crítico | Perfilamiento · Redis | ASR-1.1 · ASR-1.2 | EXP-01 |
| **P2** Interruptor de circuito | Detectar fallas por tasa de respuesta · Degradación elegante | Adaptadores externos | ASR-1.2 · ASR-3.1 | EXP-02 · EXP-04 |
| **P3** Tiempo de espera con reintento | Acotar el tiempo de espera · Reintento de operaciones idempotentes | Adaptadores externos | ASR-1.2 | EXP-02 |
| **P4** Mamparo de aislamiento | Contener el fallo limitando recursos compartidos | Todo el núcleo (depósitos por dependencia) | ASR-3.1 | EXP-04 |
| **P5** Puertos y adaptadores | Encapsular la variabilidad · Invertir dependencias · Diferir el enlace | Pagos & Recaudo · capa de adaptadores | ASR-2.1 | EXP-03 |
| **P6** Strategy con configuración externalizada | Encapsular la variabilidad · Diferir el enlace al despliegue | Cotización & Rating · configuración de ramos | ASR-2.2 | EXP-03 |
| **P7** Backend por canal | Aislar la variabilidad del canal · Reducir el acoplamiento entre canales | BFF Web · BFF Móvil | ASR-3.3 | EXP-06 |
| **P8** Publicación y suscripción | Sacar del camino crítico lo no esencial · Desacoplar productor y consumidor | Event Bus · servicios del núcleo | ASR-1.2 · ASR-2.1 | EXP-02 |
| **P9** Tokenización | Limitar el acceso por custodia centralizada · Cifrar en tránsito y reposo · Auditar cada acceso | Tokenización · Perfilamiento · Consentimientos | ASR-4.1 | EXP-07 |
| **P10** Almacenamiento inmutable con firma | Verificar integridad · Registro no repudiable · Autorizar por token de servicio | Pólizas · Object Storage · Auditoría | ASR-4.2 | EXP-08 |
| **P11** Cliente offline-first | Mantener copia local · Sincronización diferida · Acotar la vigencia del dato replicado | App móvil · BFF Móvil | ASR-3.3 | EXP-06 |
| **P12** Multi-AZ con autoescalado | Redundancia activa · Replicación síncrona · Detección por comprobación de salud | EKS · RDS · MSK | ASR-3.2 | EXP-05 |

**Cobertura.** Los nueve ASR quedan cubiertos por al menos un patrón, y los doce patrones tienen al menos un ASR que los justifica. No hay patrones huérfanos —adoptados sin un requisito que los exija— ni ASR sin mecanismo asignado.

### 3.5 Estructura de los patrones críticos

Los tres patrones siguientes se detallan estructuralmente porque son los que sostienen los ASR de mayor exigencia y los que más fácilmente se implementan mal.

#### El camino de latencia: P1 + P2 + P3 + P4 operando juntos

Los cuatro patrones del camino crítico no actúan por separado sino como una cadena de decisiones. Este diagrama muestra el recorrido completo de una solicitud de cotización y dónde interviene cada uno.

![Figura 5. Composición de los patrones Cache-Aside, Interruptor de circuito, Timeout y Mamparo en el camino de cotización](diagramas/imagenes/patron_latencia.png)

La lectura importante es que **hay tres salidas distintas hacia una respuesta válida** y ninguna es un error: acierto de caché en menos de 20 ms, respuesta del proveedor dentro del presupuesto de 150 ms, o prima preliminar en modo degradado. El sistema nunca se queda esperando, que es precisamente lo que exige la medida de «0% de solicitudes perdidas» del ASR-1.2.

#### La modificabilidad: P5 + P6 y la dirección de las dependencias

![Figura 6. Puertos, adaptadores y configuración externalizada: ninguna flecha sale del núcleo](diagramas/imagenes/patron_puertos_adaptadores.png)

Lo relevante de este diagrama no son las cajas sino **el sentido de las flechas**. El núcleo define los puertos `PasarelaDePago` y `ReglaDeRamo` y no depende de nada externo; los adaptadores y los archivos de configuración apuntan *hacia* el núcleo. Por eso la afirmación del ASR-2.1 —«cero cambios en servicios del núcleo»— no es una promesa de disciplina del equipo sino una propiedad estructural: agregar `AdaptadorSPEI` no puede obligar a modificar el núcleo porque no existe ninguna arista que vaya en esa dirección.

#### La confidencialidad: P9 y la frontera de custodia

![Figura 7. Tokenización con custodia única: aguas adentro solo circulan tokens](diagramas/imagenes/patron_tokenizacion.png)

El diagrama define una **frontera de custodia**. A su izquierda existe el dato original; a su derecha solo existen tokens, que no tienen valor si se filtran. Esa frontera es lo que convierte el ASR-4.1 en algo verificable: para comprobar que no hay datos personales en texto plano basta con inspeccionar todo lo que hay a la derecha y comprobar que solo aparecen tokens. Sin la frontera, la verificación tendría que ser exhaustiva sobre los siete servicios del núcleo.

Además, **revocar un consentimiento se reduce a invalidar la capacidad de destokenizar**, lo que surte efecto de inmediato en todo el sistema. Con el dato replicado en cada servicio, cumplir el plazo regulatorio de 5 minutos exigiría borrarlo en siete bases de datos y demostrarlo.

### 3.6 P1 — Caché de perfiles con lectura anticipada

**Problema.** El cálculo del perfil de riesgo requiere consultar Open Finance y Open Data. Esas consultas tardan cientos de milisegundos en el mejor caso. Si la cotización espera esa consulta de forma sincrónica, el objetivo de 200 ms del ASR-1.1 es inalcanzable por construcción: ninguna optimización interna compensa una llamada de red externa a un tercero.

**Aplicación.** El servicio de Perfilamiento consulta primero Redis. Si el perfil está presente y vigente, responde desde caché. Si no, consulta al proveedor externo, responde y almacena el resultado con vencimiento de 15 minutos. Para los clientes que llegan por un socio distribuidor con campaña programada, el perfil se precalcula en lote antes de la campaña.

**Razonamiento frente al ASR.** El ASR-1.1 exige p95 menor a 200 ms con 500 peticiones por minuto. Con una tasa de acierto de caché del 80% —conservadora para una ventana de 15 minutos en un flujo de cotización donde el usuario itera sobre planes— el percentil 95 queda determinado por el camino de caché y no por el camino externo. El ASR-1.2 va más lejos: exige que bajo degradación del proveedor el sistema siga respondiendo en 200 ms, lo que solo es posible si el perfil cacheado puede servir como respuesta válida y no solo como optimización.

**Contrapartida aceptada.** Un perfil cacheado puede estar hasta 15 minutos desactualizado. Para un scoring de seguro esto es tolerable: la situación financiera de una persona no cambia de forma material en ese intervalo. No sería tolerable para un saldo de cuenta, y por eso el caché se aplica al perfil derivado y nunca al dato financiero crudo.

### 3.7 P2 — Interruptor de circuito

**Problema.** Cuando un proveedor externo se degrada, el modo de falla más dañino no es que responda con error, sino que responda lento. Las peticiones se acumulan, los hilos del servicio se agotan esperando, y un problema de un proveedor se convierte en la caída completa de Solventa.

**Aplicación.** Cada adaptador externo está envuelto en un interruptor con tres estados. En estado cerrado las peticiones fluyen normalmente. Cuando la proporción de fallos o de respuestas por encima del umbral de tiempo supera el 50% en una ventana móvil, el interruptor abre y las peticiones siguientes fallan de inmediato sin tocar la red, activando la ruta de degradación. Tras un intervalo, el interruptor pasa a semiabierto y deja pasar un número reducido de peticiones de prueba.

**Razonamiento frente al ASR.** El ASR-1.2 describe exactamente este escenario: 5.000 peticiones concurrentes con el proveedor respondiendo por encima de 700 ms, y exige 0% de peticiones perdidas. Sin interruptor, las peticiones se pierden por agotamiento de recursos. Con interruptor, la petición no se pierde: se atiende por la ruta degradada usando el perfil cacheado. La diferencia entre cumplir y no cumplir el ASR-1.2 no está en la velocidad del sistema sino en su capacidad de dejar de esperar a tiempo.

**Contrapartida aceptada.** Durante la apertura del interruptor, clientes cuyo perfil no está en caché reciben una cotización preliminar en lugar de una definitiva. Se prefiere una respuesta aproximada e inmediata sobre una respuesta exacta que no llega.

### 3.8 P3 — Tiempo de espera acotado con reintento y espera creciente

**Problema.** Un tiempo de espera mal calibrado anula el interruptor de circuito. Si el tiempo de espera del cliente supera el del usuario, el usuario abandona antes de que el sistema decida.

**Aplicación.** Cada llamada externa tiene un tiempo de espera explícito, derivado hacia atrás desde el presupuesto de latencia total: si el objetivo extremo a extremo es 200 ms, el adaptador de Open Finance no puede tener un tiempo de espera de 3 segundos. Los reintentos se aplican solo a operaciones idempotentes, con espera creciente y un componente aleatorio para no sincronizar a todos los clientes en la misma reintentada.

**Razonamiento frente al ASR.** Es el patrón que hace operativo el presupuesto de latencia del ASR-1.1. Un presupuesto de latencia que no se traduce en tiempos de espera configurados es una intención, no un mecanismo.

**Contrapartida aceptada.** Tiempos de espera agresivos aumentan la proporción de respuestas degradadas cuando la red está lenta pero funcional. Se acepta porque el ASR prioriza responder a tiempo sobre responder con el dato más fresco.

### 3.9 P4 — Mamparo de aislamiento

**Problema.** Servicios que comparten un mismo depósito de conexiones o de hilos se hunden juntos. Si Siniestros agota el depósito de conexiones a la base de datos, Cotización deja de responder aunque no tenga ningún problema propio.

**Aplicación.** Cada servicio tiene depósitos de recursos separados por dependencia: un depósito de conexiones para PostgreSQL, otro para Redis, otro por cada adaptador externo. En Kubernetes, cada servicio tiene límites propios de CPU y memoria.

**Razonamiento frente al ASR.** El ASR-3.1 exige disponibilidad de 99,9% con recuperación en menos de 30 segundos ante la caída de Redis. Sin aislamiento, la caída de Redis propaga la saturación a las conexiones de PostgreSQL y la recuperación deja de depender solo de Redis. Con aislamiento, el fallo queda confinado y la ruta de respaldo hacia PostgreSQL tiene recursos disponibles para operar.

**Contrapartida aceptada.** Se desperdicia capacidad: recursos reservados para una dependencia inactiva no se prestan a otra. Es el costo directo de que un fallo no se propague.

### 3.10 P5 — Puertos y adaptadores

**Problema.** El ASR-2.1 exige integrar una pasarela de pagos nueva en menos de 4 horas-hombre y sin modificar ningún servicio del núcleo. Si el servicio de Pagos conoce el formato de la pasarela, cada pasarela nueva obliga a modificarlo, probarlo y desplegarlo.

**Aplicación.** El núcleo define un puerto —una interfaz expresada en el lenguaje del dominio: autorizar cobro, confirmar cobro, reversar cobro— y no conoce ninguna implementación. Cada pasarela se integra escribiendo un adaptador que implementa ese puerto y traduce entre el modelo de la pasarela y el del dominio. La selección del adaptador ocurre por configuración según el país. Integrar una pasarela nueva es escribir una clase nueva y agregar una entrada de configuración: cero archivos modificados en el núcleo.

**Razonamiento frente al ASR.** La medida de respuesta del ASR-2.1 —«cero cambios en servicios del núcleo»— es una afirmación verificable sobre el diagrama de dependencias, no sobre la buena voluntad del equipo. La inversión de dependencias es lo que la vuelve estructuralmente cierta: el núcleo no puede depender de una pasarela porque la flecha de dependencia apunta al revés.

**Contrapartida aceptada.** Hay una capa de indirección adicional y un modelo de dominio que mantener en paralelo a los modelos de los proveedores. Para un sistema con un solo proveedor sería sobrecosto injustificado; con cinco categorías de proveedores externos y expansión a cuatro países, se paga solo.

### 3.11 P6 — Estrategia con configuración externalizada

**Problema.** El ASR-2.2 exige lanzar un ramo nuevo en dos semanas sin tocar la lógica central del motor de rating. Un motor con las reglas de cada ramo escritas en código requiere modificar, probar y desplegar el motor por cada ramo.

**Aplicación.** El motor de rating no conoce ramos: conoce cómo evaluar un árbol de reglas y cómo componer factores. Las reglas de cada ramo, sus factores, coberturas y parámetros viven en configuración versionada, no en el código. Añadir el seguro de mascota es cargar una definición nueva. Lo mismo aplica a la regionalización: los parámetros de México son una configuración, no una bifurcación del código.

**Razonamiento frente al ASR.** El objetivo de negocio de expandirse a tres países en 36 meses y el ASR-2.2 apuntan a la misma propiedad estructural: la variabilidad del negocio debe estar en los datos y no en el código. Si está en el código, cada variación cuesta un ciclo de despliegue y el plazo de dos semanas se consume en el proceso, no en el trabajo.

**Contrapartida aceptada.** Una configuración mal formada puede romper el motor en ejecución, un error que un compilador habría detectado. Se mitiga validando la definición contra un esquema al cargarla y ejecutando un juego de casos de referencia antes de activarla.

### 3.12 P7 — Backend por canal

**Problema.** Web y móvil tienen necesidades opuestas. Web puede recibir cargas útiles grandes en una sola petición; móvil necesita cargas pequeñas, tolerancia a red intermitente y un protocolo de sincronización. Un backend único termina sirviendo mal a ambos.

**Aplicación.** Dos backends: el BFF Web compone vistas ricas agregando varios servicios del núcleo en una respuesta; el BFF Móvil entrega cargas mínimas, gestiona el protocolo de sincronización con el almacenamiento local del dispositivo y resuelve conflictos.

**Razonamiento frente al ASR.** El ASR-3.3 exige que el 100% de las consultas de póliza funcionen sin conexión y que la sincronización tome 10 segundos o menos. Eso requiere lógica de sincronización con estado, versiones y resolución de conflictos, que no tiene ningún sentido en el canal web. Ponerla en un backend compartido obligaría al canal web a cargar con complejidad que no usa.

**Contrapartida aceptada.** Hay lógica de composición duplicada entre los dos BFF. Se acepta porque la alternativa —un backend que sirve a ambos— acopla la evolución de los dos canales: cada cambio para móvil obliga a re-probar web.

### 3.13 P8 — Publicación y suscripción de eventos de dominio

**Problema.** La emisión de una póliza dispara efectos en varios servicios: notificar al cliente, actualizar la administración de pólizas, registrar auditoría, alimentar tableros regulatorios. Si Emisión llama sincrónicamente a los cuatro, su latencia es la suma de las cuatro y su disponibilidad el producto de las cuatro.

**Aplicación.** Emisión publica un evento de dominio y termina. Los servicios interesados se suscriben y reaccionan a su ritmo. El bus retiene los eventos 7 días, lo que permite reprocesar cuando un consumidor estuvo caído o cuando se corrige un error de procesamiento.

**Razonamiento frente al ASR.** Sostiene el ASR-1.2 al sacar del camino crítico todo lo que no es necesario para responderle al usuario, y refuerza el ASR-2.1: agregar un consumidor nuevo —por ejemplo, un tablero regulatorio para un país nuevo— no requiere tocar el productor.

**Contrapartida aceptada.** Consistencia eventual. Durante un intervalo breve la póliza existe pero el tablero aún no la refleja. Es aceptable para efectos secundarios; no lo sería para el cobro de la prima, que por eso permanece sincrónico dentro de la transacción de emisión.

### 3.14 P9 — Tokenización de datos sensibles

**Problema.** El ASR-4.1 exige cero datos personales en texto plano en tránsito, y la regulación exige poder revocar un consentimiento con efecto en menos de 5 minutos. Si el dato personal está copiado en las bases de siete servicios, revocar significa borrarlo en siete lugares y demostrarlo.

**Aplicación.** Un único servicio custodia los datos sensibles. El resto del sistema opera sobre tokens que no tienen valor si se filtran. Un servicio que necesita el dato original debe solicitarlo presentando autorización, y cada solicitud queda registrada. Revocar un consentimiento es invalidar la capacidad de destokenizar, lo que surte efecto de inmediato en todo el sistema sin tocar siete bases de datos.

**Razonamiento frente al ASR.** Convierte la afirmación del ASR-4.1 en algo demostrable: para verificar que no hay información personal en texto plano basta con inspeccionar el tráfico y los volcados de las bases y comprobar que solo aparecen tokens. Con el dato replicado, la verificación tendría que ser exhaustiva sobre todo el sistema.

**Contrapartida aceptada.** El servicio de tokenización es un punto único de falla y un salto adicional de latencia en las operaciones que requieren el dato original. Se mitiga porque el camino crítico de cotización opera sobre el perfil derivado y no necesita destokenizar.

### 3.15 P10 — Almacenamiento inmutable con firma digital

**Problema.** El ASR-4.2 exige detectar en menos de 1 segundo cualquier alteración no autorizada de una póliza emitida, incluyendo alteraciones hechas con credenciales internas comprometidas. Un control basado en permisos no sirve: se asume que el atacante ya tiene los permisos.

**Aplicación.** Al emitirse, cada póliza se firma con una llave gestionada y se almacena en un contenedor con bloqueo de escritura que impide la modificación y el borrado durante el periodo de retención, incluso para cuentas administrativas. Cada lectura verifica la firma. Cada escritura genera un registro de auditoría inmutable con el servicio, el momento y la huella antes y después.

**Razonamiento frente al ASR.** El control no depende de que el atacante carezca de permisos, sino de que la plataforma de almacenamiento no acepte la operación. Esto cambia la naturaleza de la garantía: pasa de ser una política a ser una propiedad del sistema.

**Contrapartida aceptada.** El periodo de retención inmutable implica costo de almacenamiento que no se puede liberar anticipadamente, y errores legítimos no se corrigen borrando sino emitiendo un documento compensatorio. Es exactamente el comportamiento que la regulación espera de una aseguradora.

### 3.16 P11 — Cliente con prioridad al modo desconectado

**Problema.** El ASR-3.3 exige que el 100% de las consultas de póliza estén disponibles sin conexión. Un cliente que consulta al servidor y muestra un error cuando no hay red no puede cumplirlo, por rápido que sea el servidor.

**Aplicación.** La app trata el almacenamiento local cifrado como su fuente de lectura y la red como un mecanismo de actualización en segundo plano. Las pólizas se sincronizan al iniciar sesión y se conservan con vigencia de 24 horas. Las acciones ejecutadas sin conexión se encolan y se envían en orden al recuperar conectividad.

**Razonamiento frente al ASR.** La medida «100% de consultas disponibles sin conexión» solo es alcanzable si la ausencia de red es el caso normal y no la excepción. Esta es una decisión de diseño del cliente que no se puede añadir después: reordena de dónde lee la aplicación.

**Contrapartida aceptada.** Datos potencialmente desactualizados, resolución de conflictos y datos sensibles en el dispositivo. Se mitiga con vigencia de 24 horas, aviso visible al vencerse, precedencia del servidor ante conflicto y cifrado del almacenamiento local limitado a lo mínimo necesario para mostrar la póliza.

### 3.17 P12 — Autoescalado con comprobaciones de salud

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

### 5.1 Qué es un experimento de arquitectura y qué no lo es

Un experimento de arquitectura no es una prueba de software. Una prueba verifica que el sistema hace lo que se especificó. Un experimento **valida una hipótesis de diseño sobre la cual el equipo tiene incertidumbre**, construyendo una porción real del diseño para evaluar su viabilidad y medir si la decisión tomada permite cumplir el requisito de calidad objetivo.

De esa definición se desprenden cuatro consecuencias que gobiernan el diseño de esta sección:

1. **El experimento construye una porción del diseño, no un banco de pruebas desechable.** Los microservicios y conectores que se levantan son los mismos que quedan en el producto. Lo que se recorta es el alcance funcional, no la fidelidad arquitectural.
2. **El experimento debe medir de forma precisa.** Una conclusión del tipo «funcionó bien» no reduce incertidumbre. Cada experimento define de antemano la métrica, el instrumento que la captura y el umbral que separa el éxito del fracaso.
3. **Si el análisis no es favorable, se cambia la decisión de diseño y se experimenta de nuevo.** Por eso cada ficha declara cuál es la decisión alternativa que se adoptaría ante un resultado adverso. Un experimento sin plan B no es un experimento: es una demostración.
4. **Solo se experimenta donde hay incertidumbre.** Si el punto de sensibilidad no genera incertidumbre en el equipo, experimentarlo consume esfuerzo sin producir información.

### 5.2 Puntos de sensibilidad, incertidumbre y selección

Un **punto de sensibilidad** es una decisión de arquitectura de la que depende críticamente el cumplimiento de una historia de arquitectura. El equipo identificó los puntos de sensibilidad de las once historias de arquitectura y calificó la incertidumbre de cada uno con tres criterios: si el equipo ha implementado antes ese mecanismo, si el cumplimiento del umbral depende de valores que hoy no se conocen, y si un resultado adverso obligaría a rehacer estructura y no solo a ajustar parámetros.

| ASR | Punto de sensibilidad (decisión crítica) | Historia | Incertidumbre | Experimento |
|---|---|---|---|---|
| ASR-1.1 | Que el perfil derivado se pueda cachear con una tasa de acierto suficiente y que el procesamiento restante quepa en el presupuesto de 200 ms | SOL-28 | **Alta** | EXP-01 |
| ASR-1.2 | La calibración del umbral y la ventana del interruptor de circuito, y el reparto del presupuesto de latencia entre tiempos de espera | SOL-37 | **Alta** | EXP-02 |
| ASR-2.1 | Que la definición del puerto de pagos sea lo bastante general para absorber una pasarela con contrato distinto | SOL-20 | Media | EXP-03 |
| ASR-2.2 | Que el motor de rating sea genuinamente agnóstico al ramo | SOL-21 | Media | EXP-03 |
| ASR-3.1 | Que la ruta de respaldo hacia PostgreSQL absorba el tráfico del caché caído sin propagar la saturación | SOL-29 | **Alta** | EXP-04 |
| ASR-3.2 | Que el esquema multi-zona opere de hecho como activo-activo y no como activo-pasivo encubierto | SOL-43 | Media-alta | EXP-05 |
| ASR-3.3 | El protocolo de sincronización y la resolución de conflictos entre almacenamiento local y servidor | SOL-44 | Media | EXP-06 |
| ASR-4.1 | Que la tokenización centralizada no introduzca latencia inaceptable ni deje rutas por donde el dato original se filtre | SOL-23 | **Alta** | EXP-07 |
| ASR-4.2 | Que la ruta de auditoría detecte y registre una alteración en menos de 1 segundo | SOL-45 | Media | EXP-08 |

**Por qué ocho experimentos y no nueve.** ASR-2.1 y ASR-2.2 son dos manifestaciones del mismo punto de sensibilidad de fondo: si la variabilidad del negocio está encapsulada en puntos de extensión o filtrada hacia el núcleo. Se miden de la misma forma —tocar un punto de variación y contar qué archivos cambian— y usan la misma instrumentación. Se agrupan en el EXP-03 con dos escenarios, lo que evita duplicar montaje sin perder cobertura: los nueve ASR quedan cubiertos.

**Por qué se experimenta ASR-4.2 pese a apoyarse en una garantía de plataforma.** El bloqueo de escritura del almacenamiento de objetos es una capacidad documentada por el proveedor y sobre eso el equipo no tiene incertidumbre. La incertidumbre real está en otro lado: en si **la ruta de auditoría propia** detecta y registra el intento en menos de 1 segundo. Eso sí es una decisión de diseño del equipo y por eso el EXP-08 se enfoca en el tiempo de detección, no en si el bloqueo funciona.

**Sprint 1 de diseño.** Los cuatro experimentos de incertidumbre alta (EXP-01, EXP-02, EXP-04 y EXP-07) conforman el Sprint 1 y se ejecutan en las semanas 5 y 6, dentro de las 42 horas comprometidas. Los cuatro restantes quedan diseñados y programados, y se ejecutan según disponibilidad y en el Proyecto Final 2, por depender de infraestructura con costo o de incertidumbre menor.

---

### 5.3 EXP-01 — Viabilidad del presupuesto de latencia del motor de scoring

| Campo | Contenido |
|---|---|
| **Título** | Validación de latencia del motor de scoring en condiciones normales de operación |
| **Propósito del experimento** | Determinar si la decisión de resolver el scoring desde un perfil derivado cacheado hace viable el presupuesto de 200 ms, y medir el reparto real de ese presupuesto entre sus componentes |
| **Resultados esperados** | p95 < 200 ms y p99 < 400 ms bajo 500 solicitudes por minuto, con tasa de acierto de caché ≥ 80% y 0% de errores |
| **Recursos requeridos** | Servicios de Cotización & Rating y de Perfilamiento, Redis, PostgreSQL, adaptador Open Finance, WireMock para simular el proveedor y Apache JMeter para generar carga |
| **Elementos de arquitectura** | ASR-1.1. Vista funcional: Cotización & Rating, Perfilamiento, Adaptador Open Finance, Redis. Vista de despliegue: EKS, RDS PostgreSQL, ElastiCache |
| **Esfuerzo estimado** | 10 horas-hombre |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Tasa de acierto del caché de perfiles y reparto del presupuesto de latencia entre saltos |
| Historias de arquitectura asociadas | SOL-28 (HU-ARQ-07) · SOL-26 (HU-ARQ-05) |
| Nivel de incertidumbre | **Alta.** El equipo no sabe qué tasa de acierto produce una vigencia de 15 minutos en un flujo donde el usuario itera sobre planes, ni cuánto del presupuesto consume el procesamiento propio. Si el rating consume 150 ms, el diseño no cierra por más que el caché acierte |
| Patrones de arquitectura | **Cache-Aside** |
| Descripción de los patrones | El servicio consulta primero el caché y solo ante ausencia recurre a la fuente costosa, escribiendo el resultado con vigencia acotada |
| Tácticas de arquitectura | Mantener múltiples copias de los datos computados · Reducir la demanda computacional en el camino crítico · Acotar el tiempo de ejecución mediante presupuesto por salto |
| Descripción de las tácticas | Se evita la llamada externa en el camino crítico sirviendo el perfil derivado desde memoria, y se asigna a cada salto un tiempo máximo derivado hacia atrás del objetivo extremo a extremo |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Cotización & Rating | Recibe la solicitud, pide el perfil, aplica el motor de rating y compone la prima. Debe consumir menos de 40 ms en el cálculo | Python 3.11 · Flask · Gunicorn |
| Perfilamiento & Scoring | Resuelve el perfil consultando primero el caché. Tasa de acierto ≥ 80%, menos de 20 ms en el camino de acierto | Python 3.11 · Flask |
| Adaptador Open Finance | Traduce del modelo del proveedor al de dominio respetando un tiempo de espera de 150 ms | Python 3.11 · httpx |
| Caché de perfiles | Sirve el perfil derivado con vigencia de 15 minutos | Redis 7 |
| Base de datos | Provee tarifas y parámetros del ramo | PostgreSQL 15 |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Cotización → Perfilamiento | Que el salto de red añada menos de 5 ms al p95 | HTTP/1.1 con conexión persistente y depósito |
| Perfilamiento → Caché | Que la lectura se resuelva por debajo de 2 ms en p99 | Protocolo RESP · redis-py con depósito |
| Cotización → Base de datos | Que la consulta de tarifas no supere 10 ms | psycopg con depósito |
| Perfilamiento → Proveedor externo | Que el tiempo de espera de 150 ms se respete y no se desborde | HTTP sobre TLS hacia WireMock con retardo fijo |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Latencia extremo a extremo por percentil | Apache JMeter | p95 < 200 ms · p99 < 400 ms |
| Tasa de acierto del caché | Contadores del servicio de perfilamiento | ≥ 80% |
| Latencia atribuida a cada salto | Trazas distribuidas | Ver tabla de conectores |
| Tasa de error | Apache JMeter | 0% |

**Criterio de refutación.** La hipótesis queda refutada si el p95 supera 200 ms **teniendo la tasa de acierto en el objetivo**: eso significaría que el problema no está en la estrategia de caché sino en el procesamiento propio.

**Decisión alternativa ante resultado adverso.** Se revisa el momento del cálculo: se pasa de calcular la prima de forma sincrónica a precalcular las combinaciones más frecuentes de ramo y perfil, sirviendo el cálculo exacto solo para las poco frecuentes. Convierte el problema de latencia en uno de espacio, más barato de resolver.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | Las herramientas permiten generar carga controlada, simular la dependencia externa con retardo determinista y atribuir el tiempo consumido a un componente concreto, que es lo que el experimento necesita medir |
| Lenguaje | Python 3.11 |
| Framework | Flask · Gunicorn |
| Plataforma de despliegue | Docker Compose (experimento) · AWS EKS (destino) |
| Bases de datos | PostgreSQL 15 · Redis 7 |
| Librerías | redis-py · psycopg · httpx |
| Herramientas de análisis | Apache JMeter 5.6 · WireMock · trazas distribuidas · CloudWatch |

---

### 5.4 EXP-02 — Calibración de la degradación elegante

| Campo | Contenido |
|---|---|
| **Título** | Validación de degradación elegante ante lentitud del proveedor Open Finance |
| **Propósito del experimento** | Encontrar la calibración del interruptor de circuito que abre a tiempo para evitar el agotamiento de recursos sin abrir de forma espuria, y confirmar que la ruta degradada sostiene el objetivo de latencia |
| **Resultados esperados** | Interruptor abierto en menos de 10 s desde el inicio de la degradación, p95 < 200 ms sirviendo desde caché, 0% de solicitudes perdidas por timeout externo y 0 aperturas espurias en operación normal |
| **Recursos requeridos** | Montaje del EXP-01 más el interruptor de circuito instrumentado, WireMock con inyección de retardo creciente y Apache JMeter |
| **Elementos de arquitectura** | ASR-1.2. Vista funcional: Perfilamiento, Adaptador Open Finance, Redis, Event Bus |
| **Esfuerzo estimado** | 12 horas-hombre |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Umbral y ventana del interruptor de circuito · reparto del presupuesto de latencia entre tiempos de espera |
| Historias de arquitectura asociadas | SOL-37 (HU-ARQ-08) · SOL-28 (HU-ARQ-07) · SOL-26 (HU-ARQ-05) |
| Nivel de incertidumbre | **Alta.** El interruptor es un mecanismo conocido, pero sus parámetros no se derivan analíticamente. Un umbral alto deja que el sistema se sature antes de abrir; uno bajo abre ante fluctuaciones normales y degrada sin necesidad. El equipo no tiene datos previos para elegirlos |
| Patrones de arquitectura | **Circuit Breaker** · **Fallback** |
| Descripción de los patrones | El interruptor corta las llamadas a una dependencia degradada tras superar un umbral de fallos, y el fallback continúa la operación con la fuente alternativa en lugar de propagar el error |
| Tácticas de arquitectura | Detección de fallas mediante monitoreo de la tasa de respuesta · Degradación elegante ante indisponibilidad · Acotar el tiempo de espera para liberar recursos |
| Descripción de las tácticas | Se limita el tiempo que el sistema espera a un tercero y se decide dejar de esperar antes de que el depósito de conexiones se agote |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Perfilamiento & Scoring | Aloja el interruptor y decide entre ruta normal y degradada. Debe conmutar en menos de 10 s | Python 3.11 · pybreaker |
| Adaptador Open Finance | Recurso protegido por el interruptor. Debe fallar rápido sin consumir conexiones cuando está abierto | Python 3.11 · httpx |
| Cotización & Rating | Consume el perfil sin saber por qué ruta vino. Mantiene p95 < 200 ms durante la degradación | Python 3.11 · Flask |
| Caché de perfiles | Sostiene el volumen completo de tráfico redirigido | Redis 7 |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Perfilamiento → Proveedor externo | Que ante latencia superior a 700 ms el interruptor abra antes de agotar el depósito | httpx con pybreaker y tiempo de espera de 150 ms |
| Perfilamiento → Caché | Que la ruta degradada absorba el 100% del tráfico redirigido | redis-py con depósito dimensionado para el pico |
| Instrumentación del interruptor | Que las transiciones de estado se registren con marca de tiempo precisa | Métricas expuestas por el servicio |
| Servicios → Event Bus | Que la publicación de eventos no bloquee la respuesta al usuario | Kafka 3.x (KRaft) · kafka-python |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Tiempo hasta la apertura del interruptor | Métrica de estado del interruptor | < 10 s |
| Latencia durante la degradación | Apache JMeter | p95 < 200 ms |
| Solicitudes perdidas por agotamiento de recursos | JMeter · métricas del depósito | 0% |
| Aperturas espurias bajo carga nominal | Métrica de estado del interruptor | 0 en 10 minutos |

**Criterio de refutación.** Queda refutada si ninguna configuración de la rejilla ensayada logra abrir a tiempo sin producir aperturas espurias: eso indicaría que el problema no es de calibración sino de dimensionamiento de los depósitos de recursos.

**Decisión alternativa ante resultado adverso.** Se adopta el mamparo de aislamiento como mecanismo primario en lugar de complementario: se asigna al adaptador Open Finance un depósito de conexiones propio y estrecho, de modo que su saturación sea imposible de propagar aunque el interruptor no abra a tiempo.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | Se requiere inyectar retardo de forma progresiva y observar el estado interno del interruptor, lo que exige instrumentarlo y no solo medir desde fuera |
| Lenguaje | Python 3.11 |
| Framework | Flask · Gunicorn |
| Plataforma de despliegue | Docker Compose · AWS EKS |
| Bases de datos | Redis 7 · PostgreSQL 15 |
| Librerías | pybreaker · httpx · redis-py · kafka-python |
| Herramientas de análisis | Apache JMeter 5.6 · WireMock con retardo variable · Toxiproxy |

---

### 5.5 EXP-03 — Modificabilidad de los puntos de extensión

| Campo | Contenido |
|---|---|
| **Título** | Validación de la modificabilidad mediante Adapter y configuración externalizada |
| **Propósito del experimento** | Medir empíricamente el costo de las dos variaciones que el negocio pedirá con más frecuencia —una pasarela de pagos nueva y un ramo de seguro nuevo— y verificar que ninguna obliga a modificar el núcleo |
| **Resultados esperados** | Escenario A: una pasarela con contrato distinto integrada en menos de 4 horas-hombre y cero archivos del núcleo modificados. Escenario B: un ramo no contemplado disponible en el flujo de cotización y en la API de socios mediante configuración, con cero archivos del motor de rating modificados |
| **Recursos requeridos** | Servicio de Pagos & Recaudo, puerto de pagos, simulador de pasarela, servicio de Cotización & Rating, configuración de ramos, PostgreSQL y repositorio con registro de cambios por archivo |
| **Elementos de arquitectura** | ASR-2.1 y ASR-2.2. Vista funcional: Pagos & Recaudo, Adaptadores externos, Cotización & Rating y módulo de configuración de ramos |
| **Esfuerzo estimado** | 10 horas-hombre (6 h escenario A · 4 h escenario B) |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Generalidad de la definición del puerto de pagos · grado de agnosticismo del motor de rating respecto del ramo |
| Historias de arquitectura asociadas | SOL-20 (HU-ARQ-02) · SOL-21 (HU-ARQ-01) |
| Nivel de incertidumbre | **Media.** Ambos mecanismos están diseñados y el equipo los conoce; lo que no se sabe es si la abstracción es lo bastante general. Un resultado adverso obliga a redefinir una interfaz, no a rehacer la estructura, por lo que su incertidumbre es menor que la de los experimentos de rendimiento |
| Patrones de arquitectura | **Ports & Adapters** · **Strategy con configuración externalizada** |
| Descripción de los patrones | El núcleo define un puerto en lenguaje de dominio y desconoce toda implementación concreta; las reglas variables de cada ramo viven en configuración versionada y no en código |
| Tácticas de arquitectura | Encapsular la variabilidad · Restringir las dependencias mediante inversión · Diferir el enlace hasta el tiempo de despliegue |
| Descripción de las tácticas | La flecha de dependencia apunta del adaptador hacia el núcleo, de modo que agregar un proveedor no puede obligar a modificar el núcleo; y la selección concreta se resuelve por configuración |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Pagos & Recaudo | Ejecuta la lógica de cobro contra el puerto, sin conocer ninguna pasarela concreta | Python 3.11 · Flask |
| Adaptador de pasarela nuevo | Traduce entre el contrato de la pasarela y el puerto de dominio. Es el único artefacto que se escribe | Python 3.11 · httpx |
| Cotización & Rating | Evalúa el árbol de reglas del ramo sin conocer ramos concretos | Python 3.11 · Flask |
| Módulo de configuración de ramos | Carga y valida la definición del ramo contra un esquema antes de activarla | Python 3.11 · JSON Schema |
| Portal de socios | Expone el ramo nuevo por la API B2B sin cambios de código | Angular 17 |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Pagos → Puerto de dominio | Que la interfaz absorba un contrato distinto sin fugas de abstracción | Interfaz Python (inversión de dependencias) |
| Adaptador → Pasarela simulada | Que la traducción quede confinada al adaptador | REST sobre TLS · httpx |
| Cotización → Configuración de ramos | Que el ramo nuevo se cargue y valide sin reiniciar el motor | psycopg · PostgreSQL 15 |
| Portal → API de socios | Que el catálogo refleje el ramo nuevo automáticamente | REST sobre TLS |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Esfuerzo de integración de la pasarela | Cronometraje del trabajo | < 4 horas-hombre |
| Archivos del núcleo modificados | `git diff --name-only` contra la base | 0 fuera de adaptadores y configuración |
| Archivos del motor de rating modificados | `git diff --name-only` | 0 |
| Pruebas del núcleo tras el cambio | pytest | Pasan sin modificación |

**Criterio de refutación.** Cualquier archivo del núcleo que deba modificarse refuta la hipótesis e identifica exactamente dónde está la fuga de abstracción. La medida no es una opinión: es el conjunto de archivos que reporta el control de versiones.

**Decisión alternativa ante resultado adverso.** Si el puerto de pagos resulta insuficiente, se redefine en términos de intención de negocio —autorizar, confirmar, reversar— en lugar de operaciones de pasarela. Si el motor de rating exige cambios, se extrae el fragmento dependiente del ramo hacia una estrategia cargada por configuración.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | La medición se apoya en el control de versiones, que da evidencia objetiva de qué se tocó, y en el cronometraje del trabajo de un integrante que no diseñó el módulo, para evitar el sesgo del autor |
| Lenguaje | Python 3.11 |
| Framework | Flask · Angular 17 (portal) |
| Plataforma de despliegue | Docker Compose · AWS EKS |
| Base de datos | PostgreSQL 15 |
| Librerías | httpx · psycopg · jsonschema |
| Herramientas de análisis | Git con registro de cambios por archivo · pytest 8 · Postman/Newman · simulador de pasarela |

---

### 5.6 EXP-04 — Absorción del tráfico ante la caída del caché

| Campo | Contenido |
|---|---|
| **Título** | Validación de tolerancia a fallos ante caída de Redis |
| **Propósito del experimento** | Verificar que la pérdida del caché degrada el rendimiento sin interrumpir el servicio, y que el aislamiento por mamparo confina el efecto a los servicios que dependen del caché |
| **Resultados esperados** | Conmutación a PostgreSQL en menos de 30 s, cero transacciones activas perdidas, disponibilidad ≥ 99,9% en la ventana medida y un servicio testigo sin afectación |
| **Recursos requeridos** | Redis, PostgreSQL, Perfilamiento, Cotización, Pólizas como servicio testigo, `docker stop` o Toxiproxy para inducir la falla, JMeter y CloudWatch |
| **Elementos de arquitectura** | ASR-3.1. Vista funcional: Perfilamiento, Cotización, Pólizas, Redis, PostgreSQL |
| **Esfuerzo estimado** | 8 horas-hombre |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Que el depósito de conexiones a PostgreSQL absorba el tráfico que atendía el caché · que la saturación no se propague por el recurso compartido |
| Historias de arquitectura asociadas | SOL-29 (HU-ARQ-06) · SOL-26 (HU-ARQ-05) |
| Nivel de incertidumbre | **Alta.** Cuando Redis cae, el 100% del tráfico que resolvía por caché pasa a PostgreSQL de golpe. No se sabe si el depósito dimensionado para operación normal soporta ese salto, ni si la saturación queda confinada al perfilamiento o alcanza a los servicios que comparten la base |
| Patrones de arquitectura | **Circuit Breaker** · **Fallback** · **Bulkhead** |
| Descripción de los patrones | El interruptor detecta la ausencia del caché, el fallback redirige a la fuente persistente y el mamparo impide que la saturación resultante alcance a otros servicios |
| Tácticas de arquitectura | Detección de fallas mediante comprobación de vitalidad · Recuperación mediante fuente alternativa · Contención del fallo limitando recursos compartidos |
| Descripción de las tácticas | Cada dependencia tiene su propio depósito de conexiones, de modo que agotar uno no agota los demás |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Perfilamiento & Scoring | Detecta la ausencia del caché y conmuta a la fuente primaria en menos de 30 s sin perder transacciones en curso | Python 3.11 · redis-py con comprobación de salud |
| Pólizas | Sirve de testigo de propagación: debe mantener latencia y tasa de error sin alteración durante todo el incidente | Python 3.11 · Flask |
| Cotización & Rating | Sostiene el flujo de usuario con degradación acotada y transitoria, sin errores | Python 3.11 · Flask |
| Base de datos | Absorbe el tráfico redirigido desde un depósito dedicado | PostgreSQL 15 |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Perfilamiento → Caché | Que la pérdida de conexión se detecte rápido y no quede esperando | redis-py con tiempo de espera de conexión corto |
| Perfilamiento → Base de datos | Que el depósito absorba el tráfico redirigido sin agotarse | psycopg con depósito dedicado |
| Pólizas → Base de datos | Que su depósito, separado del anterior, permanezca intacto | psycopg con depósito independiente |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Tiempo de conmutación a la fuente primaria | Trazas y registros del servicio | < 30 s |
| Transacciones activas perdidas | Conciliación de enviadas contra confirmadas | 0 |
| Disponibilidad en la ventana medida | Apache JMeter | ≥ 99,9% |
| Latencia y errores del servicio testigo | Apache JMeter | Sin alteración significativa |

**Criterio de refutación.** Queda refutada si el servicio de Pólizas se degrada: eso demostraría que el aislamiento por mamparo no está operando y que el fallo se propaga por el recurso compartido.

**Decisión alternativa ante resultado adverso.** Se separa físicamente el acceso a datos: el perfilamiento deja de compartir instancia de base de datos con el resto, convirtiendo el aislamiento lógico en aislamiento de infraestructura.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | Se requiere inducir una falla real de infraestructura y observar simultáneamente el servicio afectado y uno no relacionado, que es la única forma de comprobar la contención |
| Lenguaje | Python 3.11 |
| Framework | Flask · Gunicorn |
| Plataforma de despliegue | Docker Compose · AWS EKS |
| Bases de datos | PostgreSQL 15 · Redis 7 |
| Librerías | redis-py · psycopg · pybreaker |
| Herramientas de análisis | Apache JMeter 5.6 · `docker stop` · Toxiproxy · CloudWatch |

---

### 5.7 EXP-05 — Pérdida de una zona de disponibilidad

| Campo | Contenido |
|---|---|
| **Título** | Validación de alta disponibilidad ante caída de una zona AWS |
| **Propósito del experimento** | Verificar que el esquema multi-zona opera realmente como activo-activo y que los objetivos de tiempo y punto de recuperación se cumplen ante la pérdida completa de una zona |
| **Resultados esperados** | Tráfico redirigido a la zona superviviente, promoción automática de la réplica de base de datos, continuidad del bus de eventos, RTO ≤ 10 minutos, RPO ≤ 30 s y cero transacciones confirmadas perdidas |
| **Recursos requeridos** | AWS con EKS multi-AZ, RDS PostgreSQL con réplica, Amazon MSK, balanceador de aplicación, AWS Fault Injection Service y CloudWatch |
| **Elementos de arquitectura** | ASR-3.2. Vista de despliegue: EKS en dos zonas, RDS multi-AZ, MSK, balanceador |
| **Esfuerzo estimado** | 12 horas-hombre |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Que la configuración sea activo-activo de hecho y no activo-pasivo encubierto · tiempo de promoción de la réplica · continuidad del bus de eventos |
| Historias de arquitectura asociadas | SOL-43 (HU-ARQ-09) · SOL-29 (HU-ARQ-06) |
| Nivel de incertidumbre | **Media-alta.** El diseño afirma que la capacidad de la zona superviviente ya está caliente, pero eso solo se comprueba induciendo la falla. Si en la práctica opera como activo-pasivo, el RTO dependerá del arranque en frío y el objetivo de 10 minutos queda en riesgo |
| Patrones de arquitectura | **Active-Active** · **Replication** · **Automatic Failover** |
| Descripción de los patrones | Ambas zonas reciben tráfico simultáneamente y los datos se replican de forma síncrona, de modo que la recuperación dependa de la detección y no del aprovisionamiento |
| Tácticas de arquitectura | Redundancia activa · Replicación síncrona de estado · Detección de fallas mediante comprobación de salud del balanceador |
| Descripción de las tácticas | Mantener capacidad ya caliente en ambas zonas es lo que hace que el tiempo de recuperación se mida en decenas de segundos y no en minutos de arranque |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Servicios de negocio | Se ejecutan en pods repartidos entre zonas con reglas de antiafinidad; ninguna zona concentra todas las réplicas | Python 3.11 · Flask sobre Kubernetes |
| Orquestador | Retira de rotación los pods que no responden y escala la zona superviviente | Amazon EKS · Horizontal Pod Autoscaler |
| Base de datos | Promueve automáticamente la réplica a primaria conservando el RPO | Amazon RDS PostgreSQL multi-AZ |
| Bus de eventos | Continúa operando con los brokers de la zona superviviente | Amazon MSK |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Internet → Balanceador | Que la detección de la zona caída y la redirección ocurran en segundos | AWS Application Load Balancer |
| Servicios → Base de datos | Que la reconexión tras la promoción sea automática y no requiera reinicio | psycopg con reintento y descubrimiento de punto final |
| Servicios → Bus de eventos | Que no se pierdan eventos confirmados durante la conmutación | kafka-python contra MSK multi-AZ |
| Zona A ↔ Zona B | Que la replicación sostenga un RPO de 30 s | Replicación síncrona de RDS |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Tiempo de recuperación del servicio | CloudWatch · JMeter | RTO ≤ 10 min |
| Pérdida de datos | Conciliación de transacciones confirmadas antes y después | RPO ≤ 30 s |
| Transacciones confirmadas perdidas | Consulta de verificación sobre la base | 0 |
| Capacidad absorbida por la zona superviviente | Métricas del autoescalador | Sin rechazo de solicitudes |

**Criterio de refutación.** Un RTO superior a 10 minutos indicaría que el esquema opera de hecho como activo-pasivo. La pérdida de transacciones confirmadas indicaría que la replicación no es síncrona.

**Decisión alternativa ante resultado adverso.** Se pasa de replicación asíncrona a síncrona aceptando el costo en latencia de escritura, y se reserva capacidad mínima garantizada por zona en lugar de depender del autoescalado para absorber el tráfico redirigido.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | Solo un servicio de inyección de fallas permite provocar la pérdida de una zona de forma controlada y repetible; simularlo apagando instancias no reproduce el comportamiento del balanceador |
| Lenguaje | Python 3.11 |
| Framework | Flask |
| Plataforma de despliegue | AWS EKS multi-AZ |
| Bases de datos | Amazon RDS PostgreSQL multi-AZ |
| Librerías | psycopg · kafka-python |
| Herramientas de análisis | AWS Fault Injection Service · CloudWatch · Apache JMeter 5.6 |

---

### 5.8 EXP-06 — Continuidad del cliente móvil sin conexión

| Campo | Contenido |
|---|---|
| **Título** | Validación de operación offline y sincronización de pólizas en la aplicación móvil |
| **Propósito del experimento** | Verificar que la billetera de pólizas es plenamente funcional sin red, que la sincronización posterior cumple el objetivo de tiempo y que el almacenamiento local no expone información en claro |
| **Resultados esperados** | 100% de las consultas de póliza resueltas sin conexión, sincronización completa en ≤ 10 s al recuperar conectividad sin intervención del usuario, aviso de datos desactualizados al superar 24 horas y almacenamiento local ilegible fuera de la aplicación |
| **Recursos requeridos** | Emulador o dispositivo Android, aplicación móvil, BFF Móvil, API de pólizas y control de conectividad del emulador |
| **Elementos de arquitectura** | ASR-3.3. Vista funcional: aplicación móvil, almacenamiento local cifrado, BFF Móvil y módulo de sincronización |
| **Esfuerzo estimado** | 10 horas-hombre |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Protocolo de sincronización y resolución de conflictos entre el almacenamiento local y el servidor · cifrado del almacenamiento local |
| Historias de arquitectura asociadas | SOL-44 (HU-ARQ-10) |
| Nivel de incertidumbre | **Media.** El patrón offline-first está definido, pero no se conoce el costo real de la sincronización con el volumen de pólizas de un usuario típico ni cómo se comporta la resolución de conflictos cuando el dato cambió en ambos lados |
| Patrones de arquitectura | **Offline-First** · **Deferred Synchronization** |
| Descripción de los patrones | La aplicación trata el almacenamiento local como fuente de lectura y la red como mecanismo de actualización en segundo plano; las acciones ejecutadas sin conexión se encolan y se envían en orden al recuperar la red |
| Tácticas de arquitectura | Mantener una copia local del estado · Sincronización diferida con reintento · Acotar la vigencia del dato replicado |
| Descripción de las tácticas | La vigencia de 24 horas acota cuánto puede desviarse el dato local, y el aviso al vencer traslada al usuario la decisión de confiar o no en lo que ve |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Aplicación móvil | Sirve las pólizas desde el almacenamiento local sin requerir red | Kotlin nativo · Android |
| Almacenamiento local cifrado | Conserva las pólizas cifradas y solo la información mínima necesaria para mostrarlas | Room con SQLCipher · EncryptedSharedPreferences |
| Módulo de sincronización | Detecta la reconexión y sincroniza en 10 s o menos sin intervención | Kotlin · WorkManager |
| BFF Móvil | Expone las pólizas en cargas compactas y resuelve conflictos con precedencia del servidor | Python 3.11 · Flask |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Aplicación → Almacenamiento local | Que la consulta se resuelva sin red y el contenido esté cifrado en reposo | Room · SQLCipher |
| Aplicación → BFF Móvil | Que la carga útil sea compacta y tolere red intermitente | REST sobre TLS 1.3 · Retrofit · OkHttp |
| Módulo de sincronización ↔ BFF | Que las acciones diferidas se envíen en el orden en que se ejecutaron | WorkManager con reintento y espera creciente |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Consultas resueltas sin conexión | Suite de pruebas instrumentadas | 100% |
| Tiempo de sincronización tras reconectar | Cronometraje instrumentado | ≤ 10 s |
| Legibilidad del almacenamiento local | Inspección del dispositivo con depuración | Ilegible fuera de la aplicación |
| Aviso de datos desactualizados | Prueba con reloj adelantado 24 h | Aviso visible, consulta no bloqueada |

**Criterio de refutación.** Cualquier consulta de póliza que requiera red refuta la hipótesis. Una sincronización por encima de 10 s obliga a revisar el protocolo del BFF Móvil.

**Decisión alternativa ante resultado adverso.** Se pasa de sincronización por instantánea completa a sincronización incremental por diferencias, enviando solo lo que cambió desde la última marca de sincronización.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | El experimento exige controlar la conectividad de forma determinista e inspeccionar el almacenamiento del dispositivo, lo que solo es viable en emulador con depuración habilitada |
| Lenguajes | Kotlin (cliente) · Python 3.11 (BFF) |
| Frameworks | Android SDK · Flask |
| Plataforma de despliegue | Emulador Android API 34 · AWS EKS (BFF) |
| Almacenamiento | Room con SQLCipher · EncryptedSharedPreferences |
| Librerías | Retrofit · OkHttp · WorkManager · Kotlin Coroutines |
| Herramientas de análisis | Espresso · JUnit 5 · MockK · control de conectividad del emulador · Android Debug Bridge |

> **Corrección respecto de versiones anteriores de esta propuesta.** Versiones previas mencionaban `AsyncStorage` como almacenamiento local. `AsyncStorage` pertenece a React Native, stack que el equipo descartó el 19 de agosto al adoptar Kotlin nativo. El mecanismo correcto es Room con cifrado, complementado con `EncryptedSharedPreferences` para credenciales.

---

### 5.9 EXP-07 — Costo y hermeticidad de la tokenización de datos sensibles

| Campo | Contenido |
|---|---|
| **Título** | Validación de confidencialidad y protección de información financiera Open Finance |
| **Propósito del experimento** | Medir el costo en latencia de la tokenización centralizada y verificar empíricamente que no existe ninguna ruta por la cual el dato original escape del servicio custodio |
| **Resultados esperados** | 100% de las transmisiones sobre TLS 1.3, 100% de los campos personales tokenizados antes de salir de Perfilamiento, cero datos personales en texto plano en tránsito ni en reposo, y latencia añadida por la tokenización inferior a 15 ms |
| **Recursos requeridos** | Servicio de Tokenización, Perfilamiento, Consentimientos, adaptador Open Finance, AWS KMS, certificados TLS, OWASP ZAP, captura de tráfico y datos cebo |
| **Elementos de arquitectura** | ASR-4.1. Vista funcional: Tokenización, Perfilamiento, Consentimientos & Auditoría, Adaptador Open Finance. Vista de información: clasificación de datos restringidos |
| **Esfuerzo estimado** | 12 horas-hombre |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Centralizar la custodia del dato sensible en un único servicio en lugar de cifrar por campo en cada servicio |
| Historias de arquitectura asociadas | SOL-23 (HU-ARQ-03) · SOL-22 (HU-ARQ-04) |
| Nivel de incertidumbre | **Alta.** La decisión tiene dos riesgos que no se resuelven en el papel. De rendimiento: el servicio custodio es un salto adicional y un punto único, y no se sabe cuánto añade al camino crítico. De hermeticidad: el diseño afirma que el dato original no sale del custodio, pero esa afirmación solo se sostiene inspeccionando lo que realmente circula y se persiste |
| Patrones de arquitectura | **Tokenization** · **Defense in Depth** |
| Descripción de los patrones | El dato sensible se sustituye por un token sin valor fuera del sistema y su original queda bajo custodia única; y la protección se aplica en capas, cifrando también el transporte y el reposo |
| Tácticas de arquitectura | Limitar el acceso mediante custodia centralizada · Cifrar los datos en tránsito y en reposo · Registrar la auditoría de cada acceso al dato original |
| Descripción de las tácticas | Revocar un consentimiento se convierte en invalidar la capacidad de destokenizar, lo que surte efecto de inmediato en todo el sistema sin tocar siete bases de datos |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Tokenización | Custodia el dato original y entrega tokens sin valor fuera del sistema. Tokeniza en menos de 15 ms y registra cada destokenización | Python 3.11 · Flask · cifrado con llave gestionada |
| Gestión de llaves | Custodia y rota las llaves de cifrado; ningún servicio accede al material de la llave | AWS KMS |
| Perfilamiento & Scoring | Opera solo sobre el perfil derivado; no solicita destokenización en el camino crítico | Python 3.11 · Flask |
| Consentimientos & Auditoría | Registra el consentimiento y su revocación, con efecto en menos de 5 minutos | Python 3.11 · Flask · PostgreSQL 15 |
| Adaptador Open Finance | Negocia TLS 1.3 con el proveedor y entrega los datos ya tokenizados aguas adentro | Python 3.11 · httpx |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Servicio a servicio | Que el 100% de las conexiones negocie TLS 1.3 y ninguna caiga a una versión anterior | TLS 1.3 entre contenedores |
| Perfilamiento → Tokenización | Que el salto añada menos de 15 ms y no esté en el camino crítico de cotización | HTTP sobre TLS · httpx con depósito |
| Tokenización → Gestión de llaves | Que el material de la llave nunca salga del servicio de llaves | AWS KMS · boto3 |
| Servicios → Bus de eventos | Que ningún evento publicado contenga datos personales en texto plano | Kafka 3.x · consumidor de inspección |
| Servicios → Base de datos | Que ninguna tabla persista datos personales en texto plano | psycopg · inspección de volcados |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Coincidencias de datos cebo fuera del custodio | Búsqueda sobre volcados, tráfico capturado y mensajes del bus | 0 |
| Versión de TLS negociada | OWASP ZAP · captura de tráfico | TLS 1.3 en el 100% |
| Latencia añadida por la tokenización | Trazas distribuidas | < 15 ms |
| Entradas de auditoría por destokenización | Consulta al registro de auditoría | Una por acceso, sin excepción |
| Efecto de la revocación de consentimiento | Prueba de extremo a extremo cronometrada | < 5 minutos |

**Criterio de refutación.** Una sola coincidencia de dato cebo en un volcado, en un mensaje del bus o en el tráfico refuta la hipótesis e identifica el punto exacto de fuga, que es precisamente el valor del experimento.

**Decisión alternativa ante resultado adverso.** Si aparece una fuga por el bus de eventos, se adopta la publicación de eventos con referencia en lugar de con contenido: el evento transporta un identificador y el consumidor recupera lo que necesite sujeto a su propia autorización. Si la latencia añadida resulta inaceptable, se introduce un caché de tokens de corta vigencia en el consumidor, aceptando el aumento de superficie de exposición.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | La hermeticidad no se demuestra leyendo código: exige sembrar datos reconocibles y buscarlos en todo lo que el sistema transmite y persiste. De ahí el uso de datos cebo y de inspección directa de volcados y temas |
| Lenguaje | Python 3.11 |
| Framework | Flask |
| Plataforma de despliegue | Docker Compose · AWS EKS |
| Bases de datos | PostgreSQL 15 · Redis 7 |
| Librerías | cryptography · boto3 · httpx · psycopg · kafka-python |
| Herramientas de análisis | OWASP ZAP · captura de tráfico · consumidor de inspección de Kafka · consultas de verificación sobre PostgreSQL · datos cebo |

> **Precisión respecto de versiones anteriores.** AWS KMS **no** es un servicio de tokenización: gestiona el ciclo de vida de las llaves. La tokenización la implementa un servicio propio de Solventa que usa KMS para custodiar la llave con la que cifra el dato original. Confundirlos dejaría el ASR-4.1 sin componente responsable.

---

### 5.10 EXP-08 — Tiempo de detección de una alteración de póliza

| Campo | Contenido |
|---|---|
| **Título** | Validación de integridad y auditoría de pólizas emitidas |
| **Propósito del experimento** | Verificar que un intento de alterar una póliza emitida con credenciales válidas es rechazado por la plataforma y, sobre todo, que **la ruta de auditoría propia lo detecta y registra en menos de 1 segundo** |
| **Resultados esperados** | Escritura y borrado directos rechazados por el bloqueo de escritura, entrada en el registro de auditoría en menos de 1 s, verificación de firma detectando cualquier alteración y registro de auditoría inalterable |
| **Recursos requeridos** | Servicio de Emisión & Pólizas, almacenamiento de objetos con bloqueo de escritura, AWS KMS, registro de auditoría, credenciales administrativas de prueba y CloudWatch |
| **Elementos de arquitectura** | ASR-4.2. Vista funcional: Emisión & Pólizas, Object Storage, Consentimientos & Auditoría. Vista de información: datos confidenciales firmados |
| **Esfuerzo estimado** | 8 horas-hombre |

**Hipótesis de diseño**

| Campo | Contenido |
|---|---|
| Puntos de sensibilidad | Tiempo de detección de la ruta de auditoría · verificación de firma en cada lectura |
| Historias de arquitectura asociadas | SOL-45 (HU-ARQ-11) · SOL-23 (HU-ARQ-03) |
| Nivel de incertidumbre | **Media.** El bloqueo de escritura es una garantía documentada de la plataforma y sobre eso no hay incertidumbre. La incertidumbre está en la ruta de auditoría propia: si el registro se escribe de forma asíncrona, el umbral de 1 segundo puede no cumplirse, y eso sí es una decisión de diseño del equipo |
| Patrones de arquitectura | **Immutable Storage (WORM)** · **Audit Trail** · **Digital Signature** |
| Descripción de los patrones | El almacenamiento rechaza toda modificación durante el periodo de retención incluso para cuentas administrativas; cada operación deja un registro inmutable; y la firma permite detectar alteración en cualquier lectura posterior |
| Tácticas de arquitectura | Detección de intrusión mediante verificación de integridad · Registro no repudiable de las operaciones · Autorización mediante token de servicio |
| Descripción de las tácticas | El control no depende de que el atacante carezca de permisos, sino de que la plataforma no acepte la operación: pasa de ser una política a ser una propiedad del sistema |

**Componentes involucrados**

| Componente | Propósito y comportamiento esperado | Tecnología |
|---|---|---|
| Emisión & Pólizas | Firma la póliza al emitirla y verifica la firma en cada lectura, bloqueando la operación ante firma inválida | Python 3.11 · Flask |
| Almacenamiento de objetos | Rechaza modificación y borrado durante el periodo de retención, incluso con credenciales administrativas | Amazon S3 con Object Lock en modo cumplimiento |
| Gestión de llaves | Firma el resumen del documento y custodia la llave | AWS KMS |
| Consentimientos & Auditoría | Registra cada operación con servicio, momento, token y resumen antes y después, en menos de 1 s | Python 3.11 · Flask · S3 Object Lock |

**Conectores involucrados**

| Conector | Comportamiento a probar | Tecnología |
|---|---|---|
| Emisión → Almacenamiento | Que la escritura autorizada funcione y la directa sea rechazada | AWS SDK (boto3) |
| Emisión → Gestión de llaves | Que la firma se genere y verifique sin exponer el material de la llave | AWS KMS · boto3 |
| Cliente administrativo → Almacenamiento | Que el intento de sobrescritura y borrado sea rechazado por la plataforma | AWS CLI con credenciales administrativas |
| Almacenamiento → Auditoría | Que el evento de intento llegue al registro en menos de 1 s | Notificaciones de evento de S3 · CloudTrail |

**Medición**

| Métrica | Instrumento | Umbral |
|---|---|---|
| Resultado del intento de sobrescritura y borrado | Cliente administrativo | Rechazado por la plataforma |
| Latencia entre el intento y la entrada de auditoría | Marcas de tiempo comparadas | < 1 s |
| Detección de alteración por verificación de firma | Prueba con documento modificado fuera de banda | 100% detectado |
| Inmutabilidad del propio registro de auditoría | Intento de alteración del registro | Rechazado |

**Criterio de refutación.** Si el registro de auditoría tarda más de 1 segundo, la ruta es demasiado lenta y debe pasar a un camino sincrónico. Si la sobrescritura tiene éxito, la configuración de retención está mal aplicada.

**Decisión alternativa ante resultado adverso.** Se traslada el registro de auditoría del camino asíncrono al sincrónico dentro de la transacción de escritura, aceptando el costo en latencia de emisión a cambio de garantizar el umbral de detección.

**Tecnología asociada**

| Elemento | Detalle |
|---|---|
| Justificación | El experimento requiere credenciales administrativas reales para comprobar que ni siquiera ellas pueden alterar el documento; simularlo con permisos restringidos no probaría nada |
| Lenguaje | Python 3.11 |
| Framework | Flask |
| Plataforma de despliegue | AWS EKS |
| Almacenamiento | Amazon S3 con Object Lock · PostgreSQL 15 |
| Librerías | boto3 · cryptography · psycopg |
| Herramientas de análisis | AWS CLI · CloudTrail · CloudWatch · verificación de resúmenes SHA-256 |

> **Precisión respecto de versiones anteriores.** El registro de auditoría **no** puede vivir solo en CloudWatch: CloudWatch es una plataforma de observabilidad, no un almacenamiento inmutable, y el ASR-4.2 exige que el registro sea inalterable durante 5 años por regulación. El almacén de auditoría es S3 con Object Lock; CloudWatch se usa para la observabilidad y la alerta.

---

### 5.11 Ficha consolidada de tecnología

Tecnología completa del programa de experimentación. La columna de familiaridad importa: donde el equipo no domina la herramienta, el esfuerzo estimado incluye el tiempo de aprendizaje.

| Categoría | Tecnología | Experimentos | Familiaridad |
|---|---|---|---|
| Lenguaje backend | Python 3.11 | Todos | Alta |
| Lenguaje móvil | Kotlin | EXP-06 | Media |
| Lenguaje web | TypeScript · Angular 17 | EXP-03 | Media |
| Framework backend | Flask · Gunicorn | Todos | Alta |
| Base de datos | PostgreSQL 15 | 01, 03, 04, 05, 07, 08 | Alta |
| Caché | Redis 7 | 01, 02, 04, 07 | Media |
| Bus de eventos | Kafka 3.x (KRaft) · Amazon MSK | 02, 05, 07 | Baja — se reserva tiempo de aprendizaje |
| Almacenamiento de objetos | Amazon S3 con Object Lock | 08 | Baja — se reserva tiempo de aprendizaje |
| Gestión de llaves | AWS KMS | 07, 08 | Baja — se reserva tiempo de aprendizaje |
| Cliente de base de datos | psycopg con depósito | 01, 03, 04, 05, 07 | Alta |
| Cliente de caché | redis-py con depósito | 01, 02, 04 | Media |
| Cliente HTTP | httpx con depósito y tiempo de espera | 01, 02, 03, 07 | Alta |
| Interruptor de circuito | pybreaker | 02, 04 | Baja — se reserva tiempo de aprendizaje |
| Cliente de eventos | kafka-python | 02, 05, 07 | Baja |
| SDK de nube | boto3 | 07, 08 | Media |
| Criptografía | cryptography | 07, 08 | Media |
| Validación de esquema | jsonschema | 03 | Alta |
| Cliente móvil | Retrofit · OkHttp · WorkManager · Room con SQLCipher | EXP-06 | Media |
| Orquestación local | Docker · Docker Compose | Todos | Alta |
| Orquestación de nube | Amazon EKS · Horizontal Pod Autoscaler | 05 | Media |
| Generación de carga | Apache JMeter 5.6 | 01, 02, 04, 05 | Media |
| Simulación de dependencias | WireMock | 01, 02 | Media |
| Inyección de fallas | Toxiproxy · `docker stop` · AWS Fault Injection Service | 02, 04, 05 | Baja — se reserva tiempo de aprendizaje |
| Trazas distribuidas | Instrumentación de trazas por salto | 01, 02, 07 | Baja — se reserva tiempo de aprendizaje |
| Seguridad | OWASP ZAP | 07 | Media |
| Pruebas backend | pytest 8 · pytest-cov | 03 y pruebas residuales | Alta |
| Pruebas móviles | Espresso · JUnit 5 · MockK | 06 | Media |
| Pruebas de API | Postman · Newman | 03 | Alta |
| Observabilidad | AWS CloudWatch · CloudTrail | 04, 05, 08 | Media |
| Control de versiones | Git con registro de cambios por archivo | 03 | Alta |

### 5.12 Distribución de actividades por integrante

Reparto equitativo de las 42 horas del Sprint 1 de diseño, que agrupa los cuatro experimentos de incertidumbre alta.

| Integrante | Actividades asignadas | Experimentos | Horas |
|---|---|---|---|
| **Miguel Gómez** | Construir el servicio de Perfilamiento con su caché; instrumentar las trazas por salto; calibrar el interruptor recorriendo la rejilla de configuraciones; ejecutar la verificación de TLS y la búsqueda de datos cebo | 01 · 02 · 07 | 11 h |
| **Angie Arandio** | Construir el servicio de Cotización y el motor de rating; construir la ruta de respaldo hacia PostgreSQL y los depósitos separados por dependencia; ejecutar la falla inducida del caché y conciliar transacciones | 01 · 04 | 11 h |
| **Juan Mejía** | Construir el adaptador Open Finance y el simulador con retardo controlado; construir el servicio de Tokenización e integrarlo al recorrido; configurar los conectores con sus depósitos y tiempos de espera | 01 · 02 · 07 | 10 h |
| **Jazmin Córdoba** | Preparar el entorno en contenedores; construir los planes de carga en JMeter; ejecutar las corridas y consolidar las mediciones; redactar el informe de resultados y la decisión que se toma con cada uno | 01 · 02 · 04 | 10 h |
| | | **Total** | **42 h** |

> El reparto asigna a cada integrante al menos dos experimentos y combina construcción con medición, de modo que nadie quede solo construyendo ni solo midiendo. La redacción del informe se asigna explícitamente porque un experimento cuyo resultado no se documenta no reduce la incertidumbre del equipo, solo la de quien lo ejecutó. El reparto de los cuatro experimentos restantes se define al programarlos.

### 5.13 Resumen del programa de experimentación

| Experimento | ASR | Historia | Incertidumbre | Esfuerzo | Cuándo |
|---|---|---|---|---|---|
| EXP-01 Presupuesto de latencia | ASR-1.1 | SOL-28 | Alta | 10 h | Semana 5 |
| EXP-02 Degradación elegante | ASR-1.2 | SOL-37 | Alta | 12 h | Semana 5 |
| EXP-04 Caída del caché | ASR-3.1 | SOL-29 | Alta | 8 h | Semana 6 |
| EXP-07 Tokenización | ASR-4.1 | SOL-23 | Alta | 12 h | Semana 6 |
| **Sprint 1 de diseño** | | | | **42 h** | **Semanas 5–6** |
| EXP-03 Modificabilidad | ASR-2.1 · ASR-2.2 | SOL-20 · SOL-21 | Media | 10 h | Programado |
| EXP-05 Pérdida de zona | ASR-3.2 | SOL-43 | Media-alta | 12 h | Programado |
| EXP-06 Continuidad offline | ASR-3.3 | SOL-44 | Media | 10 h | Programado |
| EXP-08 Integridad de pólizas | ASR-4.2 | SOL-45 | Media | 8 h | Programado |
| **Programa completo** | **9 ASR** | | | **82 h** | |

Los ocho experimentos quedan **diseñados** en esta entrega, que es lo que corresponde a la semana 4. Su **ejecución** se escalona: las 42 horas del Sprint 1 caben exactamente en la capacidad comprometida para el Proyecto Final 1 y equivalen a 21 puntos de historia con la convención de 1 punto igual a 2 horas, contenidos dentro de los 42 puntos asignados a las historias de arquitectura. Los cuatro restantes se ejecutan según disponibilidad y en el Proyecto Final 2, por depender de infraestructura de nube con costo —EXP-05 y EXP-08— o por tener incertidumbre menor —EXP-03 y EXP-06—.

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

## 7. Capacidad del equipo, esfuerzo y plan de trabajo

### 7.1 Qué es un punto de historia

Un **punto de historia** es una medida **relativa** del esfuerzo que cuesta completar una historia. No es una unidad de tiempo. Mide tamaño, considerando tres cosas a la vez: cuánto trabajo hay, cuánta complejidad tiene y cuánta incertidumbre queda.

**Por qué el equipo no estima directamente en horas.** Una misma historia le toma tiempos distintos a personas distintas, de modo que una estimación en horas depende de quién la haga y deja de ser comparable. En cambio, el juicio de que «esta historia es del doble de tamaño que aquella» es estable entre personas. Por eso se estima el tamaño relativo y solo después se convierte a tiempo usando la velocidad observada del equipo.

**Escala usada.** Se emplea la sucesión de Fibonacci —1, 2, 3, 5, 8, 13— porque los saltos crecientes reflejan que la incertidumbre aumenta con el tamaño: distinguir entre 1 y 2 puntos es razonable, pero pretender distinguir entre 20 y 21 es falsa precisión.

| Puntos | Significado en este proyecto | Ejemplo del backlog |
|---|---|---|
| **1** | Cambio trivial, sin lógica nueva | — |
| **2** | Una pantalla o un endpoint simple, sin integración externa | FE-01.1 Iniciar cotización seleccionando ramo |
| **3** | Lógica propia o una integración conocida | FE-01.2 Autorizar consulta Open Finance |
| **5** | Varios componentes o una integración con incertidumbre | FE-05.2 Verificar identidad con prueba de vida |
| **8** | Mecanismo transversal que toca varios servicios | HU-ARQ-07 Optimización de latencia del scoring |
| **13** | Mecanismo transversal con alta incertidumbre; candidato a dividirse | HU-ARQ-06 Tolerancia a fallos y failover |

**Regla de tamaño.** Ninguna historia funcional del backlog supera 5 puntos. Las dos historias de 13 puntos son de arquitectura y se conservan sin dividir porque su validación es un experimento único e indivisible.

**Conversión a horas.** Para poder contrastar el backlog contra un calendario fijo de ocho semanas, el equipo adoptó una equivalencia de referencia:

```
1 punto de historia  =  2 horas de trabajo efectivo
```

Esta equivalencia se fijó calibrando contra historias ya conocidas del proyecto y **se recalibrará al cerrar el primer sprint**, cuando exista velocidad medida en lugar de estimada. La conversión se usa solo para planear capacidad; la estimación de cada historia sigue siendo relativa.

### 7.2 Cálculo de la capacidad del equipo

**Paso 1 — Horas comprometidas por semana**

Cada integrante se comprometió en el acta de constitución a dedicar 12 horas semanales al proyecto.

```
4 integrantes  ×  12 horas/semana  =  48 horas/semana
```

**Paso 2 — Convertir esas horas a puntos**

```
48 horas/semana  ÷  2 horas/punto  =  24 puntos/semana  (capacidad bruta)
```

**Paso 3 — Descontar el trabajo que no es construcción**

No todas las horas comprometidas producen historias terminadas. Se van en reuniones de coordinación, revisión entre pares, preparación de entregas e imprevistos. El equipo aplica un **factor de carga del 80 %**, valor conservador estándar para equipos sin velocidad histórica medida.

```
24 puntos/semana  ×  0,80  =  19,2  ≈  19 puntos/semana
```

> **Velocidad efectiva del equipo: 19 puntos de historia por semana.**

**Paso 4 — Capacidad total del proyecto**

```
19 puntos/semana  ×  8 semanas  =  152 puntos
```

**Paso 5 — Capacidad realmente disponible para construir**

Las semanas 1 a 4 se dedicaron a acta de constitución, EDT, visión de arquitectura, escenarios de calidad, estrategia de pruebas y diseño de experimentos. Ese trabajo era necesario, pero no produjo historias del backlog de producto. Esa capacidad ya está consumida.

```
Capacidad total del proyecto            8 semanas × 19 pts  =  152 pts
Consumida en semanas 1–4 (arquitectura)  4 semanas × 19 pts  =   76 pts
──────────────────────────────────────────────────────────────────────
Disponible para construcción (semanas 5–8)  4 semanas × 19 pts  =  76 pts
```

> **Capacidad disponible para construir historias: 76 puntos.**

### 7.3 Capacidad por integrante

La misma cuenta, vista por persona, muestra cuánto aporta cada integrante a esos 76 puntos:

| Paso | Cálculo | Resultado |
|---|---|---|
| Horas comprometidas por persona, semanas 5 a 8 | 12 h/semana × 4 semanas | 48 h |
| Convertidas a puntos | 48 h ÷ 2 h/punto | 24 pts brutos |
| Aplicando el factor de carga del 80 % | 24 pts × 0,80 | **19 pts efectivos** |
| Multiplicado por los cuatro integrantes | 19 pts × 4 personas | **76 pts** |

| Integrante | Horas comprometidas | Puntos efectivos | Foco según su rol |
|---|---|---|---|
| Jazmin Córdoba | 48 h | 19 pts | Gerencia, usabilidad y entrega |
| Juan Mejía | 48 h | 19 pts | Web front, integración de APIs y pagos |
| Miguel Gómez | 48 h | 19 pts | Arquitectura, Open Finance, KYC, rendimiento y seguridad |
| Angie Arandio | 48 h | 19 pts | Dominio, web back, móvil y pruebas unitarias |
| **Total** | **192 h** | **76 pts** | |

Las 192 horas brutas equivalen a 154 horas efectivas tras el factor de carga; las 38 horas restantes son las que absorben coordinación, revisión e imprevistos.

### 7.4 El backlog completo frente a la capacidad

Aquí está el resultado que condiciona todo el plan y conviene enunciarlo sin rodeos:

| Concepto | Puntos | Historias |
|---|---|---|
| Backlog total del producto | 229 pts | 62 |
| Capacidad disponible, semanas 5 a 8 | 76 pts | — |
| **Diferencia** | **−153 pts** | **−45** |

**El equipo no puede construir las 62 historias en el Proyecto Final 1.** Con 19 puntos por semana, agotar 229 puntos tomaría 12 semanas de construcción y solo quedan 4. Esto no es un error de estimación ni de planeación: es la consecuencia de que Solventa es una plataforma completa y el Proyecto Final 1 cubre una parte del ciclo de vida.

Forzar los números para que cuadraran habría exigido reducir las estimaciones a un tercio de su valor, lo que produciría un plan que se incumple en la segunda semana. La respuesta correcta es la contraria: **declarar el alcance explícitamente** y comprometer solo lo que cabe.

### 7.5 Alcance comprometido: 76 puntos que sí caben

De las 62 historias del backlog se comprometen **17, que suman exactamente 76 puntos**. El criterio de selección, en este orden:

1. **¿Valida un ASR que el proyecto debe demostrar?** Sin las historias de arquitectura ligadas a los experimentos de las semanas 5 y 6 no hay evidencia que presentar.
2. **¿Pertenece al recorrido crítico mínimo?** *Cotizar → emitir* en web y *onboarding → consultar póliza* en móvil es el mínimo que hace demostrable el prototipo.
3. **¿Es prerrequisito de algo de prioridad alta?** Hereda la prioridad de aquello que habilita.

| Bloque | Historias | Puntos |
|---|---|---|
| Historias de arquitectura que sostienen los experimentos | 5 | 42 |
| Historias funcionales del recorrido crítico web | 8 | 21 |
| Historias funcionales del recorrido crítico móvil | 4 | 13 |
| **Total comprometido** | **17** | **76** |
| **Capacidad disponible** | | **76** |
| **Holgura** | | **0** |

> El alcance se ajustó a la capacidad exacta. No hay holgura, y el equipo asume ese compromiso de forma explícita: **ante un imprevisto se saca alcance, no se extienden horas.** Cualquier historia adicional que entre desplaza a otra.

Las 45 historias restantes, que suman 153 puntos, quedan documentadas, estimadas y priorizadas en el backlog, y se difieren al Proyecto Final 2. Su detalle completo está en `historias_de_usuario_v2.docx`.

### 7.6 Distribución del esfuerzo comprometido por integrante

Así se reparten los 76 puntos entre las cuatro personas, respetando la afinidad con su rol:

| Integrante | Historias asignadas | Puntos |
|---|---|---|
| **Miguel Gómez** | HU-ARQ-06 Tolerancia a fallos y failover (13) · FE-01.2 Autorizar consulta Open Finance (3) · FE-05.2 Verificar identidad con prueba de vida (5) | **21** |
| **Jazmin Córdoba** | HU-ARQ-07 Optimización de latencia del scoring (8) · HU-ARQ-03 Tokenización de PII (8) · FE-05.1 Capturar documento de identidad (3) | **19** |
| **Angie Arandio** | HU-ARQ-05 Persistencia PostgreSQL y Redis (5) · HU-ARQ-08 Event Bus Kafka (8) · FE-06.1 Ver pólizas en la billetera (2) · FE-06.2 Consultar pólizas sin conexión (3) | **18** |
| **Juan Mejía** | FE-10.2 Iniciar sesión con segundo factor (3) · FE-01.1 Iniciar cotización (2) · FE-01.3 Ingresar datos del bien (2) · FE-01.4 Ver la prima calculada (3) · FE-02.1 Completar datos del tomador (2) · FE-02.4 Pagar la primera prima (3) · FE-02.5 Emitir la póliza (3) | **18** |
| | **Total** | **76** |

La asignación queda entre 18 y 21 puntos por persona, frente a una capacidad individual de 19. La desviación de ±2 puntos se absorbe con trabajo en parejas en las historias de arquitectura, que es donde se concentra: Miguel lleva 21 porque HU-ARQ-06 es la historia más grande del alcance, y en ella trabaja acompañado durante la semana 6.

> Esta asignación es indicativa y se confirma en la planeación de cada sprint. Lo que no se negocia es el total: 76 puntos.

### 7.7 Compromiso por sprint

| Semana | Historias comprometidas | Puntos | Experimentos en curso |
|---|---|---|---|
| 5 (31 ago – 6 sep) | HU-ARQ-05, HU-ARQ-07, FE-10.2, FE-01.1 | 18 | EXP-01 · EXP-02 |
| 6 (7 – 13 sep) | HU-ARQ-06, FE-01.2, FE-01.3 | 18 | EXP-04 · EXP-07 |
| 7 (14 – 20 sep) | HU-ARQ-03, HU-ARQ-08, FE-01.4 | 19 | — |
| 8 (21 – 27 sep) | FE-02.1, FE-02.4, FE-02.5, FE-05.1, FE-05.2, FE-06.1, FE-06.2 | 21 | — |
| **Total** | **17 historias** | **76** | |

La carga sube ligeramente hacia el final —18, 18, 19, 21— porque las historias de la semana 8 son de menor tamaño y se pueden paralelizar mejor entre los cuatro integrantes, mientras que las primeras semanas concentran mecanismos de arquitectura que exigen concentración de una sola persona.

Las 42 horas de los cuatro experimentos del Sprint 1 de diseño (§5.13) están contenidas dentro de estos 76 puntos y no se suman aparte: construir el mecanismo y ejecutar el experimento que lo valida son parte de la misma historia. En puntos, esas 42 horas equivalen a 21 puntos, contenidos dentro de los 42 puntos asignados a las cinco historias de arquitectura.

### 7.8 Estado del proyecto

| Semana | Foco | Estado |
|---|---|---|
| 1 (3–9 ago) | Acta de constitución y backlog inicial | Completada |
| 2 (10–16 ago) | Visión de arquitectura, EDT y estrategia de pruebas | Completada |
| 3 (17–23 ago) | Escenarios de calidad, historias de usuario y frameworks | Completada · corregida en esta entrega |
| 4 (24–30 ago) | Modelos de arquitectura, patrones y diseño de experimentos | Esta entrega |
| 5 (31 ago–6 sep) | Ejecución de EXP-01 y EXP-02 · construcción del núcleo de cotización | Planificada |
| 6 (7–13 sep) | Ejecución de EXP-04 y EXP-07 · cliente web | Planificada |
| 7 (14–20 sep) | Cliente móvil · integración | Planificada |
| 8 (21–27 sep) | Integración, cierre y presentación final | Planificada |

### 7.9 Tablero

El tablero del proyecto en Jira refleja el backlog descompuesto, con épicas, estimación en puntos de historia, prioridad y la asociación de cada historia de arquitectura con su ASR y su experimento.

| Tablero | Qué muestra | Enlace |
|---|---|---|
| Jira — Tablero | Épicas, funciones e historias con estimación, prioridad y etiquetas | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/boards |
| Jira — Backlog | Backlog descompuesto de 62 historias ordenado por prioridad | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/backlog |
| Repositorio | Documentos, fuentes de los diagramas y registro de cambios | https://github.com/Migue765/proyecto-final-uniandes |

### 7.10 Estado del tablero tras la actualización

| Tipo de incidencia | Cantidad | Puntos de historia |
|---|---|---|
| Épica | 10 | — |
| Función | 10 | — |
| Historia | 62 | 229 |
| Subtarea | 25 | — |

El tablero es un proyecto gestionado por el equipo, cuya jerarquía tiene tres niveles: **Épica** en el nivel superior; **Función** e **Historia** como tipos hermanos en el nivel intermedio; y **Subtarea** en el inferior. Como Función e Historia comparten nivel, una historia no puede colgar de una función: ambas cuelgan de la épica, y la relación entre ellas se expresa con etiquetas. Por la misma razón la estimación vive únicamente en las historias; si las funciones también la llevaran, el tablero sumaría dos veces el mismo trabajo y mostraría 298 puntos donde el backlog real son 229.

### 7.11 Cómo leer el tablero

| Etiqueta | Significado |
|---|---|
| `FE-01` … `FE-10` | Función a la que pertenece la historia |
| `funcion` | Marca los diez ítems de tipo Función |
| `arquitectura` | Marca las once historias de arquitectura |
| `canal-web` · `canal-movil` · `canal-api` | Canal donde se implementa |
| `prioridad-alta` · `prioridad-media` · `prioridad-baja` | Prioridad asignada |
| `proyecto-1` · `proyecto-2` | Si entra en el alcance del Proyecto Final 1 o se difiere al 2 |
| `EXP-01` … `EXP-08` | Historia de arquitectura que lleva ese experimento |

Para ver únicamente el alcance comprometido de este proyecto, filtrar por `proyecto-1`: devuelve 17 historias y 76 puntos, que es exactamente el compromiso por sprint de §7.7.

---

## 8. Video con evidencias

### 8.1 Enlace al video

| Descripción | Duración | Presentadores | Enlace |
|---|---|---|---|
| Correcciones de la semana 3, modelos de arquitectura, patrones de diseño, propuesta de experimentos y recorrido por el tablero | 8 minutos | Jazmin Córdoba · Miguel Gómez · Juan Mejía · Angie Arandio | *(pegar enlace del video)* |

### 8.2 Contenido del video por bloque

| Bloque | Presentador | Minuto | Contenido |
|---|---|---|---|
| 0 | Jazmin Córdoba | 0:00 – 0:45 | Apertura y qué contiene la entrega |
| 1 | Jazmin Córdoba | 0:45 – 2:15 | Corrección de la semana 3: descomposición del backlog y cálculo de capacidad |
| 2 | Miguel Gómez | 2:15 – 4:00 | Los tres modelos de arquitectura |
| 3 | Juan Mejía | 4:00 – 5:45 | Patrones de diseño y su razonamiento frente a los ASR |
| 4 | Angie Arandio | 5:45 – 7:15 | Propuesta de experimentos y criterio de selección por incertidumbre |
| 5 | Jazmin Córdoba | 7:15 – 8:00 | Tablero actualizado y compromiso por sprint |

### 8.3 Guion de la sustentación

> El texto en párrafos es lo que se dice; el texto entre corchetes es lo que se muestra en pantalla. Los tiempos son orientativos.

### Bloque 0 — Apertura · Jazmin · 0:00 – 0:45

[Pantalla: portada de la hoja de trabajo de la semana 4]

Buenas tardes. Somos el Grupo 2 y este es el avance de la semana 4 del proyecto Solventa, nuestra aseguradora digital construida sobre Finanzas Abiertas.

Esta semana tenemos dos cosas para mostrar. La primera es la corrección de la entrega de la semana 3: recibimos una retroalimentación clara sobre el documento de historias de usuario y la trabajamos a fondo. La segunda es el entregable propio de esta semana: los modelos de arquitectura, el diseño detallado con patrones y la propuesta de experimentos.

Empezamos por la corrección, porque cambia la base sobre la que está construido todo lo demás.

---

### Bloque 1 — Corrección de la semana 3 · Jazmin · 0:45 – 2:15

[Pantalla: documento de historias de usuario v2.0, sección 1 «Correcciones aplicadas»]

La retroalimentación nos señaló tres cosas y las tomamos todas.

La primera: se esperaba la lista completa de historias del proyecto y nosotros entregamos veinte. Al revisarlo entendimos que el problema de fondo no era el número sino la granularidad. Teníamos ciento cincuenta y dos puntos de historia repartidos en veinte historias, es decir un promedio de siete coma seis puntos por historia. Un promedio así significa que lo que llamábamos historias eran en realidad features.

[Pantalla: anexo de mapeo, mostrando SOL-3 descompuesta en seis historias]

Por ejemplo, «Cotización de seguros en tiempo real» parecía una historia, pero adentro tenía el consentimiento de Open Finance, la captura de datos, el cálculo de la prima, la comparación de planes y la recuperación de la cotización. Son seis historias distintas, cada una verificable por separado.

Descompusimos todo el backlog y pasamos de veinte a sesenta y dos historias. El promedio bajó de siete coma seis a tres coma siete puntos por historia, y ninguna historia funcional supera cinco puntos. En el ejercicio encontramos además algo que no teníamos: la autenticación web era un recorrido crítico sin una sola historia asociada. Ahora es una épica propia.

[Pantalla: sección 2, cálculo de capacidad]

La segunda observación fue que no se encontró la evidencia del cálculo de capacidad. Y tenía razón: el cálculo existía, pero lo habíamos dejado en un archivo del repositorio en vez de ponerlo dentro del documento que se entrega. Esa fue nuestra lección de la semana. Ahora el cálculo está completo dentro del entregable, paso a paso: cuatro personas por doce horas son cuarenta y ocho horas semanales; a dos horas por punto son veinticuatro puntos; aplicando un factor de carga del ochenta por ciento quedan diecinueve puntos por semana.

[Pantalla: tabla de capacidad frente al backlog]

Y la tercera observación, la advertencia sobre el proyecto final dos, la respondimos de frente. Al re-estimar de abajo hacia arriba el backlog subió a doscientos veintinueve puntos. Nuestra capacidad para las semanas cinco a ocho es de setenta y seis. No forzamos las cifras para que cuadraran: declaramos explícitamente qué entra en el Proyecto Final 1 y qué se difiere al 2.

---

### Bloque 2 — Modelos de arquitectura · Miguel · 2:15 – 4:00

[Pantalla: Figura 1, vista funcional]

Paso al entregable de esta semana. Definimos tres vistas de la arquitectura.

Esta es la vista funcional. Son cuatro capas más una plataforma de datos. Arriba los canales: web en Angular, móvil en Kotlin nativo y los sistemas de socios. Después la capa Edge, donde ocurre todo lo que debe pasar antes de tocar lógica de negocio. Luego un backend por canal, y en el centro el núcleo de negocio con siete servicios delimitados por contexto de dominio.

Lo importante de este diagrama está abajo a la izquierda: los adaptadores externos. Ningún servicio del núcleo conoce el formato de un proveedor. Todo pasa por un adaptador. Esa decisión es la que sostiene el escenario de modificabilidad.

[Pantalla: Figura 2, vista de despliegue]

Esta es la vista de despliegue. Dos zonas de disponibilidad en configuración activo-activo, no activo-pasivo. La diferencia importa: si una zona cae, la capacidad de la otra ya está caliente, así que el tiempo de recuperación depende de la detección y no del arranque de instancias. Eso es lo que hace alcanzable el objetivo de diez minutos.

[Pantalla: Figura 3, vista de información]

Y esta es la vista de información. Además de las entidades, clasificamos los datos en tres niveles, y el nivel determina el tratamiento. Esto es lo que vuelve verificable el escenario de confidencialidad: la afirmación «cero datos personales en texto plano» solo se puede comprobar si antes se declaró qué cuenta como dato personal.

---

### Bloque 3 — Patrones y su razonamiento · Juan · 4:00 – 5:45

[Pantalla: sección 3.1, tabla resumen de patrones]

Documentamos doce patrones. Lo que quiero destacar no es la lista sino cómo la construimos: cada patrón está aquí porque hay un escenario de calidad que lo exige, y de cada uno declaramos qué sacrificamos al adoptarlo.

[Pantalla: sección 3.2, caché de perfiles]

Un ejemplo. El escenario de latencia pide percentil noventa y cinco por debajo de doscientos milisegundos. El perfil de riesgo requiere consultar a Open Finance, que tarda cientos de milisegundos. Ese objetivo es inalcanzable por construcción si la cotización espera esa llamada. Por eso el caché de perfiles no es una optimización: es lo que hace posible el escenario.

Y declaramos la contrapartida: un perfil cacheado puede estar hasta quince minutos desactualizado. Para un scoring de seguro es tolerable. No lo sería para un saldo de cuenta, y por eso el caché se aplica al perfil derivado y nunca al dato financiero crudo.

[Pantalla: sección 3.6, puertos y adaptadores]

Otro ejemplo. El escenario de modificabilidad pide integrar una pasarela de pagos nueva en menos de cuatro horas-hombre, sin tocar el núcleo. Con puertos y adaptadores, el núcleo define una interfaz en lenguaje de dominio y no conoce ninguna implementación. Integrar una pasarela nueva es escribir una clase y agregar una línea de configuración. Cero archivos modificados en el núcleo. Y eso no es una promesa: es una propiedad del grafo de dependencias, porque la flecha apunta al revés.

[Pantalla: sección 4, decisiones descartadas]

Documentamos también lo que descartamos y por qué. Un monolito modular nos habría simplificado estas ocho semanas, pero impide escalar de forma independiente el servicio de scoring, que es justamente el único con exigencia de latencia y el único con picos de diez veces el tráfico.

---

### Bloque 4 — Propuesta de experimentos · Angie · 5:45 – 7:15

[Pantalla: sección 5.1, marco de experimentación]

Diseñamos ocho experimentos que cubren los nueve escenarios de calidad. Partimos de una distinción: una prueba verifica que el sistema hace lo especificado; un experimento verifica que una decisión de diseño produce la propiedad que le atribuimos.

Por eso cada experimento está formulado como una hipótesis falsable, y cada uno tiene un criterio de refutación explícito. Definimos de antemano qué resultado nos obligaría a cambiar el diseño, porque un experimento que no puede fracasar no aporta información.

[Pantalla: sección 5.4, EXP-02]

Este es el de degradación elegante. La hipótesis: con el proveedor respondiendo por encima de setecientos milisegundos y diez veces la carga normal, el interruptor de circuito abre en menos de diez segundos y el sistema mantiene el percentil noventa y cinco bajo doscientos milisegundos sirviendo desde caché, sin perder ninguna petición.

Y el criterio de refutación: si perdemos peticiones por agotamiento del depósito de conexiones, eso nos diría que los tiempos de espera están mal calibrados frente al presupuesto de latencia. Sabemos de antemano qué aprenderíamos si sale mal.

[Pantalla: sección 5.13, resumen del programa]

Calificamos la incertidumbre de cada punto de sensibilidad y eso define cuándo se ejecuta cada uno. Cuatro resultaron de incertidumbre alta y forman el Sprint 1 de diseño, en las semanas cinco y seis. Un ejemplo de cómo esa calificación cambió un experimento: en integridad de pólizas, el bloqueo de escritura del almacenamiento es una garantía de la plataforma, así que ahí no tenemos incertidumbre. La incertidumbre está en si nuestra propia ruta de auditoría detecta el intento en menos de un segundo. Reenfocamos el experimento hacia eso.

El programa completo son ochenta y dos horas. Cuarenta y dos las comprometemos en el Sprint 1, que es exactamente nuestra capacidad, repartidas entre los cuatro integrantes: once, once, diez y diez horas.

[Pantalla: sección 6, refinamiento de estrategia de pruebas]

Refinamos también la estrategia de pruebas. El cambio principal es que incorporamos la prueba de arquitectura como nivel propio, distinto de la prueba de integración, porque su criterio de éxito es una medida y no una aserción.

---

### Bloque 5 — Tablero y cierre · Jazmin · 7:15 – 8:00

[Pantalla: tablero de Jira con el backlog descompuesto]

Este es el tablero con el backlog ya descompuesto. Se ven las épicas, la estimación en puntos, la prioridad de cada historia y la asociación de cada historia de arquitectura con su escenario de calidad.

[Pantalla: sección 7.2, compromiso por sprint]

Y este es el compromiso por sprint para las cuatro semanas que quedan: dieciocho, dieciocho, diecinueve y veintiún puntos, setenta y seis en total, que es exactamente nuestra capacidad. No dejamos holgura, y lo asumimos de forma explícita: si aparece un imprevisto, sacamos alcance en vez de extender horas.

En la semana cinco arrancamos con los experimentos de latencia y de degradación elegante, junto con la construcción del núcleo de cotización.

Gracias.

---

### Lista de verificación antes de grabar

- [ ] Los tres diagramas se ven nítidos a pantalla completa
- [ ] El tablero de Jira está actualizado con las 62 historias antes de grabar el bloque 5
- [ ] Los documentos están publicados y sus enlaces funcionan
- [ ] Cada presentador probó su bloque en voz alta y cabe en su tiempo
- [ ] La grabación tiene audio de un solo canal y volumen parejo entre presentadores
- [ ] El video queda subido con acceso por enlace y ese enlace está pegado en el documento de entregables


---

## 9. Corrección de la entrega de la semana 3

El documento de historias de usuario de la semana 3 obtuvo 10 de 40 puntos. Se corrigieron los tres hallazgos señalados y se detectaron dos adicionales por cuenta del equipo.

### 9.1 Hallazgos señalados y su corrección

| Observación recibida | Corrección aplicada | Dónde verificarla |
|---|---|---|
| *"Se esperaba la lista completa de historias de usuario del proyecto, no solo 20"* | El backlog se descompuso de 20 a **62 historias**. La revisión del tablero mostró el origen preciso del problema: ocho de las veinte estaban tipadas en Jira como **Función** y no como Historia, y ninguna tenía historias asociadas. El backlog tenía en realidad 12 historias y 8 funciones sin descomponer. El promedio pasó de 7,6 a 3,7 SP por historia | `historias_de_usuario_v2.docx` §3 y §4 · tablero Jira |
| *"No se encontró la evidencia de cálculo de la capacidad del equipo"* | El cálculo está ahora **dentro del entregable**, con la aritmética paso a paso: 4 personas × 12 h = 48 h/semana → 24 SP → factor de carga 80% → 19 SP/semana → 76 SP disponibles para las semanas 5 a 8. En la versión anterior el cálculo existía, pero en un archivo del repositorio que no se entregaba | `historias_de_usuario_v2.docx` §2 |
| *"Un backlog de 152 puntos de historia con sólo 20 HUs... le puede generar dolores de cabeza en el proyecto final 2"* | Se re-estimó de abajo hacia arriba: el backlog subió a **229 SP**. Frente a una capacidad de 76 SP se declara explícitamente qué entra en el Proyecto Final 1 y qué se difiere al Proyecto Final 2, con el criterio de corte documentado | `historias_de_usuario_v2.docx` §5 |

### 9.2 Hallazgos detectados por el equipo

| Hallazgo | Corrección |
|---|---|
| La **autenticación web** figuraba como recorrido crítico en la definición de alcance pero no tenía ninguna historia asociada en el backlog | Se creó la épica EP-06 y la función FE-10 con cuatro historias (9 SP) |
| Las historias **no eran legibles sin abrir Jira**: el documento solo listaba identificador, nombre y enlace | Cada historia aparece ahora completa en el documento, con enunciado *Como / Quiero / Para*, criterios de aceptación, estimación, prioridad, canal y ASR relacionado |

### 9.3 Resultado

| Métrica | Semana 3 | Corrección |
|---|---|---|
| Historias en el backlog | 20 | 62 |
| Promedio de puntos por historia | 7,6 SP | 3,7 SP |
| Historia funcional más grande | 8 SP | 5 SP |
| Story points totales | 152 SP | 229 SP |
| Alcance declarado para el Proyecto Final 1 | — | 76 SP · 17 historias |
| Diferido al Proyecto Final 2 | — | 153 SP · 45 historias |
| Recorridos críticos sin historias | 1 (autenticación web) | 0 |

---

## 10. Enlaces y pendientes

### 10.1 Enlaces de la entrega

| Recurso | Enlace |
|---|---|
| Este documento | *(pegar enlace)* |
| Historias de usuario v2.0 — corrección de la semana 3 | *(pegar enlace)* |
| Video de sustentación | *(pegar enlace)* |
| Jira — Tablero | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/boards |
| Jira — Backlog | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/backlog |
| Repositorio | https://github.com/Migue765/proyecto-final-uniandes |

### 10.2 Pendientes antes de enviar

- [ ] Publicar este documento y el de historias de usuario, y pegar sus enlaces en §10.1
- [ ] Grabar el video siguiendo el guion de §8.3 y pegar su enlace en §8.1 y §10.1
- [ ] Verificar que el tablero muestre las 62 historias antes de grabar el bloque 5 del video
- [ ] Confirmar que las tres figuras de §2 se ven nítidas en la versión publicada
