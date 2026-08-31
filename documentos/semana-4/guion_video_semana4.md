# Guion del video de sustentación — Semana 4

**Proyecto Solventa · MISW4501 · Grupo 2**
**Duración:** 10 minutos · **Presentadores:** Jazmin Córdoba, Miguel Gómez, Juan Mejía, Angie Arandio

> Copia extraída de `entregable_semana4.docx` §8, para tenerla a mano al grabar.
> La versión que se califica es la del entregable; si se edita algo acá, replicarlo allá.


## Enlace al video

| Descripción | Duración | Presentadores | Enlace |
|---|---|---|---|
| Corrección de la semana 3, estilo y modelos de arquitectura, patrones, propuesta de experimentos, capacidad del equipo y recorrido por el tablero | 10 minutos | Jazmin Córdoba · Miguel Gómez · Juan Mejía · Angie Arandio | *(pegar enlace del video)* |

## Contenido por bloque

| Bloque | Presentador | Minuto | Contenido |
|---|---|---|---|
| 0 | Jazmin | 0:00 – 0:40 | Apertura y qué contiene la entrega |
| 1 | Jazmin | 0:40 – 2:10 | Corrección de la semana 3: descomposición del backlog y cálculo de capacidad |
| 2 | Miguel | 2:10 – 3:30 | Estilo de arquitectura y por qué se eligió |
| 3 | Miguel | 3:30 – 5:20 | Los seis modelos, con foco en el componente-conector UML |
| 4 | Juan | 5:20 – 7:00 | Patrones, tácticas y trazabilidad con los ASR |
| 5 | Angie | 7:00 – 8:40 | Propuesta de experimentos y criterio de cuántos |
| 6 | Jazmin | 8:40 – 10:00 | Capacidad, plan por sprint, tablero y cierre |

## Guion de la sustentación

> El texto en párrafos es lo que se dice; el texto entre corchetes es lo que se muestra en pantalla. Conviene grabar por bloques y unirlos.

### Bloque 0 — Apertura · Jazmin · 0:00 – 0:40

[Pantalla: portada del entregable]

Buenas tardes. Somos el Grupo 2 y este es el avance de la semana 4 del proyecto Solventa, nuestra aseguradora digital construida sobre Finanzas Abiertas.

Esta semana el foco estuvo en la arquitectura, que es lo que el curso pide priorizar en este bloque. Traemos cuatro cosas: la corrección de la entrega de la semana 3, el estilo y los modelos de arquitectura, el diseño detallado con patrones, y la propuesta de experimentos. Empezamos por la corrección, porque cambia la base sobre la que está construido todo lo demás.

### Bloque 1 — Corrección de la semana 3 · Jazmin · 0:40 – 2:10

[Pantalla: sección 9, tabla de correcciones]

La retroalimentación nos señaló tres cosas y las tomamos todas.

La primera: se esperaba la lista completa de historias y nosotros entregamos veinte. Al revisar el tablero encontramos el origen exacto del problema, y es más revelador de lo que pensábamos: **ocho de esas veinte estaban tipadas en Jira como Función, no como Historia**, y ninguna tenía historias asociadas. O sea que el backlog tenía en realidad doce historias y ocho funciones sin descomponer. El tablero ya nos estaba diciendo lo mismo que el profesor.

[Pantalla: anexo de mapeo, SOL-3 descompuesta]

Descompusimos todo. Pasamos de veinte a sesenta y dos historias, y el promedio bajó de siete coma seis a tres coma siete puntos por historia. En el ejercicio encontramos algo que no teníamos: la autenticación web era un recorrido crítico sin una sola historia asociada.

[Pantalla: sección 7.2, cálculo de capacidad]

La segunda observación fue que no se encontró la evidencia del cálculo de capacidad. Y tenía razón: el cálculo existía, pero lo habíamos dejado en un archivo del repositorio en vez de ponerlo dentro del documento que se entrega. Esa fue nuestra lección de la semana, y por eso este entregable es un documento único donde todo lo calificable está adentro.

### Bloque 2 — Estilo de arquitectura · Miguel · 2:10 – 3:30

[Pantalla: sección 2.1, tabla de estilos]

Paso a la arquitectura. Antes de mostrar modelos quiero declarar el estilo, porque es la decisión de la que dependen todas las demás.

Solventa no adopta un estilo puro sino una combinación de tres. **Microservicios** en el núcleo, **capas** por encima y **orientado a eventos** para lo asíncrono. Cada uno resuelve algo que los otros no.

Y quiero justificar el primero, porque es el más discutible. Un monolito modular nos habría simplificado estas ocho semanas, y era una alternativa seria. Lo descartamos por una razón concreta: el servicio de Perfilamiento es el único con exigencia de latencia de doscientos milisegundos y el único que enfrenta picos de diez veces el tráfico. En un monolito, escalar ese componente obliga a replicar todo el sistema. La independencia de despliegue no es un fin en sí: es lo que hace económicamente viable el escenario de latencia.

[Pantalla: último párrafo de 2.1]

También documentamos lo que dejamos fuera. No adoptamos arquitectura sin servidor pese a que encajaría con los picos, porque los arranques en frío son incompatibles con un presupuesto de doscientos milisegundos. Y no adoptamos malla de servicios porque su costo de operación no se justifica con siete servicios y cuatro personas.

### Bloque 3 — Los modelos · Miguel · 3:30 – 5:20

[Pantalla: Figura 1, contexto]

Hicimos seis modelos. Este es el de contexto: seis actores y cinco sistemas externos. Lo importante acá es que distinguimos qué integramos de verdad y qué simulamos: Open Finance, pagos y KYC se integran realmente porque son los que traen incertidumbre; Open Data y firma electrónica se simulan.

[Pantalla: Figura 2, vista funcional]

Esta es la vista funcional: cuatro capas más la plataforma de datos.

[Pantalla: Figura 3, componente-conector UML]

Y esta es la misma estructura en notación UML de componente-conector. Quiero detenerme porque el cambio no es estético.

En el diagrama anterior una flecha no dice si la interacción es síncrona o asíncrona, ni cuál es el contrato. Acá sí. Los cuadraditos son **puertos**, los círculos son **interfaces provistas**, los semicírculos son **interfaces requeridas**, y donde encajan hay un **contrato**.

Y esto es lo que hace que valga la pena: el componente Pagos declara el puerto **CobrarPrima** en lenguaje de dominio y no conoce ninguna pasarela concreta. Los adaptadores implementan PasarelaPago. Por eso integrar una pasarela nueva no puede obligar a modificar el núcleo: no hay ninguna arista que salga de él hacia afuera. Antes eso teníamos que afirmarlo en prosa; ahora se lee en el diagrama.

[Pantalla: Figura 4, despliegue]

El despliegue es activo-activo en dos zonas, no activo-pasivo. La diferencia importa: si una zona cae, la capacidad de la otra ya está caliente, así que la recuperación depende de la detección y no del arranque de instancias.

[Pantalla: Figuras 5 y 6, información y dominio]

Y la vista de información, donde clasificamos los datos en tres niveles. Esto es lo que vuelve verificable el escenario de confidencialidad: la afirmación «cero datos personales en texto plano» solo se puede comprobar si antes se declaró qué cuenta como dato personal.

### Bloque 4 — Patrones y tácticas · Juan · 5:20 – 7:00

[Pantalla: sección 3.2, marco]

Documentamos doce patrones. Antes de mostrarlos quiero aclarar tres conceptos que operan en niveles distintos, porque es fácil confundirlos.

El **atributo de calidad** es la propiedad que el sistema debe exhibir. La **táctica** es una decisión de diseño elemental que influye sobre esa propiedad. El **patrón** es una composición de tácticas con estructura conocida y contrapartidas documentadas. La cadena que seguimos siempre es la misma: un ASR exige una propiedad, unas tácticas la consiguen, un patrón las materializa, se asigna a componentes, y un experimento mide si funcionó.

[Pantalla: Figura 7, asignación de patrones]

Esta vista muestra dónde vive cada patrón. Fíjense que el mamparo y el multi-zona se anotan sobre la capa y no sobre una caja: no son componentes, son políticas transversales.

[Pantalla: sección 3.4, matriz de trazabilidad]

Y esta es la matriz completa: patrón, tácticas que materializa, componentes donde vive, ASR que lo justifica y experimento que lo valida. Lo que demuestra es que **no hay patrones huérfanos** —ninguno adoptado sin un requisito que lo exija— ni ASR sin mecanismo asignado.

[Pantalla: sección 3.6, cache-aside]

Un ejemplo del razonamiento. El escenario de latencia pide percentil noventa y cinco bajo doscientos milisegundos. El perfil de riesgo requiere consultar Open Finance, que tarda cientos de milisegundos. Ese objetivo es inalcanzable por construcción si la cotización espera esa llamada. Por eso el caché no es una optimización: es lo que hace posible el escenario.

Y de cada patrón declaramos qué sacrificamos. Acá: un perfil cacheado puede estar hasta quince minutos desactualizado. Para un scoring de seguro es tolerable. No lo sería para un saldo de cuenta, y por eso el caché se aplica al perfil derivado y nunca al dato financiero crudo.

### Bloque 5 — Experimentos · Angie · 7:00 – 8:40

[Pantalla: sección 5.1]

Diseñamos tres experimentos. Y quiero explicar por qué son tres, porque esa fue la decisión más importante de esta sección.

Partimos de una distinción: una prueba verifica que el sistema hace lo especificado; un experimento valida una hipótesis de diseño sobre la que tenemos incertidumbre, construyendo una porción real del diseño.

[Pantalla: sección 5.3, criterio]

El número sale de dos restricciones. La primera es de calendario: los experimentos se construyen en las semanas seis y siete, que son las mismas dos semanas de toda la experiencia de usuario. Haciendo la cuenta, quedan unas treinta y seis horas para experimentos. Los tres nuestros suman treinta y cuatro.

La segunda es de utilidad: solo se experimenta donde hay incertidumbre real. Evaluamos los nueve puntos de sensibilidad y solo cuatro resultaron de incertidumbre alta, y de esos uno queda cubierto por otro.

[Pantalla: sección 5.7, descartados]

Los cinco que descartamos quedan documentados con su razón. Un caso que ilustra el criterio: la integridad de las pólizas. El bloqueo de escritura del almacenamiento es una garantía de la plataforma, así que ahí no tenemos incertidumbre. La incertidumbre está en si nuestra propia ruta de auditoría detecta el intento en menos de un segundo, y eso es una prueba de configuración, no un experimento.

[Pantalla: sección 5.5, EXP-02]

Cada experimento tiene criterio de refutación. Este es el de degradación elegante. Si perdemos peticiones por agotamiento del depósito de conexiones, eso nos diría que los tiempos de espera están mal calibrados frente al presupuesto de latencia. Sabemos de antemano qué aprenderíamos si sale mal, y qué decisión cambiaríamos.

### Bloque 6 — Capacidad, plan y tablero · Jazmin · 8:40 – 10:00

[Pantalla: sección 7.2]

Cierro con la capacidad, que es lo que nos costó puntos la semana pasada y ahora está completo dentro del entregable.

Cuatro personas por doce horas son cuarenta y ocho horas semanales. A dos horas por punto son veinticuatro puntos. Con un factor de carga del ochenta por ciento quedan **diecinueve puntos por semana**.

[Pantalla: sección 7.5]

Y acá está la parte importante. En el Proyecto Final 1 no construimos historias de usuario: construimos arquitectura, experimentos y experiencia de usuario. Las historias se implementan en los tres sprints del Proyecto Final 2, que son siete semanas. Diecinueve por siete son **ciento treinta y tres puntos**.

Nuestro backlog son doscientos veintinueve. No caben. Y lo decimos sin rodeos: forzar los números habría exigido reducir las estimaciones a la mitad, produciendo un plan que se incumple en el primer sprint. Comprometemos treinta historias, ciento treinta y tres puntos, holgura cero. Ante un imprevisto sacamos alcance, no extendemos horas.

[Pantalla: sección 7.7, viabilidad]

Verificamos además que la arquitectura sea construible, porque los tutores validarán que el código del Proyecto Final 2 se conforme a ella. Construimos cinco de los siete servicios del núcleo y tres de los cinco adaptadores; el resto se simula o se difiere, y está declarado.

[Pantalla: tablero de Jira filtrado]

Y este es el tablero, con las sesenta y dos historias, sus estimaciones y sus etiquetas.

En la semana cinco cerramos la arquitectura, terminamos el diseño de los experimentos y arrancamos los wireframes. Gracias.

## Lista de verificación antes de grabar

- [ ] Las diez figuras se ven nítidas a pantalla completa
- [ ] El tablero de Jira está actualizado antes de grabar el bloque 6
- [ ] Cada presentador probó su bloque en voz alta y cabe en su tiempo
- [ ] Audio de un solo canal y volumen parejo entre presentadores
- [ ] El video queda subido con acceso por enlace y ese enlace está pegado en §8.1 y §10.1
