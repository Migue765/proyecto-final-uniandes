# Guion del video de sustentación — Semana 4

**Proyecto Integrador · Grupo 2 · Solventa**
**Duración objetivo:** 8 minutos · **Presentadores:** 4

> **Cómo usar este guion.** El texto en párrafos es lo que se dice; el texto entre corchetes es lo que se muestra en pantalla. Los tiempos son orientativos. Conviene grabar por bloques y unirlos, en lugar de intentar una sola toma continua.

---

## Bloque 0 — Apertura · Jazmin · 0:00 – 0:45

[Pantalla: portada de la hoja de trabajo de la semana 4]

Buenas tardes. Somos el Grupo 2 y este es el avance de la semana 4 del proyecto Solventa, nuestra aseguradora digital construida sobre Finanzas Abiertas.

Esta semana tenemos dos cosas para mostrar. La primera es la corrección de la entrega de la semana 3: recibimos una retroalimentación clara sobre el documento de historias de usuario y la trabajamos a fondo. La segunda es el entregable propio de esta semana: los modelos de arquitectura, el diseño detallado con patrones y la propuesta de experimentos.

Empezamos por la corrección, porque cambia la base sobre la que está construido todo lo demás.

---

## Bloque 1 — Corrección de la semana 3 · Jazmin · 0:45 – 2:15

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

## Bloque 2 — Modelos de arquitectura · Miguel · 2:15 – 4:00

[Pantalla: Figura 1, vista funcional]

Paso al entregable de esta semana. Definimos tres vistas de la arquitectura.

Esta es la vista funcional. Son cuatro capas más una plataforma de datos. Arriba los canales: web en Angular, móvil en Kotlin nativo y los sistemas de socios. Después la capa Edge, donde ocurre todo lo que debe pasar antes de tocar lógica de negocio. Luego un backend por canal, y en el centro el núcleo de negocio con siete servicios delimitados por contexto de dominio.

Lo importante de este diagrama está abajo a la izquierda: los adaptadores externos. Ningún servicio del núcleo conoce el formato de un proveedor. Todo pasa por un adaptador. Esa decisión es la que sostiene el escenario de modificabilidad.

[Pantalla: Figura 2, vista de despliegue]

Esta es la vista de despliegue. Dos zonas de disponibilidad en configuración activo-activo, no activo-pasivo. La diferencia importa: si una zona cae, la capacidad de la otra ya está caliente, así que el tiempo de recuperación depende de la detección y no del arranque de instancias. Eso es lo que hace alcanzable el objetivo de diez minutos.

[Pantalla: Figura 3, vista de información]

Y esta es la vista de información. Además de las entidades, clasificamos los datos en tres niveles, y el nivel determina el tratamiento. Esto es lo que vuelve verificable el escenario de confidencialidad: la afirmación «cero datos personales en texto plano» solo se puede comprobar si antes se declaró qué cuenta como dato personal.

---

## Bloque 3 — Patrones y su razonamiento · Juan · 4:00 – 5:45

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

## Bloque 4 — Propuesta de experimentos · Angie · 5:45 – 7:15

[Pantalla: sección 5.1, marco de experimentación]

Diseñamos nueve experimentos, uno por cada escenario de calidad. Partimos de una distinción: una prueba verifica que el sistema hace lo especificado; un experimento verifica que una decisión de diseño produce la propiedad que le atribuimos.

Por eso cada experimento está formulado como una hipótesis falsable, y cada uno tiene un criterio de refutación explícito. Definimos de antemano qué resultado nos obligaría a cambiar el diseño, porque un experimento que no puede fracasar no aporta información.

[Pantalla: sección 5.3, EXP-02]

Este es el de degradación elegante. La hipótesis: con el proveedor respondiendo por encima de setecientos milisegundos y diez veces la carga normal, el interruptor de circuito abre en menos de diez segundos y el sistema mantiene el percentil noventa y cinco bajo doscientos milisegundos sirviendo desde caché, sin perder ninguna petición.

Y el criterio de refutación: si perdemos peticiones por agotamiento del depósito de conexiones, eso nos diría que los tiempos de espera están mal calibrados frente al presupuesto de latencia. Sabemos de antemano qué aprenderíamos si sale mal.

[Pantalla: sección 5.11, resumen de esfuerzo]

Estimamos el esfuerzo de los nueve: ochenta y seis horas en total. Cuarenta y dos las comprometemos en el Proyecto Final 1, que son los cuatro experimentos de prioridad alta. Esas cuarenta y dos horas equivalen a veintiún puntos de historia, y están contenidas dentro de los cuarenta y dos puntos que asignamos a las historias de arquitectura, porque construir el mecanismo y ejecutar el experimento que lo valida son la misma historia.

[Pantalla: sección 6, refinamiento de estrategia de pruebas]

Refinamos también la estrategia de pruebas. El cambio principal es que incorporamos la prueba de arquitectura como nivel propio, distinto de la prueba de integración, porque su criterio de éxito es una medida y no una aserción.

---

## Bloque 5 — Tablero y cierre · Jazmin · 7:15 – 8:00

[Pantalla: tablero de Jira con el backlog descompuesto]

Este es el tablero con el backlog ya descompuesto. Se ven las épicas, la estimación en puntos, la prioridad de cada historia y la asociación de cada historia de arquitectura con su escenario de calidad.

[Pantalla: sección 7.2, compromiso por sprint]

Y este es el compromiso por sprint para las cuatro semanas que quedan: dieciocho, dieciocho, diecinueve y veintiún puntos, setenta y seis en total, que es exactamente nuestra capacidad. No dejamos holgura, y lo asumimos de forma explícita: si aparece un imprevisto, sacamos alcance en vez de extender horas.

En la semana cinco arrancamos con los experimentos de latencia y de degradación elegante, junto con la construcción del núcleo de cotización.

Gracias.

---

## Lista de verificación antes de grabar

- [ ] Los tres diagramas se ven nítidos a pantalla completa
- [ ] El tablero de Jira está actualizado con las 62 historias antes de grabar el bloque 5
- [ ] Los documentos están publicados y sus enlaces funcionan
- [ ] Cada presentador probó su bloque en voz alta y cabe en su tiempo
- [ ] La grabación tiene audio de un solo canal y volumen parejo entre presentadores
- [ ] El video queda subido con acceso por enlace y ese enlace está pegado en el documento de entregables
