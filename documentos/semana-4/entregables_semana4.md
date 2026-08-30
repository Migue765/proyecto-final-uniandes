---portada
institucion: Universidad de los Andes
facultad: Facultad de Ingeniería · Departamento de Ingeniería de Sistemas y Computación
programa: Maestría en Ingeniería de Software
curso: MISW4501 — Proyecto Final
titulo: Entregables
subtitulo: Índice de documentos, tableros y evidencias de la semana
proyecto: Proyecto Solventa — Aseguradora digital sobre Finanzas Abiertas
entrega: Entrega — Semana 4
grupo: Grupo 2
integrantes: Jazmin Natalia Córdoba Puerto ~ Gerente del proyecto — Usabilidad y entrega|Juan Esteban Mejía Izasa ~ Web front, integración de APIs y pagos|Miguel Alejandro Gómez Alarcón ~ Arquitectura, Open Finance, KYC, rendimiento y seguridad|Angie Natalia Arandio Niño ~ Dominio, web back, móvil y pruebas unitarias
fecha: Bogotá D.C. · 30 de agosto de 2026
---

## 1. Qué contiene esta entrega

Esta entrega tiene dos partes. La primera es el entregable propio de la semana 4. La segunda es la corrección del documento de historias de usuario de la semana 3, que obtuvo 10 de 40 puntos.

| # | Entregable | Documento | Rúbrica |
|---|---|---|---|
| 1 | Hoja de trabajo: modelos de arquitectura, patrones detallados y experimentos | `hoja_trabajo_semana4.docx` | 70 pts |
| 2 | Refinamiento de la estrategia de pruebas | `hoja_trabajo_semana4.docx` · §6 | 10 pts |
| 3 | Plan de trabajo y tablero | `hoja_trabajo_semana4.docx` · §7 + tablero Jira | 10 pts |
| 4 | Video con evidencias | Enlace en §4 de este documento | 10 pts |
| — | **Corrección semana 3:** historias de usuario y capacidad del equipo | `historias_de_usuario_v2.docx` | *Reentrega* |

---

## 2. Documentos

| # | Documento | Contenido | Enlace |
|---|---|---|---|
| 1 | hoja_trabajo_semana4.docx | Vista funcional, de despliegue y de información · 12 patrones con su razonamiento frente a cada ASR · 8 decisiones de arquitectura con alternativas descartadas · 8 experimentos que cubren los 9 ASR, cada uno con punto de sensibilidad, nivel de incertidumbre justificado, patrones y tácticas, componentes, conectores, criterio de refutación y ficha de tecnología · refinamiento de la estrategia de pruebas · plan por sprint | *(pegar enlace)* |
| 2 | historias_de_usuario_v2.docx | Backlog completo de 62 historias con criterios de aceptación · cálculo de capacidad del equipo paso a paso · priorización y corte de alcance entre Proyecto Final 1 y 2 · trazabilidad entre ASR e historias | *(pegar enlace)* |

Ambos documentos están además versionados en el repositorio, en `documentos/semana-4/`, junto con las fuentes de los diagramas en formato `.dot`, que se regeneran con un solo comando.

---

## 3. Tableros

| Tablero | Qué muestra | Enlace |
|---|---|---|
| Jira — Tablero | Épicas, funciones e historias con estimación, prioridad y etiquetas de alcance | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/boards |
| Jira — Backlog | Backlog descompuesto de 62 historias, ordenado por prioridad | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/backlog |
| Repositorio | Documentos, diagramas y registro de cambios de la entrega | https://github.com/Migue765/proyecto-final-uniandes |

**Cómo leer el tablero.** Las historias nuevas llevan etiquetas que permiten filtrarlas:

| Etiqueta | Significado |
|---|---|
| `FE-01` … `FE-10` | Función a la que pertenece la historia. Función e Historia son tipos del mismo nivel en Jira, así que la relación se expresa con esta etiqueta y no con la jerarquía |
| `funcion` | Marca los diez ítems de tipo Función |
| `EXP-01` … `EXP-08` | Historia de arquitectura que lleva ese experimento |
| `canal-web` · `canal-movil` · `canal-api` | Canal donde se implementa |
| `prioridad-alta` · `prioridad-media` · `prioridad-baja` | Prioridad asignada |
| `proyecto-1` · `proyecto-2` | Si entra en el alcance del Proyecto Final 1 o se difiere al 2 |

Para ver únicamente el alcance comprometido de este proyecto, filtrar por `proyecto-1`.

---

## 4. Video de sustentación

| Descripción | Duración | Enlace |
|---|---|---|
| Correcciones de la semana 3, modelos de arquitectura, patrones, propuesta de experimentos y tablero | 8 min | *(pegar enlace)* |

El guion completo, con el reparto por presentador y la lista de verificación previa a grabar, está en `guion_video_semana4.md`.

---

## 5. Correcciones aplicadas a la entrega de la semana 3

| Observación recibida | Corrección | Dónde verificarla |
|---|---|---|
| *"Se esperaba la lista completa de historias de usuario del proyecto, no solo 20"* | El backlog se descompuso de 20 a 62 historias. La revisión del tablero mostró que ocho de las veinte estaban tipadas en Jira como Función y no como Historia, sin ninguna historia hija: el backlog tenía en realidad 12 historias y 8 funciones sin descomponer. El promedio pasó de 7,6 a 3,7 SP por historia | `historias_de_usuario_v2.docx` §3 y §4 · tablero Jira |
| *"No se encontró la evidencia de cálculo de la capacidad del equipo"* | El cálculo está ahora dentro del entregable, con la aritmética paso a paso: 4 personas × 12 h = 48 h/semana → 24 SP → factor de carga 80% → 19 SP/semana → 76 SP disponibles para las semanas 5 a 8. En la versión anterior el cálculo existía, pero en un archivo del repositorio que no se entregaba | `historias_de_usuario_v2.docx` §2 |
| *"Un backlog de 152 puntos de historia con sólo 20 HUs... le puede generar dolores de cabeza en el proyecto final 2"* | Se re-estimó de abajo hacia arriba: el backlog subió a 229 SP, reflejando alcance que estaba oculto dentro de historias demasiado gruesas. Frente a una capacidad de 76 SP, se declara explícitamente qué entra en el Proyecto Final 1 y qué se difiere al Proyecto Final 2 | `historias_de_usuario_v2.docx` §5 |

Se detectaron además dos cosas por cuenta propia al hacer la corrección: la autenticación web era un recorrido crítico sin ninguna historia asociada, y se agregó como épica y función nuevas; y las historias no eran legibles sin abrir Jira, por lo que ahora cada una aparece completa dentro del documento.

---

## 6. Pendientes antes de enviar

- [ ] Publicar los dos documentos y pegar sus enlaces en la tabla de §2
- [ ] Grabar el video siguiendo el guion y pegar su enlace en §4
- [ ] Verificar que el tablero de Jira se vea con las 62 historias antes de grabar el bloque del video que lo muestra
