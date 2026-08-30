# Guion — Video de Sustentación Semana 3

**Proyecto:** Solventa · MISW4501 · Grupo 2
**Duración objetivo:** 5 minutos
**Presentadores:** 3 (asignación sugerida — pueden intercambiarse)

| Rol en el guion | Integrante sugerido |
| --- | --- |
| Presentador 1 — Apertura y correcciones de gestión | Jazmin Córdoba |
| Presentador 2 — Correcciones de arquitectura (ASRs / Jira) | Miguel Gómez |
| Presentador 3 — Avances nuevos semana 3 | Angie Arandio |

**Antes de grabar, tener abierto en pantalla:**
1. Tablero Jira — proyecto SOL (vista Backlog)
2. Historia SOL-44 en Jira (para mostrar la corrección)
3. `estrategia_pruebas_solventa.docx`
4. `definicion_frameworks_ambientes.docx`
5. `gantt_cronograma_pruebas.xlsx`
6. `historias_de_usuario.docx` (documento de ASRs)

---

## 0:00 – 0:40 | Apertura (Presentador 1 — Jazmin)

> "Hola, somos el Grupo 2 del proyecto Solventa. En este video les mostramos cómo corregimos los comentarios que recibimos en la entrega de la semana 2 sobre nuestro backlog de arquitectura, y los avances nuevos que construimos esta semana 3: estrategia de pruebas, frameworks, ambientes y el cronograma de ejecución."

*(Cambiar a pantalla compartida: tablero Jira, proyecto SOL)*

---

## 0:40 – 2:20 | Corrección: Backlog de arquitectura y ASRs en Jira (Presentador 2 — Miguel)

> "El segundo comentario fue más de fondo: nos dijeron que el backlog de arquitectura que presentamos no cumplía con los campos esperados de un escenario de calidad — fuente del estímulo, estímulo, ambiente, respuesta y medida de respuesta — y que debíamos reescribirlos con la plantilla: 'Como fuente, cuando estímulo, dado que el ambiente es X, quiero que respuesta, esto debe suceder medida de respuesta'.
>
> Fuimos a cada una de nuestras 9 historias de arquitectura en Jira y, además de la tabla técnica que ya teníamos con los 6 campos, le agregamos esa frase narrativa a cada escenario. Aquí pueden ver, por ejemplo, en HU-ARQ-07 de optimización de latencia, cómo queda la tabla junto con la frase en formato de historia.
>
> Y aprovechando esta revisión completa, encontramos y corregimos un error: la historia de sincronización offline del cliente móvil tenía copiado por error el mismo escenario de caída de Redis de otra historia. Le escribimos su propio escenario de calidad, específico para pérdida de conectividad en el celular, con su propia medida de respuesta de sincronización en menos de 10 segundos."

*(Mostrar en pantalla: SOL-28 con tabla + frase narrativa, luego SOL-44 con el escenario corregido ASR-3.3)*

---

## 2:20 – 4:35 | Avances nuevos de la semana 3 (Presentador 3 — Angie)

> "Ahora les mostramos lo nuevo que construimos esta semana. Primero, el documento de estrategia de pruebas versión 2, donde definimos un experimento de validación por cada uno de nuestros escenarios de calidad: pruebas de carga con JMeter para los ASRs de latencia, simulación de caída de Redis y de zona de AWS para disponibilidad, y escaneo con OWASP ZAP para los de seguridad.
>
> Segundo, el documento de definición de frameworks y ambientes. Aquí también tuvimos un ajuste importante: como equipo decidimos cambiar nuestro stack de frontend de React a Angular, y el de móvil de React Native a Kotlin nativo en Android. Actualizamos todo el documento con las herramientas de prueba correspondientes: Jasmine y Karma para pruebas unitarias web, y JUnit con Espresso para las pruebas de la app Android nativa.
>
> Tercero, el cronograma de pruebas en formato de diagrama de Gantt, con las actividades distribuidas semana a semana desde el diseño de casos hasta el cierre de pruebas de seguridad e internacionalización.
>
> Y por último, consolidamos un documento de entregables con los enlaces a cada uno de estos documentos, a los dos tableros del proyecto —Jira y GitHub Projects— y a este mismo video."

*(Mostrar en pantalla: estrategia_pruebas_solventa.docx → sección de frameworks Angular/Kotlin, luego el Gantt en Excel, luego entregable_semana3.docx)*

---

## 4:35 – 5:00 | Cierre (Presentador 1 — Jazmin)

> "En resumen: completamos el formato narrativo de nuestros escenarios de calidad en Jira, corregimos un error que encontramos en el camino, y avanzamos con toda la estrategia y frameworks de pruebas para las próximas semanas. Muchas gracias."

*(Pantalla final: logo o nombre del proyecto + integrantes)*

---

## Notas de producción

- Tiempo total estimado: **4:55 – 5:05 min** (ajustar ritmo de lectura según ensayo).
- Si algún presentador no puede grabar, cualquier integrante puede leer su parte; el guion no depende de quién lo diga.
- Recordar mostrar en pantalla el link de cada documento, no solo nombrarlo.
- Grabar con la pestaña de Jira ya cargada en SOL-28 y SOL-44 para no perder tiempo buscando durante la grabación.
