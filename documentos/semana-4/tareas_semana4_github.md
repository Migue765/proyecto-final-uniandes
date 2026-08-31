# Tareas de la semana 4 — para cargar en GitHub Projects

**Proyecto:** Solventa · MISW4501 · Grupo 2
**Semana:** 4 (24–30 ago 2026)
**Rama:** `feature/semana-4`

> Cada bloque de abajo es una tarea. Copiar el título como nombre de la tarjeta y el cuerpo como descripción.
> Estado sugerido: `Hecho` salvo donde diga lo contrario.

---

## 1. Documentación

### T-01 · Consolidar la entrega en un documento único
**Estado:** Hecho
Unificar la hoja de trabajo, el índice de entregables y el guion del video en un solo `.docx`, con mapa de rúbrica al inicio que asocia cada ítem calificable con su sección. Evita repetir el error de la semana 3, donde el contenido existía pero fuera del entregable.
`documentos/semana-4/entregable_semana4.docx`

### T-02 · Redactar la sección de estilo de arquitectura
**Estado:** Hecho
Declarar y justificar la combinación de tres estilos: microservicios, capas y orientado a eventos. Incluir lo descartado (sin servidor, malla de servicios) con su razón. El curso nombra el estilo antes que las tácticas y no estaba documentado.
`entregable_semana4.docx` §2.1

### T-03 · Documentar los doce patrones de diseño
**Estado:** Hecho
Cada patrón con el problema que resuelve, el ASR que lo motiva, cómo se aplica en Solventa y la contrapartida que se acepta. Más ocho decisiones de arquitectura con sus alternativas descartadas.
`entregable_semana4.docx` §3, §4

### T-04 · Construir la matriz de trazabilidad
**Estado:** Hecho
Tabla patrón → tácticas → componentes → ASR → experimento, para los doce patrones. Evidencia que no hay patrones huérfanos ni ASR sin mecanismo asignado.
`entregable_semana4.docx` §3.4

### T-05 · Diseñar la propuesta de experimentos
**Estado:** Hecho
Tres experimentos con punto de sensibilidad, nivel de incertidumbre justificado, patrones y tácticas, componentes, conectores, medición, criterio de refutación y decisión alternativa. Más el criterio de cuántos experimentos y las cinco alternativas descartadas con su razón.
`entregable_semana4.docx` §5

### T-06 · Refinar la estrategia de pruebas
**Estado:** Hecho
Incorporar la prueba de arquitectura como nivel propio, distinto de la prueba de integración, y alinear los objetivos de cobertura con el backlog descompuesto.
`entregable_semana4.docx` §6

### T-07 · Documentar capacidad, esfuerzo y plan de trabajo
**Estado:** Hecho
Qué es un punto de historia y por qué se estima en tamaño relativo; cálculo de la capacidad paso a paso; capacidad por integrante; dónde se gasta en el Proyecto Final 1; compromiso contra los tres sprints del Proyecto Final 2.
`entregable_semana4.docx` §7.1 a §7.6

### T-08 · Declarar el margen para atrasos
**Estado:** Hecho
Tabla de sensibilidad con cuatro escenarios de velocidad, válvula de escape de siete historias con orden de corte declarado, y punto de recalibración obligatorio al cerrar el Sprint 1.
`entregable_semana4.docx` §7.7

### T-09 · Argumentar la viabilidad de construcción
**Estado:** Hecho
Declarar qué se construye realmente en el Proyecto Final 2 (cinco de siete servicios, tres de cinco adaptadores), por qué el estilo elegido no infla el costo, y cuál es el riesgo real de cronograma.
`entregable_semana4.docx` §7.8

---

## 2. Corrección de la semana 3

### T-10 · Descomponer el backlog de 20 a 62 historias
**Estado:** Hecho
Partir las nueve funciones en historias verificables de forma independiente. El promedio baja de 7,6 a 3,7 puntos por historia; ninguna historia funcional supera 5 puntos.
`historias_de_usuario_v2.docx` §4

### T-11 · Incorporar el cálculo de capacidad al entregable
**Estado:** Hecho
Trasladar el cálculo desde el README del repositorio al documento que se entrega, con la aritmética paso a paso. Era la observación literal del profesor.
`historias_de_usuario_v2.docx` §2

### T-12 · Re-estimar el backlog de abajo hacia arriba
**Estado:** Hecho
De 152 a 229 puntos, reflejando alcance que estaba oculto dentro de historias demasiado gruesas. Declarar el corte: 133 comprometidos, 96 diferidos.
`historias_de_usuario_v2.docx` §3, §5

### T-13 · Crear la épica y función de autenticación web
**Estado:** Hecho
La autenticación web figuraba como recorrido crítico en la definición de alcance pero no tenía ninguna historia asociada. Se crea la épica EP-06 (SOL-61) y la función FE-10 (SOL-62).

---

## 3. Diagramas

> Todos en `documentos/semana-4/diagramas/`, en formato `.drawio` editable, con su PNG exportado.

### T-14 · Diagrama de contexto
**Estado:** Hecho
Seis actores y cinco sistemas externos, distinguiendo cuáles se integran realmente y cuáles se simulan. Se retiran reaseguradoras e IoT/telemetría por no aparecer en ninguna historia comprometida.
`diagrama_contexto.drawio` · Figura 1

### T-15 · Vista funcional
**Estado:** Hecho
Cuatro capas más la plataforma de datos. Se corrigen los objetivos de latencia (p95 < 200 ms, no 250/400 ms), se agrega el servicio de Tokenización y el caché Redis, y se corrige el timeout de 700 a 150 ms.
`vista_funcional.drawio` · Figura 2

### T-16 · Vista funcional en notación UML componente-conector
**Estado:** Hecho
La misma estructura con puertos, interfaces provistas y requeridas, conectores de ensamblaje y conectores de mensajería. Nombra los ocho contratos del sistema. Es la notación que el curso espera para la vista funcional.
`vista_funcional_uml.drawio` · Figura 3

### T-17 · Vista de despliegue
**Estado:** Hecho
AWS multi-AZ activo-activo con región DR. Se reemplaza DynamoDB por ElastiCache Redis y PostgreSQL, porque contradecía la restricción de no usar NoSQL transaccional, y la réplica de lectura pasa a réplica con promoción automática.
`vista_despliegue.drawio` · Figura 4

### T-18 · Vista de información
**Estado:** Hecho
Entidades de dominio, clasificación de datos en tres niveles y almacenamiento. La clasificación es lo que vuelve verificable el ASR-4.1.
`vista_informacion.drawio` · Figura 5

### T-19 · Modelo de dominio
**Estado:** Hecho
Entidades con atributos y cardinalidades. Marca los campos tokenizados, incorpora el registro de auditoría como entidad de primera clase y Ramo como entidad de configuración.
`modelo_dominio.drawio` · Figura 6

### T-20 · Vista de asignación de patrones
**Estado:** Hecho
La arquitectura anotada con el patrón que gobierna cada componente y cada capa.
`vista_patrones.drawio` · Figura 7

### T-21 · Diagrama de estructura del camino de latencia
**Estado:** Hecho
Composición de Cache-Aside, Interruptor de circuito, Timeout y Mamparo operando encadenados, con las tres salidas válidas hacia una respuesta.
`patron_latencia.dot` · Figura 8

### T-22 · Diagrama de puertos y adaptadores
**Estado:** Hecho
Inversión de dependencias: ninguna flecha sale del núcleo. Es lo que convierte «cero cambios en el núcleo» de promesa en propiedad estructural.
`patron_puertos_adaptadores.dot` · Figura 9

### T-23 · Diagrama de la frontera de custodia de tokenización
**Estado:** Hecho
A la izquierda existe el dato original, a la derecha solo tokens sin valor.
`patron_tokenizacion.dot` · Figura 10

---

## 4. Tablero Jira

### T-24 · Cargar las 51 historias nuevas
**Estado:** Hecho
Crear las historias FE-01.1 a FE-10.4 con descripción Como/Quiero/Para, criterios de aceptación, story points y etiquetas. El tablero queda con 62 historias y 229 puntos.

### T-25 · Corregir la jerarquía y el tipado del tablero
**Estado:** Hecho
Convertir SOL-31 de Historia a Función, para que quede al mismo nivel que sus ocho hermanas FE-01 a FE-08.

### T-26 · Eliminar el doble conteo de story points
**Estado:** Hecho
Retirar la estimación de las diez Funciones. Como Función e Historia comparten nivel de jerarquía, si ambas llevaran puntos el tablero sumaría 298 donde el backlog real son 229.

### T-27 · Etiquetar el backlog
**Estado:** Hecho
Etiquetas de función (`FE-01` a `FE-10`), canal, prioridad, alcance y experimento (`EXP-01` a `EXP-03`), para poder filtrar el tablero.

### T-28 · Corregir la referencia a AsyncStorage en SOL-44
**Estado:** Hecho
El artefacto del ASR-3.3 decía AsyncStorage, que pertenece a React Native. Se reemplaza por Room con SQLCipher, acorde al stack Kotlin nativo adoptado el 19 de agosto.

### T-29 · Reetiquetar el alcance de todo el backlog
**Estado:** Hecho
Reemplazar las etiquetas `proyecto-1` / `proyecto-2` del encuadre anterior por `sprint-1`, `sprint-2`, `sprint-3` y `diferido`, en las 62 historias. Cada sprint queda lleno hasta su capacidad exacta: 38, 38 y 57 puntos. Se agrega además la etiqueta `valvula-escape` a las siete historias declaradas en §7.7 como primeras en salir ante un atraso.

---

## 5. Video

### T-30 · Escribir el guion de sustentación
**Estado:** Hecho
Siete bloques, diez minutos, cuatro presentadores, con lo que se dice y lo que se muestra en pantalla en cada momento.
`entregable_semana4.docx` §8.3

### T-31 · Grabar el video
**Estado:** PENDIENTE
Seguir el guion de §8.3. Verificar antes que las diez figuras se vean nítidas y que el tablero esté actualizado para el bloque 6.

### T-32 · Publicar el video y pegar el enlace
**Estado:** PENDIENTE
Subir con acceso por enlace y pegarlo en §8.1 y §10.1 del entregable.

### T-35 · Alinear el campo nativo de prioridad con las etiquetas
**Estado:** Hecho
El campo `priority` de Jira contradecía la etiqueta `prioridad-*` en 33 historias: las creadas hoy quedaron todas con el valor por defecto Medium y las de arquitectura con High heredado. Como Jira ordena el backlog por el campo nativo y no por la etiqueta, el tablero mostraba un orden que contradecía la priorización documentada en §7.5. Se alinean los dos.

---

## 6. Cierre de la entrega

### T-33 · Publicar los documentos y completar enlaces
**Estado:** PENDIENTE
Publicar `entregable_semana4.docx` e `historias_de_usuario_v2.docx`, y pegar sus enlaces en §10.1.

### T-34 · Abrir el pull request de la rama
**Estado:** PENDIENTE
Push de `feature/semana-4` y crear el PR manualmente:
`https://github.com/Migue765/proyecto-final-uniandes/compare/develop...feature/semana-4`

---

## Resumen

| Bloque | Tareas | Hechas | Pendientes |
|---|---|---|---|
| Documentación | T-01 a T-09 | 9 | 0 |
| Corrección semana 3 | T-10 a T-13 | 4 | 0 |
| Diagramas | T-14 a T-23 | 10 | 0 |
| Tablero Jira | T-24 a T-29, T-35 | 7 | 0 |
| Video | T-30 a T-32 | 1 | 2 |
| Cierre | T-33 a T-34 | 0 | 2 |
| **Total** | **35** | **31** | **4** |
