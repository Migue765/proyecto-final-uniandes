---portada
institucion: Solventa
facultad: Aseguradora digital sobre Finanzas Abiertas y Datos Abiertos
programa: Dirección de Arquitectura
curso: Estrategia de Pruebas
titulo: Estrategia de Pruebas
subtitulo: Componentes, alcance, tipos de prueba, frameworks y ambientes
proyecto: Versión 3.0
entrega: Documento técnico
grupo: Equipo de arquitectura
integrantes: Jazmin Natalia Córdoba Puerto ~ Gerencia de proyecto, usabilidad y entrega|Juan Esteban Mejía Izasa ~ Web front, integración de APIs y pagos|Miguel Alejandro Gómez Alarcón ~ Arquitectura, Open Finance, KYC, rendimiento y seguridad|Angie Natalia Arandio Niño ~ Dominio, web back, móvil y pruebas
fecha: Bogotá D.C. · 30 de agosto de 2026
---

## 0. Qué cambia en esta versión y por qué

Esta versión de la estrategia no reemplaza a la anterior: la refina como consecuencia del diseño detallado de la arquitectura. Cuatro cosas cambiaron en el diseño y las cuatro obligan a cambiar la forma de probar.

| Cambio en el diseño | Consecuencia sobre la estrategia de pruebas |
|---|---|
| El diseño identificó puntos de sensibilidad cuyo resultado adverso obliga a rehacer estructura, no a ajustar un parámetro | Aparece la **prueba de arquitectura** como nivel propio, con criterio de umbral y no de igualdad (§3) |
| Se definió un programa de tres experimentos —EXP-01, EXP-02 y EXP-03— sobre los puntos de sensibilidad de mayor incertidumbre | Cada experimento satisfactorio deja como residuo una prueba automatizada que lo vuelve a ejecutar (§3.4) |
| El backlog se descompuso de 20 a **62 historias** con estimación y prioridad, de las cuales 30 se comprometen | Los objetivos de cobertura se expresan sobre historias comprometidas y criterios de aceptación, no sobre porcentajes sueltos (§4) |
| Se cerró el stack de clientes: **Angular 17** para web y **Kotlin nativo** para móvil, con almacenamiento local en **Room cifrado con SQLCipher** | Los frameworks de prueba de ambos clientes quedan fijados y la continuidad sin conexión se verifica sobre Room, no sobre un almacén de clave-valor plano (§5) |

---

## 1. Aplicación bajo prueba

### 1.1 Datos del sistema

| Campo | Valor |
|---|---|
| Nombre del sistema | Solventa |
| Versión bajo prueba | 1.0.0 (MVP) |
| Tipo de sistema | Plataforma de seguros digitales — API-first / seguro embebido |
| Inicio de la fase de diseño | 3 de agosto de 2026 |
| Cierre de la fase de diseño | 27 de septiembre de 2026 |
| Fase de construcción | 28 de septiembre – 15 de noviembre de 2026 (tres sprints de dos, dos y tres semanas) |

### 1.2 Descripción del sistema

Solventa es una aseguradora digital greenfield, nativa en la nube, construida sobre Finanzas Abiertas y Datos Abiertos. Su propuesta de valor es cotizar, suscribir, emitir y gestionar siniestros de forma casi instantánea, embebiendo el seguro directamente en el punto de necesidad del cliente. Opera en los ramos de viaje, protección de dispositivos, microseguros de vida, seguro paramétrico y protección de pagos, y está orientada a los mercados de Colombia, México, Chile y Perú.

Lo que hace exigente su verificación no es la funcionalidad sino las propiedades que esa funcionalidad debe conservar: responder por debajo de 200 ms mientras un tercero se degrada, seguir sirviendo pólizas sin conexión, y no dejar un solo dato personal en texto plano en ninguna base, cola o traza. Ninguna de esas tres propiedades se comprueba con una aserción de igualdad, y de ahí nace el nivel de prueba que esta versión introduce.

### 1.3 Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend (microservicios) | Python 3.11 + Flask + Gunicorn |
| Frontend web | Angular 17 + TypeScript |
| Frontend móvil | Kotlin nativo (Android, API 34) |
| Almacenamiento local móvil | Room con SQLCipher |
| Base de datos relacional | PostgreSQL 15 |
| Caché y sesiones | Redis 7 |
| Mensajería asíncrona | Apache Kafka 3.x (KRaft en local) / Amazon MSK (producción) |
| Infraestructura cloud | AWS EKS + RDS + MSK + S3 con bloqueo de escritura + KMS + CloudWatch |
| Orquestación local | Docker Compose |
| Infraestructura como código | Terraform |
| Autenticación | JWT + OAuth 2.0 (Finanzas Abiertas Colombia) |
| Firma digital | AWS KMS + SHA-256 |

### 1.4 Componentes funcionales bajo prueba

| # | Componente | Canal | Descripción |
|---|---|---|---|
| 1 | Cotización y oferta | Web | Motor de rating con señales de Finanzas Abiertas; cotización en tiempo real |
| 2 | Suscripción y emisión | Web | Cobro, firma digital y emisión automática de póliza |
| 3 | Administración de pólizas | Web | Ciclo de vida: alta, cambios, renovación, cancelación |
| 4 | Gestión de siniestros | Web | Evaluación, aprobación, pago y enrutamiento a perito |
| 5 | Autenticación biométrica | Móvil | Verificación de identidad, prueba de vida, KYC/AML |
| 6 | Billetera de pólizas | Móvil | Consulta sin conexión, sincronización y autogestión desde el dispositivo |
| 7 | Reporte de siniestros | Móvil | Captura de fotos y video con geoetiquetado |
| 8 | Notificaciones y asistencia | Móvil | Avisos push y geolocalización de prestadores |
| 9 | Finanzas Abiertas / Datos Abiertos | API | Integración con fuentes financieras para perfilamiento de riesgo |
| 10 | KYC / AML | API | Verificación de identidad y prevención de lavado de activos |
| 11 | Pagos y recaudo | API | Procesamiento de pagos con idempotencia y alta disponibilidad |
| 12 | Bus de eventos | Infra | Eventos de dominio: cotización, emisión, siniestros, pagos |
| 13 | Tokenización | Infra | Custodia única del dato personal y emisión de tokens sin valor fuera del sistema |

Los componentes 1 a 12 provienen del alcance funcional original. El componente 13 se incorpora en esta versión: el diseño detallado convirtió la tokenización en un servicio del núcleo con frontera de custodia propia, y un componente responsable de una propiedad de seguridad verificable no puede quedar fuera del alcance de prueba.

### 1.5 Modelos que fijan la frontera de prueba

La estrategia toma como referencia los modelos de arquitectura de Solventa y no los reproduce aquí. De ellos se derivan tres decisiones de alcance:

- **La vista funcional** define las cuatro capas —canales, Edge, BFF y núcleo— y los ocho contratos entre componentes. Esos contratos son los puntos donde se ejerce la prueba de integración.
- **La vista de despliegue** define la distribución en dos zonas de disponibilidad. Es la que hace que el escenario de pérdida de zona sea comprobable, y también la que explica por qué se difiere.
- **La vista de información** clasifica los datos en restringido, confidencial e interno. Sin esa clasificación previa, la afirmación «cero datos personales en texto plano» no sería comprobable, porque no habría criterio para decidir qué cuenta como dato personal.

---

## 2. Contexto de la estrategia de pruebas

### 2.1 Objetivos

| # | Objetivo |
|---|---|
| O1 | Verificar que los recorridos críticos —cotizar, suscribir, emitir y reportar un siniestro— funcionan de extremo a extremo en los canales web y móvil |
| O2 | Validar que las APIs de integración —Finanzas Abiertas, KYC y pagos— responden dentro de los umbrales de latencia declarados en los escenarios de calidad (p95 ≤ 200 ms) |
| O3 | Comprobar que el sistema sostiene disponibilidad ≥ 99,9% en los recorridos críticos bajo carga variable y ante la caída de un componente |
| O4 | Detectar vulnerabilidades en el manejo de datos personales, la autenticación y los puntos expuestos, en línea con PCI-DSS y la Ley 1581 de 2012 |
| O5 | Verificar la presentación y la internacionalización para los cuatro mercados objetivo (Colombia, México, Chile y Perú) |
| O6 | Comprobar que cada decisión de diseño produce la propiedad de calidad que se le atribuyó, midiendo contra el umbral declarado en el escenario correspondiente |
| O7 | Sostener la cobertura del backlog descompuesto: que ninguna de las 30 historias comprometidas se dé por terminada sin sus criterios de aceptación automatizados |

Los objetivos O6 y O7 son los que esta versión incorpora. O6 antes se enunciaba como «validar las hipótesis de calidad mediante experimentos controlados»; la diferencia no es de redacción. Un experimento se ejecuta una vez y produce una decisión; O6 exige que la propiedad se siga midiendo después, lo que la convierte en una prueba y no en un hito.

### 2.2 Presupuesto de pruebas

#### Recursos humanos

El equipo lo conforman cuatro integrantes con formación en ingeniería de sistemas y experiencia en desarrollo de software y arquitectura. Cada uno se comprometió a doce horas semanales.

| Integrante | Rol en pruebas | Horas/semana |
|---|---|---|
| Jazmin Natalia Córdoba | Coordinación de la estrategia, aceptación y usabilidad | 12 h |
| Juan Esteban Mejía | Integración, contrato de API y pruebas del cliente móvil | 12 h |
| Miguel Alejandro Gómez | Prueba de arquitectura, rendimiento y seguridad | 12 h |
| Angie Natalia Arandio | Pruebas unitarias, de módulo y de dominio | 12 h |
| **Total del equipo** | | **48 h/semana · 336 h en las siete semanas de la fase de construcción** |

> Las 336 horas no son horas adicionales a la construcción: son las mismas horas comprometidas por el equipo, clasificadas según la actividad de verificación a la que sirven. En Solventa la prueba no es una etapa posterior sino la parte de cada historia que demuestra sus criterios de aceptación. Con la equivalencia de dos horas por punto y el factor de carga del 80%, esas 336 horas brutas equivalen a unas 269 horas efectivas, que es lo que sostiene el compromiso de 133 puntos.

#### Recursos computacionales

| Recurso | Detalle |
|---|---|
| Docker Compose (local) | Entorno integrado: Flask + PostgreSQL 15 + Redis 7 + Kafka KRaft + WireMock |
| AWS EC2 (t3.medium) | Ejecución de los planes de carga de JMeter |
| AWS Device Farm | Pruebas instrumentadas en dispositivos Android reales (API 34) |
| AWS CloudWatch | Métricas y trazas durante las corridas de carga y de inyección de fallas |
| AWS Fault Injection Service | Inyección de fallas para el escenario multi-zona, diferido a la fase de construcción |
| Toxiproxy | Degradación controlada de la red hacia los proveedores externos |
| Equipos del equipo | Desarrollo y ejecución local de pruebas unitarias y de módulo |
| Postman Cloud (nivel gratuito) | Colecciones de contrato de API compartidas por el equipo |

#### Recursos económicos

La estrategia se apoya exclusivamente en herramientas de código abierto y en niveles gratuitos de servicios en la nube. No se contratan servicios externos ni herramientas de pago.

| Herramienta | Costo | Uso |
|---|---|---|
| pytest 8 + pytest-cov | $0 | Pruebas unitarias y de módulo del backend |
| testcontainers-python | $0 | Pruebas de integración con PostgreSQL y Redis reales en contenedores |
| Jasmine 5 + Karma 6 | $0 | Pruebas unitarias y de componente del cliente web Angular 17 |
| Playwright | $0 | Pruebas de extremo a extremo y de aceptación en el navegador |
| JUnit 5 + MockK | $0 | Pruebas unitarias del cliente móvil Kotlin nativo |
| Espresso 3.6 | $0 | Pruebas instrumentadas de interfaz en el dispositivo Android |
| Robolectric | $0 | Pruebas de componentes Android sin emulador, incluida la internacionalización |
| Postman + Newman | $0 | Pruebas de contrato de API y su ejecución dentro del proceso de integración |
| Apache JMeter 5.6 | $0 | Generación de carga para las pruebas de arquitectura y de rendimiento |
| OWASP ZAP 2.14 | $0 | Análisis dinámico de seguridad |
| WireMock | $0 | Simulación de proveedores externos con retardo determinista |
| Toxiproxy | $0 | Inyección de latencia y cortes de red |
| AWS | $100 | Infraestructura de la nube: EKS, RDS, Device Farm e inyección de fallas |

### 2.3 Técnicas, niveles y tipos de prueba

| ID | Tipo | Nivel | Técnica | Herramienta | Componentes a probar | Objetivo |
|---|---|---|---|---|---|---|
| T1 | Automática | Unitario | Caja blanca | pytest · Jasmine y Karma · JUnit 5 y MockK | Motor de rating, cálculo de primas, motor de siniestros, componentes y servicios de Angular, modelos de vista y casos de uso de Kotlin | O1, O7 |
| T2 | Automática | Módulo | Caja negra | pytest con dobles de prueba | Un servicio completo con sus dependencias simuladas: cotización, suscripción, emisión, pólizas | O1, O7 |
| T3 | Automática | Integración | Caja negra | pytest con testcontainers · Postman y Newman | Colaboración real entre servicios y con PostgreSQL, Redis y el bus de eventos; adaptadores de Finanzas Abiertas, KYC y pagos | O2, O7 |
| T4 | Automática | Extremo a extremo | Caja negra | Playwright (web) · Espresso (móvil) | Recorrido web de cotización a emisión; recorrido móvil de ingreso a consulta de póliza | O1 |
| T5 | **Automática** | **Arquitectura** | **Medición contra umbral** | JMeter · Toxiproxy · WireMock · OWASP ZAP · verificación estática del grafo de dependencias | Camino de latencia del scoring, interruptor de circuito y ruta degradada, frontera de custodia de la tokenización | O6 |
| T6 | Automática | Rendimiento | Caja negra | Apache JMeter 5.6 | Motor de cotización bajo carga sostenida y bajo pico de campaña | O2, O3 |
| T7 | Automática | Seguridad | Caja negra | OWASP ZAP · inspección de volcados, temas del bus y tráfico | Autenticación, manejo de datos personales, puntos REST expuestos, consentimiento revocable | O4 |
| T8 | Manual | Aceptación | Exploratoria | Playwright · Espresso · guiones de recorrido | Recorrido completo web, incorporación biométrica móvil, reporte de siniestro | O1, O5 |
| T9 | Automática | Internacionalización | Parametrizada por locale | Jasmine y Karma con `@ngx-translate` · Robolectric con recursos por locale | Presentación en cuatro locales: es-CO, es-MX, es-CL, es-PE; formatos de moneda y fecha | O5 |

La fila T5 es la novedad de esta versión y la sección siguiente explica por qué no cabe dentro de T3.

---

## 3. Niveles de prueba y su relación con los experimentos

### 3.1 Los niveles consolidados

| Nivel | Qué verifica | Herramientas | Criterio de éxito |
|---|---|---|---|
| Unitaria | La lógica de una unidad aislada de sus colaboradores | pytest (backend) · Jasmine y Karma (web) · JUnit 5 y MockK (móvil) | 80% de líneas en backend · 70% en los clientes |
| Módulo | Un servicio completo con sus dependencias simuladas | pytest con dobles de prueba | Todos los criterios de aceptación de las historias del servicio |
| Integración | La colaboración real entre servicios y con la plataforma de datos | pytest con testcontainers · Postman y Newman | Los recorridos de cotización, emisión y siniestro completos |
| Extremo a extremo | El recorrido del usuario sobre el cliente real | Playwright (web) · Espresso (móvil) | Los dos recorridos críticos del alcance comprometido |
| **Arquitectura** | **Que una decisión de diseño produce la propiedad de calidad que se le atribuyó** | **JMeter · Toxiproxy · WireMock · OWASP ZAP · verificación estática** | **La medida de respuesta del escenario de calidad correspondiente** |
| Rendimiento | El comportamiento bajo carga sostenida y bajo pico | Apache JMeter | Los objetivos de percentil de los escenarios de latencia |
| Seguridad | La ausencia de vulnerabilidades conocidas y de fuga de datos | OWASP ZAP · inspección de volcados y del bus | 0 hallazgos críticos · 0 datos personales en texto plano |
| Internacionalización | El comportamiento por locale | Pruebas parametrizadas por locale | Los cuatro locales objetivo |

### 3.2 Por qué la prueba de arquitectura no es una prueba de integración

Es tentador tratar la verificación de un atributo de calidad como un caso más de prueba de integración: al fin y al cabo, ambas ejercitan varios componentes a la vez. La diferencia no está en cuántos componentes se tocan sino en **qué forma tiene la afirmación que se comprueba**.

| | Prueba de integración | Prueba de arquitectura |
|---|---|---|
| Pregunta que responde | ¿Estos componentes colaboran según el contrato acordado? | ¿La estructura elegida produce la propiedad que se le atribuyó? |
| Forma del criterio | Una **aserción de igualdad**: el resultado observado es igual al esperado | Una **medición contra un umbral**: la magnitud observada está por debajo o por encima de un valor declarado |
| Resultado | Binario y determinista: pasa o falla, y falla igual todas las veces | Una distribución de valores que se compara con un límite; el veredicto depende del percentil, no de una corrida |
| Qué se necesita para ejecutarla | Los componentes y sus contratos | Además, carga representativa, un instrumento de medida y un entorno con dimensionamiento conocido |
| Qué significa que falle | Alguien rompió un contrato | La estructura no sostiene el atributo: hay que rediseñar, no corregir una línea |
| Ejemplo en Solventa | El adaptador de pagos traduce la respuesta de la pasarela al modelo de dominio sin perder el identificador de la transacción | El p95 del recorrido de cotización se mantiene por debajo de 200 ms con 500 solicitudes por minuto y una tasa de acierto de caché del 80% |

Tres consecuencias prácticas se derivan de esa diferencia y explican por qué el nivel necesita existir por separado:

**La prueba de arquitectura no puede vivir en el mismo entorno que las demás.** Un umbral de latencia medido sobre un portátil compartido con el navegador y el entorno de desarrollo no significa nada. Necesita un entorno con dimensionamiento declarado, y por eso la sección 5.5 le reserva ambientes propios.

**Su veredicto es estadístico y necesita repetición.** Una corrida que arroja p95 de 198 ms no demuestra que el sistema cumple; demuestra que esa corrida cumplió. El criterio de aceptación fija además el número de corridas y la duración de cada una.

**Su falla no se corrige donde se detecta.** Cuando una prueba de integración falla, el arreglo está en el componente que rompió el contrato. Cuando falla una prueba de arquitectura, el arreglo suele estar en una decisión tomada semanas antes. Por eso cada escenario de la sección 6 declara de antemano la decisión alternativa que se adoptaría, en lugar de dejar esa decisión para el momento del fallo.

### 3.3 Relación entre experimentos y pruebas

El programa de experimentación de arquitectura y la estrategia de pruebas no compiten: se relevan. La distinción es de tiempo verbal.

> Un **experimento** responde: *¿esta decisión de diseño produce la propiedad que busco?*
> Una **prueba** responde: *¿esa propiedad sigue presente después del último cambio?*

El experimento se ejecuta una vez, sobre una porción del sistema construida a propósito, y su producto es una decisión: se conserva el diseño o se adopta la alternativa declarada. La prueba se ejecuta indefinidamente, sobre el sistema completo, y su producto es una señal: la propiedad se conserva o se perdió.

De ahí la regla que gobierna esta versión de la estrategia:

> **Cada experimento satisfactorio deja como residuo una prueba automatizada.**

No es una recomendación de higiene. Un experimento cuyo montaje se desmonta al terminar deja al equipo con una creencia —«la latencia cierra»— sin ningún mecanismo que la sostenga en el tiempo. La primera consulta sin índice o el primer campo añadido al perfil la invalidan sin que nadie se entere. Convertir el montaje en prueba cuesta poco porque el trabajo caro —el plan de carga, el simulador del proveedor, la instrumentación por salto, los datos cebo— ya está hecho: lo que falta es fijar el umbral como criterio de fallo y colgarlo del proceso de integración.

La regla opera también en sentido contrario. Un punto de sensibilidad cuya incertidumbre es baja no necesita experimento, pero sí necesita prueba: el escenario de integridad de pólizas no se experimenta, porque el bloqueo de escritura del almacenamiento de objetos es una garantía documentada de la plataforma, y aun así su tiempo de detección se verifica con una prueba de configuración dentro de la suite de seguridad.

### 3.4 El residuo de prueba de cada experimento

Los tres experimentos del programa de arquitectura se construyen y ejecutan entre el 7 y el 20 de septiembre de 2026. Cada uno deja una prueba de arquitectura permanente.

| Experimento | Punto de sensibilidad que resuelve | Escenario | Prueba residual que deja | Cuándo se ejecuta después |
|---|---|---|---|---|
| **EXP-01** Presupuesto de latencia | La tasa de acierto del caché de perfiles y el reparto del presupuesto entre saltos | ASR-1.1 | Plan de carga de JMeter con umbral de p95 y de tasa de acierto, más la instrumentación por salto que atribuye el tiempo a cada componente | En cada cierre de sprint y ante cualquier cambio en el camino de cotización |
| **EXP-02** Degradación elegante | La calibración del umbral y la ventana del interruptor de circuito | ASR-1.2 · ASR-3.1 | Prueba de resiliencia que degrada el proveedor con Toxiproxy y verifica apertura del interruptor, latencia de la ruta degradada y ausencia de pérdidas | Semanalmente y ante cualquier cambio de los parámetros del interruptor o del dimensionamiento de los depósitos |
| **EXP-03** Tokenización de datos sensibles | Centralizar la custodia del dato en un único servicio | ASR-4.1 | Verificación de hermeticidad: siembra de datos cebo y búsqueda automatizada sobre volcados, temas del bus y tráfico capturado, más comprobación de la versión de TLS | En cada integración a la rama principal, dentro de la suite de seguridad |

Los tres residuos comparten una propiedad: **fallan con un número, no con una excepción**. El de EXP-01 falla cuando el p95 cruza 200 ms; el de EXP-02, cuando la apertura del interruptor tarda más de 10 segundos; el de EXP-03, cuando aparece una sola coincidencia de un dato cebo donde no debería haberla. Esa forma de fallar es lo que los hace pruebas de arquitectura y no pruebas de integración con muchos componentes.

**Los escenarios sin experimento también tienen prueba.** De los nueve escenarios de calidad, tres tienen experimento propio, uno queda instrumentado dentro de otro, dos se verifican de forma estática, uno se ejercita en el prototipo móvil, uno se comprueba con una prueba de configuración y uno se difiere. Ninguno queda sin mecanismo, y la sección 6 lo declara escenario por escenario.

---

## 4. Objetivos de cobertura y alineación con el backlog

### 4.1 El backlog sobre el que se mide la cobertura

La versión anterior de esta estrategia se escribió cuando el backlog tenía 20 historias gruesas. La descomposición posterior lo llevó a **62 historias estimadas y priorizadas**, y eso cambia lo que significa «cubrir».

| Concepto | Puntos | Historias |
|---|---|---|
| Backlog total del producto | 229 | 62 |
| Capacidad de la fase de construcción | 133 | — |
| **Comprometido** | **133** | **30** |
| **Diferido a una fase posterior** | **96** | **32** |

Con 20 historias gruesas, un objetivo de cobertura solo podía expresarse como un porcentaje de líneas, porque no había unidad de verificación más fina. Con 62 historias descompuestas, cada una con sus criterios de aceptación, la unidad natural pasa a ser el criterio de aceptación, y el porcentaje de líneas queda como lo que siempre fue: un indicador de que no hay código sin ejercitar, no una medida de que el sistema hace lo que debe.

### 4.2 Los tres objetivos de cobertura

**Objetivo 1 — Cobertura de criterios de aceptación: 100% de las 30 historias comprometidas.** Ninguna historia se da por terminada sin que sus criterios de aceptación estén automatizados en el nivel que les corresponde. Esta es la definición de terminado del equipo y no admite excepción: una historia con criterios verificados a mano queda en curso.

**Objetivo 2 — Cobertura de escenarios de calidad: los nueve, con el mecanismo declarado.** Cada escenario tiene un mecanismo de verificación asignado en la sección 6, con su umbral y su instrumento. Ocho se verifican dentro de esta fase y uno —el escenario multi-zona— se difiere de forma explícita, con su razón documentada.

**Objetivo 3 — Cobertura de líneas por capa, como red de seguridad.**

| Capa | Umbral de cobertura de líneas | Instrumento |
|---|---|---|
| Backend Python / Flask | 80% | pytest-cov |
| Cliente web Angular 17 | 70% | Karma con Istanbul |
| Cliente móvil Kotlin nativo | 70% | JaCoCo |

### 4.3 Cobertura por bloque comprometido

Las 30 historias comprometidas se agrupan en seis bloques. Cada bloque declara qué niveles de prueba lo cubren y con qué criterio.

| Bloque comprometido | Historias | Puntos | Niveles que lo cubren | Criterio de cobertura |
|---|---|---|---|---|
| Historias de arquitectura que sostienen los escenarios de calidad | 10 | 79 | **Arquitectura** · integración · rendimiento · seguridad | La medida de respuesta del escenario asociado, medida contra su umbral |
| Cotización web completa — FE-01 | 6 | 15 | Unitaria · módulo · integración · extremo a extremo · rendimiento | 100% de criterios de aceptación · el recorrido completo en Playwright · p95 dentro del presupuesto |
| Suscripción y emisión web — FE-02 | 4 | 11 | Unitaria · módulo · integración · extremo a extremo | 100% de criterios de aceptación · transacción de emisión con cobro verificada de punta a punta |
| Autenticación web completa — FE-10 | 4 | 9 | Unitaria · integración · extremo a extremo · seguridad | 100% de criterios de aceptación · 0 hallazgos críticos de OWASP ZAP sobre el ingreso |
| Incorporación móvil — FE-05 | 3 | 11 | Unitaria · instrumentada · extremo a extremo | 100% de criterios de aceptación · recorrido biométrico verificado en dispositivo real |
| Billetera móvil, incluida la consulta sin conexión — FE-06 | 3 | 8 | Unitaria · instrumentada · **arquitectura** | 100% de criterios de aceptación · 100% de consultas resueltas sin conexión y sincronización ≤ 10 s |
| **Total comprometido** | **30** | **133** | | |

Las 10 historias de arquitectura concentran 79 de los 133 puntos comprometidos, el 59%. Ese reparto explica por qué la prueba de arquitectura necesita ser un nivel con presupuesto propio y no un apéndice de la prueba de integración: la mayor parte del esfuerzo comprometido existe para sostener atributos de calidad, no para agregar funcionalidad.

### 4.4 Las 32 historias diferidas

Las historias diferidas —administración de pólizas, gestión completa de siniestros, portal de socios y la mayor parte de la autogestión móvil— quedan documentadas, estimadas y priorizadas en el tablero, pero **fuera del alcance de automatización de esta fase**. Declararlo así evita el error de reportar una cobertura del 100% que en realidad solo cubre la mitad del producto.

Lo que sí se hace ahora con ellas es preservar la posibilidad de cubrirlas después: los contratos de API que consumirán ya están definidos en las colecciones de Postman, y los componentes de Angular y de Kotlin que compartirán se prueban desde ahora. La cobertura diferida es una deuda de verificación registrada, no una omisión.

### 4.5 Criterios de entrada y de salida

| Momento | Criterio |
|---|---|
| Entrada a la ejecución de un sprint | Los criterios de aceptación de sus historias están escritos y son medibles; el entorno en contenedores levanta con un solo comando |
| Salida de una historia | Sus criterios de aceptación están automatizados y verdes; la cobertura de la capa no baja del umbral; no introduce hallazgos críticos de seguridad |
| Salida de un sprint | Las pruebas de arquitectura residuales de EXP-01, EXP-02 y EXP-03 se ejecutaron y sus mediciones están dentro de umbral |
| Salida de la fase de construcción | Los dos recorridos críticos pasan de extremo a extremo en web y móvil; 0 hallazgos críticos de seguridad; 0 datos personales en texto plano; los cuatro locales verificados |

---

## 5. Frameworks y ambientes de prueba

### 5.1 Framework por capa

| Capa | Framework principal | Integración y extremo a extremo | Cobertura mínima |
|---|---|---|---|
| Backend Python 3.11 / Flask | pytest 8 + pytest-cov | testcontainers-python · Postman con Newman | 80% de líneas |
| Cliente web Angular 17 | Jasmine 5 + Karma 6 | Playwright | 70% de líneas |
| Cliente móvil Kotlin nativo | JUnit 5 + MockK + Robolectric | Espresso 3.6 | 70% de líneas |
| Arquitectura y rendimiento | Apache JMeter 5.6 | WireMock · Toxiproxy | La medida de respuesta de cada escenario |
| Seguridad | OWASP ZAP 2.14 | Inspección de volcados, temas del bus y tráfico | 0 hallazgos críticos · 0 datos personales en claro |

### 5.2 Backend — Python 3.11 / Flask

- **Pruebas unitarias:** pytest 8 con accesorios propios por servicio —cotización, perfilamiento, suscripción y emisión, pólizas, pagos y tokenización—, sin dependencias externas.
- **Pruebas de módulo:** pytest con dobles de prueba para las dependencias del servicio, de modo que se verifiquen sus criterios de aceptación sin depender de la disponibilidad de los demás.
- **Pruebas de integración:** pytest con testcontainers-python, que levanta PostgreSQL 15 y Redis 7 reales en contenedores. Se usa el contenedor real y no un doble porque buena parte de los defectos de integración viven en el dialecto de SQL y en la semántica de vencimiento del caché, que un doble no reproduce.
- **Pruebas de contrato de API:** colecciones de Postman exportadas y ejecutadas con Newman dentro del proceso de integración.
- **Cobertura:** pytest-cov con umbral mínimo del 80% de líneas.

```
# Pruebas unitarias con cobertura
pytest --cov=src --cov-report=html tests/unit/

# Pruebas de integración con contenedores reales
pytest -m integration tests/integration/ -v

# Verificación del umbral mínimo de cobertura
pytest --cov=src --cov-fail-under=80 tests/

# Contrato de API con Newman
newman run solventa_api.postman_collection.json --env-var base_url=http://localhost:5000
```

### 5.3 Cliente web — Angular 17 + TypeScript

- **Pruebas unitarias y de componente:** Jasmine 5 como marco de aserción y Karma 6 como ejecutor sobre navegador real en modo sin interfaz, para componentes, servicios y lógica de presentación.
- **Pruebas de extremo a extremo:** Playwright sobre el recorrido completo de cotización a emisión, con la API real levantada en contenedores.
- **Internacionalización:** `@ngx-translate/core` con pruebas de presentación por locale para es-CO, es-MX, es-CL y es-PE, incluyendo formato de moneda y de fecha.
- **Accesibilidad:** axe-core junto con las utilidades de accesibilidad del CDK de Angular, contra WCAG 2.1 AA.
- **Cobertura:** Karma con Istanbul, umbral mínimo del 70% de líneas.

```
# Pruebas unitarias y de componente con cobertura
ng test --no-watch --code-coverage

# Pruebas de extremo a extremo
npx playwright test --project=chromium
```

### 5.4 Cliente móvil — Kotlin nativo (Android)

- **Pruebas unitarias:** JUnit 5 con MockK para modelos de vista, repositorios y casos de uso. MockK se usa en lugar de un simulador genérico porque el código del cliente es Kotlin idiomático, con funciones de suspensión y objetos acompañantes que un simulador pensado para Java no intercepta bien.
- **Pruebas de componente sin emulador:** Robolectric para todo lo que necesita el marco de Android pero no un dispositivo —recursos por locale, formato de fecha y moneda, ciclo de vida de las vistas—. Es lo que permite ejecutar la mayor parte de la suite móvil en el proceso de integración sin arrancar un emulador.
- **Pruebas instrumentadas y de extremo a extremo:** Espresso 3.6 sobre emulador Android API 34 y sobre dispositivo real en Device Farm, para la incorporación biométrica y el recorrido de la billetera.
- **Pruebas sin conexión:** Espresso junto con UiAutomator, cortando la conectividad del dispositivo durante una sesión activa para verificar que la billetera resuelve las consultas desde **Room** y sincroniza al recuperar la red.
- **Pruebas del almacenamiento local cifrado:** el almacenamiento local es **Room con SQLCipher**, y eso hace verificable algo que un almacén de clave-valor en texto plano no permitía comprobar. Las pruebas cubren tres cosas: que la base en memoria responde las consultas de póliza sin red, que el archivo de base de datos en disco no contiene ninguna cadena legible de los datos sembrados, y que la frase de paso proviene del almacén de claves del dispositivo y no del código.
- **Cobertura:** JaCoCo, umbral mínimo del 70% de líneas.

```
# Pruebas unitarias y de componente con cobertura
./gradlew testDebugUnitTest jacocoTestReport

# Pruebas instrumentadas en emulador o dispositivo
./gradlew connectedDebugAndroidTest

# Corte de conectividad durante la sesión, para la consulta sin conexión
adb shell svc wifi disable && adb shell svc data disable
```

### 5.5 Ambientes de prueba

| Ambiente | Descripción | Herramientas activas | Nivel que atiende |
|---|---|---|---|
| Local | Docker Compose: Flask + PostgreSQL 15 + Redis 7 + Kafka KRaft + WireMock | pytest, Karma, Robolectric, Newman | Unitario · módulo · integración |
| Integración continua | Los mismos contenedores levantados por el proceso de integración en cada cambio | pytest con testcontainers, Newman, Karma, Robolectric, verificación de hermeticidad | Unitario · módulo · integración · seguridad |
| Preproducción | EKS con dos nodos t3.medium + RDS PostgreSQL + caché gestionada + bus de eventos gestionado | Playwright, Newman, agente remoto de JMeter | Extremo a extremo |
| **Arquitectura y rendimiento** | **EC2 t3.medium dedicado con dimensionamiento declarado, aislado de otro tráfico** | **JMeter 5.6 en modo distribuido · WireMock con retardo determinista · Toxiproxy · trazas por salto · CloudWatch** | **Arquitectura · rendimiento** |
| Seguridad | Instancia de preproducción aislada para análisis dinámico | OWASP ZAP en modo activo · consumidor de inspección del bus · consultas de verificación sobre la base | Seguridad |
| Móvil | Emulador Android API 34 en local y Device Farm para dispositivo real | Ejecutor de pruebas de Espresso · UiAutomator | Instrumentado · extremo a extremo |

El ambiente de arquitectura y rendimiento es dedicado y no compartido, y esa es la única forma de que sus umbrales signifiquen algo. Una medición de p95 tomada sobre una máquina que además está compilando el cliente web no mide el sistema: mide la máquina.

---

## 6. Pruebas de arquitectura por escenario de calidad

Cada escenario de calidad tiene un mecanismo de verificación asignado, con su medida de respuesta y su umbral. Tres de ellos se resuelven con los experimentos del programa de arquitectura, y cada experimento satisfactorio deja la prueba residual descrita en la sección 3.4. Los seis restantes se verifican con mecanismos proporcionados a su incertidumbre.

### 6.1 Mapa de mecanismos

| Escenario | Atributo | Historia | Mecanismo de verificación | Nivel |
|---|---|---|---|---|
| ASR-1.1 | Latencia | SOL-28 | **EXP-01** y su prueba residual de rendimiento | Arquitectura |
| ASR-1.2 | Latencia bajo degradación | SOL-37 | **EXP-02** y su prueba residual de resiliencia | Arquitectura |
| ASR-2.1 | Modificabilidad | SOL-20 | Verificación estática del grafo de dependencias y del registro de cambios | Arquitectura |
| ASR-2.2 | Modificabilidad | SOL-21 | Verificación estática del grafo de dependencias y del registro de cambios | Arquitectura |
| ASR-3.1 | Disponibilidad | SOL-29 | Instrumentado dentro de **EXP-02** | Arquitectura |
| ASR-3.2 | Disponibilidad multi-zona | SOL-43 | Diferido a la fase de construcción, con infraestructura provisionada | Arquitectura |
| ASR-3.3 | Continuidad sin conexión | SOL-44 | Prototipo móvil con Room y SQLCipher | Arquitectura · instrumentado |
| ASR-4.1 | Confidencialidad | SOL-23 | **EXP-03** y su prueba residual de hermeticidad | Arquitectura · seguridad |
| ASR-4.2 | Integridad | SOL-45 | Prueba de configuración dentro de la suite de seguridad | Seguridad |

### 6.2 ASR-1.1 — Latencia del scoring en operación normal

Historia en Jira: SOL-28 · Mecanismo: **EXP-01**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | Resolver el scoring desde un perfil derivado cacheado hace viable el presupuesto de 200 ms |
| Fuente del estímulo | Usuario final, con 500 cotizaciones por minuto |
| Estímulo | 500 solicitudes concurrentes al punto de cotización |
| Ambiente | Operación normal, sistema completamente disponible |
| Artefacto | Cotización y Rating + Perfilamiento y Scoring + caché de perfiles + adaptador de Finanzas Abiertas |
| Respuesta esperada | El sistema responde a todas las solicitudes sin error, sirviendo la mayoría de los perfiles desde caché |
| **Medida de respuesta y umbral** | p95 < 200 ms · p99 < 400 ms · tasa de acierto de caché ≥ 80% · 0% de errores |
| Instrumento | Apache JMeter 5.6 para la latencia extremo a extremo; contadores del servicio para la tasa de acierto; trazas por salto para atribuir el tiempo |
| Configuración | 500 hilos, rampa de 60 s, duración de 10 minutos, contra `POST /api/v1/cotizaciones`; el proveedor externo simulado con WireMock y retardo determinista |
| Criterio de refutación | El p95 supera 200 ms **teniendo la tasa de acierto en el objetivo**, lo que indicaría que el problema no está en la estrategia de caché sino en el procesamiento propio |
| Decisión alternativa | Precalcular las combinaciones más frecuentes de ramo y perfil, y reservar el cálculo exacto para las poco frecuentes: convierte un problema de latencia en uno de espacio |
| Prueba residual | Plan de carga con umbral de p95 y de tasa de acierto, ejecutado en cada cierre de sprint y ante cualquier cambio en el camino de cotización |

### 6.3 ASR-1.2 — Latencia con el proveedor de Finanzas Abiertas degradado

Historia en Jira: SOL-37 · Mecanismo: **EXP-02**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | Existe una calibración del interruptor de circuito que abre a tiempo para evitar el agotamiento de recursos sin abrir de forma espuria, y la ruta degradada sostiene el objetivo de latencia |
| Fuente del estímulo | Campaña masiva de un socio distribuidor, con 5.000 usuarios concurrentes |
| Estímulo | El proveedor de Finanzas Abiertas responde por encima de 700 ms |
| Ambiente | Proveedor externo degradado, caché disponible |
| Artefacto | Perfilamiento y Scoring con el interruptor instrumentado + adaptador de Finanzas Abiertas + caché de perfiles |
| Respuesta esperada | El interruptor abre, el sistema sirve el perfil desde caché y la cotización continúa sin interrumpirse |
| **Medida de respuesta y umbral** | Apertura del interruptor < 10 s desde el inicio de la degradación · p95 < 200 ms sirviendo desde caché · 0% de solicitudes perdidas por vencimiento del tiempo de espera externo · 0 aperturas espurias en 10 minutos de carga nominal |
| Instrumento | JMeter para la latencia; métrica de estado del interruptor para las transiciones; métricas del depósito de conexiones para las pérdidas |
| Configuración | Retardo creciente inyectado con Toxiproxy y WireMock sobre el proveedor simulado; recorrido de una rejilla de configuraciones de umbral y ventana |
| Criterio de refutación | Ninguna configuración de la rejilla logra abrir a tiempo sin producir aperturas espurias, lo que indicaría un problema de dimensionamiento de los depósitos y no de calibración |
| Decisión alternativa | Adoptar el mamparo de aislamiento como mecanismo primario y no complementario, asignando al adaptador un depósito de conexiones propio y estrecho |
| Prueba residual | Prueba de resiliencia semanal que degrada el proveedor y verifica las cuatro medidas anteriores |

### 6.4 ASR-2.1 — Modificabilidad: nueva pasarela de pagos regional

Historia en Jira: SOL-20 · Mecanismo: **verificación estática**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | El puerto de pagos es lo bastante general para absorber una pasarela con contrato distinto sin tocar el núcleo |
| Fuente del estímulo | El área de negocio solicita integrar una pasarela regional |
| Estímulo | Requerimiento de integrar una pasarela nueva |
| Ambiente | Tiempo de diseño, dentro de un sprint |
| Artefacto | Capa de adaptadores de pagos y el puerto `CobrarPrima` del núcleo |
| Respuesta esperada | El adaptador nuevo queda disponible sin cambios en los servicios del núcleo |
| **Medida de respuesta y umbral** | ≤ 4 horas-hombre · 0 archivos modificados en los servicios del núcleo |
| Instrumento | Registro de horas y análisis del registro de cambios por archivo; verificación de que no exista ninguna arista dirigida del núcleo hacia la capa de adaptadores |
| Configuración | Integrar una pasarela simulada durante un sprint y medir; la verificación del grafo se ejecuta como paso del proceso de integración |
| Por qué no lleva experimento | Su medida es el conjunto de archivos que cambian, y eso se comprueba con el grafo de dependencias y el registro del control de versiones. No requiere montaje ni carga: es una verificación estática |

### 6.5 ASR-2.2 — Modificabilidad: nuevo ramo de seguro

Historia en Jira: SOL-21 · Mecanismo: **verificación estática**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | El motor de rating es genuinamente agnóstico al ramo y un ramo nuevo es una definición cargada, no código nuevo |
| Fuente del estímulo | El área de producto solicita lanzar un ramo nuevo |
| Estímulo | Requerimiento de un ramo adicional |
| Ambiente | Tiempo de diseño |
| Artefacto | Motor de rating y catálogo de ramos en configuración versionada |
| Respuesta esperada | El ramo queda disponible en preproducción solo con configuración |
| **Medida de respuesta y umbral** | Disponible en ≤ 2 semanas · 0 modificaciones en el motor de rating |
| Instrumento | Registro de calendario y análisis del registro de cambios por archivo |
| Configuración | Cargar la definición de un ramo nuevo únicamente por configuración y verificar que el motor no cambió |
| Por qué no lleva experimento | Igual que el anterior: la propiedad se lee en el grafo de dependencias, no en una medición bajo carga |

### 6.6 ASR-3.1 — Disponibilidad: caída del caché

Historia en Jira: SOL-29 · Mecanismo: **instrumentado dentro de EXP-02**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | Al caer el caché, el interruptor y el mamparo hacen que la ruta de respaldo hacia PostgreSQL absorba el tráfico sin propagar la saturación |
| Fuente del estímulo | Fallo de infraestructura: caída del servicio de caché |
| Estímulo | Desconexión abrupta del caché durante operación normal |
| Ambiente | Operación normal con carga de 100 solicitudes por minuto |
| Artefacto | Cotización y Rating + caché de perfiles + interruptor de circuito + PostgreSQL |
| Respuesta esperada | El interruptor activa la ruta de respaldo y el sistema se recupera sin intervención |
| **Medida de respuesta y umbral** | Recuperación automática < 30 s · 0 transacciones perdidas · disponibilidad mensual ≥ 99,9% |
| Instrumento | `docker stop` sobre el contenedor de caché, JMeter para la carga, registros de recuperación y CloudWatch |
| Configuración | Carga de 100 solicitudes por minuto durante 5 minutos, apagando el caché en el minuto 2 |
| Por qué no lleva experimento propio | Los mecanismos que gobiernan este escenario —interruptor y mamparo— son los mismos que se calibran en EXP-02. Se instrumenta EXP-02 para registrar también esta transición, lo que ahorra unas ocho horas sin perder cobertura |

### 6.7 ASR-3.2 — Disponibilidad: pérdida de una zona

Historia en Jira: SOL-43 · Mecanismo: **diferido a la fase de construcción**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | El esquema multi-zona opera de hecho como activo-activo, de modo que el tiempo de recuperación depende de la detección del balanceador y no del arranque de instancias |
| Fuente del estímulo | Fallo de una zona de disponibilidad de la nube |
| Estímulo | Terminación de todos los nodos de la zona primaria |
| Ambiente | Operación normal, sistema multi-zona activo |
| Artefacto | Clúster de contenedores + balanceador + base de datos con réplica en espera |
| Respuesta esperada | El tráfico migra a la zona secundaria sin intervención manual |
| **Medida de respuesta y umbral** | RTO ≤ 10 min · RPO ≤ 30 s · disponibilidad mensual ≥ 99,9% |
| Instrumento | Servicio de inyección de fallas de la nube + CloudWatch + JMeter |
| Configuración | Terminar los nodos de la zona primaria bajo carga y medir el tiempo hasta la recuperación y la pérdida de datos |
| Razón del diferimiento | Requiere infraestructura multi-zona con costo real y un servicio de inyección de fallas contratado. El presupuesto de esta fase no lo cubre y el despliegue se hace en una sola zona. Se ejecuta en la fase de construcción, cuando la infraestructura ya esté provisionada |

### 6.8 ASR-3.3 — Continuidad sin conexión del cliente móvil

Historia en Jira: SOL-44 · Mecanismo: **prototipo móvil**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | Mantener una copia local cifrada con vigencia acotada permite servir el 100% de las consultas de póliza sin red y reconciliar al recuperarla |
| Fuente del estímulo | Usuario móvil que pierde señal de datos o de red inalámbrica |
| Estímulo | El dispositivo pierde conectividad mientras el usuario consulta sus pólizas activas en la billetera |
| Ambiente | Aplicación en uso, sesión autenticada, pólizas previamente sincronizadas |
| Artefacto | BFF Móvil + **almacenamiento local en Room cifrado con SQLCipher** + módulo de sincronización |
| Respuesta esperada | La aplicación sirve número, vigencia y cobertura desde la base local cifrada sin requerir conexión, y sincroniza los cambios pendientes al recuperar la red |
| **Medida de respuesta y umbral** | 100% de consultas resueltas sin conexión · sincronización automática ≤ 10 s al recuperar conectividad · vigencia del dato local de 24 h · 0 cadenas legibles de datos de póliza en el archivo de base de datos en disco |
| Instrumento | Espresso con UiAutomator sobre emulador y dispositivo real; inspección binaria del archivo de base de datos; Robolectric para los casos por locale |
| Configuración | Deshabilitar red inalámbrica y datos durante una sesión activa, ejercitar la consulta, reactivar la conectividad y cronometrar la sincronización |
| Por qué no lleva experimento propio | El prototipo móvil que se construye como parte de la experiencia de usuario ya ejercita este escenario; montar un experimento aparte duplicaría el montaje del emulador sin producir información nueva |

> El cambio de almacén de clave-valor plano a Room con SQLCipher no es cosmético para la estrategia: agrega un umbral que antes no existía. Con un almacén en texto plano la única propiedad comprobable era funcional —«la consulta responde sin red»—. Con una base cifrada se puede además abrir el archivo en disco y verificar que no contiene ninguna cadena de los datos sembrados, que es una medida y no una aserción de igualdad.

### 6.9 ASR-4.1 — Confidencialidad de los datos de Finanzas Abiertas

Historia en Jira: SOL-23 · Mecanismo: **EXP-03**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | Centralizar la custodia del dato personal en un único servicio de tokenización cuesta poco en latencia y no deja ninguna ruta por la que el dato original escape |
| Fuente del estímulo | Auditoría del regulador sobre el manejo de datos financieros |
| Estímulo | Intercambio de datos personales con el proveedor de Finanzas Abiertas durante una cotización |
| Ambiente | Operación normal, recorrido completo de cotización |
| Artefacto | Tokenización + Perfilamiento + Consentimientos y Auditoría + adaptador de Finanzas Abiertas + PostgreSQL + bus de eventos |
| Respuesta esperada | Todos los campos personales viajan cifrados y quedan tokenizados antes de salir del servicio custodio |
| **Medida de respuesta y umbral** | 0 coincidencias de datos cebo fuera del custodio, en volcados, en mensajes del bus o en tráfico capturado · TLS 1.3 en el 100% de las conexiones · latencia añadida por la tokenización < 15 ms · una entrada de auditoría por cada destokenización, sin excepción · efecto de la revocación de consentimiento < 5 minutos |
| Instrumento | OWASP ZAP como intermediario para la versión de TLS; búsqueda automatizada de datos cebo sobre volcados de PostgreSQL, temas del bus y tráfico capturado; trazas por salto para la latencia añadida |
| Configuración | Sembrar datos cebo reconocibles, ejecutar el recorrido completo de cotización y buscarlos después en todo lo que el sistema transmitió y persistió |
| Criterio de refutación | Una sola coincidencia de un dato cebo refuta la hipótesis e identifica el punto exacto de fuga, que es precisamente el valor del experimento |
| Decisión alternativa | Si la fuga aparece por el bus, publicar eventos con referencia en lugar de con contenido, de modo que el consumidor recupere lo que necesite sujeto a su propia autorización. Si la latencia añadida resulta inaceptable, introducir un caché de tokens de vigencia corta, aceptando el aumento de superficie de exposición |
| Prueba residual | Verificación de hermeticidad ejecutada en cada integración a la rama principal, dentro de la suite de seguridad |

### 6.10 ASR-4.2 — Integridad de las pólizas emitidas

Historia en Jira: SOL-45 · Mecanismo: **prueba de configuración**

| Campo | Detalle |
|---|---|
| Hipótesis de diseño | El almacenamiento inmutable y la firma digital hacen que cualquier alteración no autorizada sea detectable y quede registrada |
| Fuente del estímulo | Actor interno con acceso de escritura al almacenamiento de objetos |
| Estímulo | Modificación directa del objeto de una póliza sin pasar por la API |
| Ambiente | Póliza ya emitida y almacenada |
| Artefacto | Suscripción y Emisión + almacenamiento de objetos con bloqueo de escritura + gestión de llaves + registro de auditoría inmutable |
| Respuesta esperada | Se genera una alerta y la póliza queda bloqueada para acceso posterior |
| **Medida de respuesta y umbral** | Alerta en < 1 s · entrada completa en el registro de auditoría inmutable · póliza bloqueada |
| Instrumento | Guion de modificación directa sobre el almacenamiento, eventos de la nube y consulta al registro de auditoría |
| Configuración | Modificar el objeto con credenciales de prueba y cronometrar la alerta |
| Por qué no lleva experimento | El bloqueo de escritura del almacenamiento de objetos es una garantía documentada de la plataforma y sobre eso el equipo no tiene incertidumbre. Lo que sí es incierto —el tiempo de detección de la ruta de auditoría propia— se verifica con una prueba de configuración dentro de la suite de seguridad |

---

## 7. Distribución de esfuerzo y cronograma

### 7.1 Esfuerzo de la fase de diseño

El diseño de los tres experimentos se cierra el 6 de septiembre de 2026. Su construcción y ejecución ocurre entre el 7 y el 20 de septiembre, en paralelo con la construcción de la experiencia de usuario, y consume 34 horas-hombre.

| Experimento | Escenario | Historia | Esfuerzo | Construcción y ejecución |
|---|---|---|---|---|
| EXP-01 Presupuesto de latencia | ASR-1.1 | SOL-28 | 10 h | 7 – 13 de septiembre |
| EXP-02 Degradación elegante | ASR-1.2 · ASR-3.1 | SOL-37 · SOL-29 | 12 h | 7 – 20 de septiembre |
| EXP-03 Tokenización | ASR-4.1 | SOL-23 | 12 h | 14 – 20 de septiembre |
| **Total** | | | **34 h** | |

| Integrante | Actividades asignadas | Experimentos | Horas |
|---|---|---|---|
| Miguel Gómez | Construir Perfilamiento con su caché, instrumentar las trazas por salto y calibrar el interruptor recorriendo la rejilla | EXP-01 · EXP-02 | 9 h |
| Juan Mejía | Construir el adaptador de Finanzas Abiertas y su simulador con retardo, y el servicio de Tokenización integrado al recorrido de cotización | EXP-01 · EXP-03 | 9 h |
| Angie Arandio | Construir Cotización y el motor de rating; sembrar los datos cebo e inspeccionar volcados, temas del bus y tráfico | EXP-01 · EXP-03 | 8 h |
| Jazmin Córdoba | Preparar el entorno en contenedores, construir los planes de carga, ejecutar las corridas y consolidar las mediciones | EXP-01 · EXP-02 | 8 h |
| | | **Total** | **34 h** |

### 7.2 Calendario de pruebas de la fase de diseño

| Periodo | Actividad de pruebas |
|---|---|
| 3 – 16 de agosto | Diseño de los casos de prueba y montaje del entorno local en contenedores |
| 17 – 23 de agosto | Definición de las hipótesis de calidad y de la medida de respuesta y el umbral de cada escenario |
| 24 de agosto – 6 de septiembre | Diseño de los tres experimentos de arquitectura: métrica, instrumento, umbral y decisión alternativa |
| 7 – 20 de septiembre | Construcción y ejecución de EXP-01, EXP-02 y EXP-03; prototipo móvil con consulta sin conexión sobre Room |
| 21 – 27 de septiembre | Análisis de resultados, ajuste de las decisiones de diseño y conversión de cada experimento en su prueba automatizada residual |

### 7.3 Distribución del esfuerzo de la fase de construcción

Las 336 horas del equipo en las siete semanas de la fase de construcción, repartidas por la actividad de verificación a la que sirven.

| Tipo de prueba | Periodo | Horas | % | Responsable principal |
|---|---|---|---|---|
| Unitarias y de módulo — backend (pytest) | Sprints 1 a 3 · 28 sep – 15 nov | 48 h | 14% | Angie Arandio |
| Unitarias y de componente — web (Jasmine y Karma) | Sprints 1 y 2 · 28 sep – 25 oct | 24 h | 7% | Angie Arandio |
| Unitarias e instrumentadas — móvil (JUnit 5, MockK, Robolectric, Espresso) | Sprint 3 · 26 oct – 15 nov | 24 h | 7% | Juan Mejía |
| Integración y contrato de API (testcontainers, Postman y Newman) | Sprints 2 y 3 · 12 oct – 15 nov | 48 h | 14% | Juan Mejía |
| **Arquitectura y rendimiento (JMeter, Toxiproxy, verificación estática)** | Sprints 2 y 3 · 12 oct – 15 nov | 72 h | 21% | Miguel Gómez |
| Aceptación y usabilidad (Playwright) | Sprints 2 y 3 · 12 oct – 15 nov | 60 h | 18% | Jazmin Córdoba |
| Seguridad (OWASP ZAP y verificación de hermeticidad) | Sprint 3 · 26 oct – 15 nov | 36 h | 11% | Miguel Gómez |
| Internacionalización (cuatro locales) | Sprint 3 · 2 – 15 nov | 24 h | 7% | Todo el equipo |
| **Total** | | **336 h** | **100%** | |

La prueba de arquitectura y de rendimiento es la partida individual más grande, con el 21% del esfuerzo. Eso es coherente con el reparto del backlog comprometido: si 79 de los 133 puntos comprometidos son historias de arquitectura, la verificación de atributos de calidad no puede ser una partida residual.

### 7.4 Calendario de pruebas de la fase de construcción

| Sprint | Periodo | Foco de construcción | Actividad de pruebas |
|---|---|---|---|
| **Sprint 1** | 28 sep – 11 oct | Cimientos de arquitectura: persistencia, caché, bus de eventos, tokenización y consentimientos. Autenticación web completa | Unitarias y de módulo del backend; unitarias y de componente en Angular; contrato de API en Postman; primera corrida de la prueba residual de EXP-03 |
| **Sprint 2** | 12 – 25 oct | Recorrido de cotización completo con Finanzas Abiertas. Latencia del scoring y tolerancia a fallos | Integración con contenedores reales; pruebas residuales de EXP-01 y EXP-02 con sus umbrales; extremo a extremo del recorrido de cotización en Playwright |
| **Sprint 3** | 26 oct – 15 nov | Suscripción, emisión y pagos. Incorporación móvil y billetera. Parametrización, pasarelas, integridad y sincronización sin conexión | Unitarias e instrumentadas en Kotlin; consulta sin conexión sobre Room; verificación estática de modificabilidad; análisis dinámico de seguridad; los cuatro locales; cierre y reporte |

### 7.5 Ritmo de ejecución

| Suite | Cuándo se ejecuta | Duración objetivo |
|---|---|---|
| Unitarias y de componente (backend, web, móvil con Robolectric) | En cada cambio enviado al repositorio | < 5 min |
| Módulo e integración con contenedores reales | En cada solicitud de incorporación de cambios | < 15 min |
| Contrato de API con Newman | En cada solicitud de incorporación de cambios | < 5 min |
| Verificación de hermeticidad, residuo de EXP-03 | En cada integración a la rama principal | < 10 min |
| Extremo a extremo en web y móvil | Diaria, sobre preproducción | < 30 min |
| Prueba de arquitectura, residuo de EXP-01 | En cada cierre de sprint y ante cambios en el camino de cotización | 10 min por corrida, 3 corridas |
| Prueba de resiliencia, residuo de EXP-02 | Semanal y ante cambios en los parámetros del interruptor | 20 min por corrida |
| Análisis dinámico de seguridad completo | Semanal y antes de cada entrega | < 60 min |

Las pruebas de arquitectura no se ejecutan en cada cambio, y es deliberado: su corrida dura minutos y su veredicto es estadístico, de modo que ejecutarlas por cada envío al repositorio produciría ruido sin información. Se ejecutan cuando cambia algo del camino que miden, y siempre al cerrar un sprint.

---

## 8. Trazabilidad en el tablero

El tablero del proyecto en Jira es la única fuente de verdad sobre qué se prueba y con qué prioridad. La trazabilidad se mantiene con etiquetas, no con un documento aparte que se desactualiza.

| Etiqueta | Qué permite recuperar |
|---|---|
| `arquitectura` | Las once historias de arquitectura, cada una con su escenario de calidad asociado |
| `EXP-01` · `EXP-02` · `EXP-03` | Las historias de arquitectura cuya verificación depende de cada experimento y de su prueba residual |
| `canal-web` · `canal-movil` · `canal-api` | El canal donde se implementa la historia, que determina el framework de prueba que le corresponde |
| `sprint-1` · `sprint-2` · `sprint-3` | Las 30 historias comprometidas y su distribución, que es el alcance de automatización de esta fase |
| `diferido` | Las 32 historias fuera del alcance comprometido, con su cobertura declarada como deuda de verificación |
| `valvula-escape` | Las siete historias declaradas como primeras en salir ante un atraso, cuya ausencia no deja ningún escenario de calidad sin mecanismo |

Filtrando por `sprint-1`, `sprint-2` y `sprint-3` se obtienen las 30 historias y 133 puntos que esta estrategia se compromete a cubrir al 100% en criterios de aceptación. Filtrando por `diferido` se obtienen las 32 restantes con sus 96 puntos.

**Una precisión sobre la válvula de escape.** Las siete historias declaradas como primeras en salir se eligieron con un criterio que atañe directamente a esta estrategia: ninguna deja un escenario de calidad sin mecanismo de verificación. Que salga la sincronización al recuperar conectividad, por ejemplo, degrada la experiencia pero conserva la consulta sin conexión, que es la propiedad que el escenario ASR-3.3 exige. Recortar alcance no puede significar recortar la evidencia de que el sistema tiene los atributos que dice tener.

---

## 9. Resumen

| Dimensión | Estado en esta versión |
|---|---|
| Niveles de prueba | Ocho, con la **prueba de arquitectura** como nivel propio y criterio de umbral |
| Escenarios de calidad cubiertos | Los nueve, con mecanismo declarado; ocho verificados en esta fase y uno diferido con razón documentada |
| Experimentos de arquitectura | Tres —EXP-01, EXP-02 y EXP-03—, 34 horas, cada uno con su prueba residual automatizada |
| Cobertura comprometida | 30 de 62 historias, 133 de 229 puntos, 100% de sus criterios de aceptación automatizados |
| Cobertura de líneas | 80% en backend, 70% en el cliente web, 70% en el cliente móvil |
| Frameworks | pytest y testcontainers · Jasmine, Karma y Playwright · JUnit 5, MockK, Espresso y Robolectric · JMeter · OWASP ZAP · Postman y Newman |
| Ambientes | Seis, con uno dedicado y aislado para la prueba de arquitectura y de rendimiento |
| Esfuerzo | 34 h de experimentos en la fase de diseño · 336 h de verificación en la fase de construcción |
