---portada
institucion: Solventa
facultad: Aseguradora digital sobre Finanzas Abiertas y Datos Abiertos
programa: Dirección de Arquitectura
curso: Plan de Construcción
titulo: Capacidad, Esfuerzo y Plan de Trabajo
subtitulo: Cálculo de capacidad del equipo, alcance comprometido y seguimiento en Jira
proyecto: Versión 1.0
entrega: Documento de planeación
grupo: Equipo de arquitectura
integrantes: Jazmin Natalia Córdoba Puerto ~ Gerencia de proyecto, usabilidad y entrega|Juan Esteban Mejía Izasa ~ Web front, integración de APIs y pagos|Miguel Alejandro Gómez Alarcón ~ Arquitectura, Open Finance, KYC, rendimiento y seguridad|Angie Natalia Arandio Niño ~ Dominio, web back, móvil y pruebas
fecha: Bogotá D.C. · 30 de agosto de 2026
---

## 1. Cálculo de la capacidad del equipo

**Paso 1 — Horas comprometidas por semana**

Cada integrante se comprometió en el acta de constitución a dedicar 12 horas semanales al proyecto.

```
4 integrantes  ×  12 horas/semana  =  48 horas/semana
```

**Paso 2 — Convertir esas horas a puntos**

El equipo adopta la equivalencia de referencia de **1 punto de historia = 2 horas de trabajo efectivo**, que se recalibrará al cerrar el primer sprint cuando exista velocidad medida.

```
48 horas/semana  ÷  2 horas/punto  =  24 puntos/semana  (capacidad bruta)
```

**Paso 3 — Descontar el trabajo que no es construcción**

No todas las horas comprometidas producen historias terminadas. Se van en reuniones de coordinación, revisión entre pares, preparación de entregas e imprevistos. El equipo aplica un factor de carga del 80 %, valor conservador estándar para equipos sin velocidad histórica medida.

```
24 puntos/semana  ×  0,80  =  19,2  ≈  19 puntos/semana
```

> **Velocidad efectiva del equipo: 19 puntos de historia por semana.**

**Paso 4 — Capacidad total de cada fase**

```
Fase de diseño        8 semanas × 19 pts  =  152 pts
Fase de construcción  7 semanas × 19 pts  =  133 pts
```

**Paso 5 — Capacidad realmente disponible para construir historias**

Los 152 puntos de la fase de diseño se consumen íntegramente en acta de constitución, EDT, visión de arquitectura, escenarios de calidad, estrategia de pruebas, diseño y ejecución de experimentos y experiencia de usuario. Ese trabajo es necesario, pero no produce historias del backlog de producto. Las historias se construyen en los tres sprints de la fase de construcción, que son de dos, dos y tres semanas.

```
Fase de diseño — arquitectura, experimentos y UX      152 pts
Fase de construcción — construcción del producto      133 pts
────────────────────────────────────────────────────────────
Sprint 1   2 semanas × 19 pts   =   38 pts
Sprint 2   2 semanas × 19 pts   =   38 pts
Sprint 3   3 semanas × 19 pts   =   57 pts
```

> **Capacidad disponible para construir historias: 133 puntos.**

## 2. Capacidad por integrante

La misma cuenta, vista por persona, muestra cuánto aporta cada integrante a esos 133 puntos:

| Paso | Cálculo | Resultado |
|---|---|---|
| Horas comprometidas por persona en la fase de construcción | 12 h/semana × 7 semanas | 84 h |
| Convertidas a puntos | 84 h ÷ 2 h/punto | 42 pts brutos |
| Aplicando el factor de carga del 80 % | 42 pts × 0,80 | 33 pts efectivos |
| Multiplicado por los cuatro integrantes | 33 pts × 4 personas | 133 pts |

| Integrante | Horas comprometidas | Puntos efectivos | Foco según su rol |
|---|---|---|---|
| Jazmin Córdoba | 84 h | 33 pts | Gerencia, usabilidad y entrega |
| Juan Mejía | 84 h | 33 pts | Web front, integración de APIs y pagos |
| Miguel Gómez | 84 h | 33 pts | Arquitectura, Open Finance, KYC, rendimiento y seguridad |
| Angie Arandio | 84 h | 34 pts | Dominio, web back, móvil y pruebas unitarias |
| **Total** | **336 h** | **133 pts** | |

Las 336 horas brutas equivalen a 269 horas efectivas tras el factor de carga; las 67 horas restantes son las que absorben coordinación, revisión e imprevistos.

## 3. Capacidad de la fase de construcción y compromiso del backlog

La fase de construcción tiene una estructura fija que no se negocia: **tres sprints, de dos, dos y tres semanas**, siete semanas en total. Con la misma velocidad de 19 puntos por semana:

```
19 puntos/semana  ×  7 semanas  =  133 puntos
```

| Sprint | Duración | Capacidad |
|---|---|---|
| Sprint 1 | 2 semanas | 38 pts |
| Sprint 2 | 2 semanas | 38 pts |
| Sprint 3 | 3 semanas | 57 pts |
| **Total** | **7 semanas** | **133 pts** |

**El backlog frente a esa capacidad:**

| Concepto | Puntos | Historias |
|---|---|---|
| Backlog total del producto | 229 | 62 |
| Capacidad de la fase de construcción | 133 | — |
| **Comprometido** | **133** | **30** |
| **Diferido a una fase posterior** | **96** | **32** |

El backlog completo no cabe: sobran 96 puntos. Forzar los números para que cuadraran habría exigido reducir las estimaciones a poco más de la mitad, produciendo un plan que se incumple en el primer sprint. La respuesta correcta es **declarar el alcance**: se comprometen las 30 historias de mayor prioridad, que suman exactamente los 133 puntos disponibles.

**Criterio de priorización, en este orden:**

1. **¿Valida un ASR que el sistema debe demostrar?** Las historias de arquitectura ligadas a los escenarios de calidad entran primero: sin ellas no hay atributos de calidad, solo funcionalidad.
2. **¿Pertenece al recorrido crítico?** *Cotizar → suscribir → emitir* en web y *onboarding → consultar póliza* en móvil es lo que hace que el producto exista.
3. **¿Es prerrequisito de algo ya comprometido?** Hereda la prioridad de aquello que habilita.

| Bloque comprometido | Historias | Puntos |
|---|---|---|
| Historias de arquitectura que sostienen los ASR *(las once menos HU-ARQ-09, cuyo escenario multi-zona se difiere)* | 10 | 79 |
| Cotización web completa — FE-01 | 6 | 15 |
| Suscripción y emisión web — FE-02, recorrido mínimo | 4 | 11 |
| Autenticación web completa — FE-10 | 4 | 9 |
| Onboarding móvil — FE-05, recorrido mínimo | 3 | 11 |
| Billetera móvil — FE-06, incluida la consulta sin conexión | 3 | 8 |
| **Total comprometido** | **30** | **133** |
| **Capacidad de la fase de construcción** | | **133** |
| **Holgura** | | **0** |

> El alcance se ajustó a la capacidad exacta y el equipo asume ese compromiso de forma explícita: **ante un imprevisto se saca alcance, no se extienden horas.** Cualquier historia adicional que entre desplaza a otra.

Las 32 historias diferidas —administración de pólizas, gestión completa de siniestros, portal de socios y la mayor parte de la autogestión móvil— quedan documentadas, estimadas y priorizadas en el backlog. Su detalle está en el tablero.

## 4. Distribución por sprint de la fase de construcción

| Sprint | Semanas | Foco | Historias | Puntos |
|---|---|---|---|---|
| **Sprint 1** | 2 | Cimientos de arquitectura: persistencia, caché, bus de eventos, tokenización y consentimientos. Autenticación web completa | 9 | 38 |
| **Sprint 2** | 2 | Recorrido de cotización completo con Open Finance. Latencia del scoring y tolerancia a fallos | 9 | 38 |
| **Sprint 3** | 3 | Suscripción, emisión y pagos. Onboarding móvil y billetera. Parametrización, pasarelas, integridad y sincronización offline | 12 | 57 |
| **Total** | **7** | | **30** | **133** |

Cada sprint se llena hasta su capacidad exacta. El detalle historia por historia está en el tablero: filtrando por `sprint-1`, `sprint-2` o `sprint-3` se obtiene el contenido de cada uno, y por `valvula-escape` las siete historias declaradas en §5.

El Sprint 1 concentra historias de arquitectura porque son prerrequisito de todo lo demás: sin persistencia, caché y bus no hay dónde apoyar los recorridos funcionales. El Sprint 3 es más largo y absorbe más puntos, lo que da margen para el ajuste que casi siempre exige el cierre.

## 5. Margen para atrasos: sensibilidad de la velocidad y válvula de escape

Los 133 puntos comprometidos equivalen a la capacidad completa del equipo. Eso significa que **no hay holgura por construcción**, y conviene ser explícito sobre qué protege ese plan y qué no.

**Lo que el factor de carga sí cubre.** El descuento del 20 % aplicado en §2 absorbe el trabajo conocido que no produce historias terminadas: ceremonias, coordinación y revisión entre pares. Sobre las siete semanas son unos 38 puntos de esfuerzo ya descontados. Pero eso es **overhead previsible**, no reserva para lo imprevisto.

**Lo que no cubre.** La velocidad de 19 puntos por semana descansa en dos supuestos que el equipo todavía no ha medido: que un punto de historia equivale a dos horas, y que el factor de carga real es del 80 %. Si cualquiera se corre, la capacidad cae:

| Escenario | Supuestos | Velocidad | Capacidad en 7 semanas |
|---|---|---|---|
| **A** — el plan actual | 2 h/SP · factor 80 % | 19 SP/semana | **133 SP** |
| **B** — factor más conservador | 2 h/SP · factor 70 % | 17 SP/semana | 119 SP |
| **C** — subestimamos el tamaño | 2,5 h/SP · factor 80 % | 15 SP/semana | 107 SP |
| **D** — ambos a la vez | 2,5 h/SP · factor 70 % | 13 SP/semana | **94 SP** |

El compromiso de 133 puntos corresponde al escenario A, que es el más favorable de los cuatro. Tres factores empujan hacia abajo: tres tecnologías con familiaridad baja declarada por el equipo —bus de eventos, gestión de llaves y almacenamiento inmutable—, el rendimiento típicamente menor del primer sprint mientras se montan entornos, y el tamaño de las dos historias de arquitectura de 13 puntos.

**La válvula de escape.** En lugar de descubrir el desvío a mitad del Sprint 3, el equipo declara **desde ahora** qué historias salen primero si la velocidad medida resulta menor que la estimada. Son 18 puntos, el 13,5 % del compromiso, elegidas porque su ausencia degrada la experiencia sin romper ningún recorrido crítico ni dejar un ASR sin cobertura:

| Orden de corte | Historia | SP | Qué se pierde si sale |
|---|---|---|---|
| 1 | FE-01.5 Comparar planes de cobertura | 3 | El cliente ve una sola opción de cobertura en lugar de tres; el recorrido de cotización sigue completo |
| 2 | FE-10.4 Cerrar sesión y expirar por inactividad | 2 | La sesión expira solo del lado del navegador; el ingreso sigue protegido |
| 3 | FE-01.6 Guardar y recuperar cotización | 2 | La cotización no se puede retomar más tarde; se recotiza |
| 4 | FE-10.3 Recuperar el acceso a la cuenta | 2 | El restablecimiento de contraseña pasa a soporte manual |
| 5 | FE-05.5 Iniciar sesión con biometría del dispositivo | 3 | El acceso móvil queda solo con contraseña; el onboarding biométrico no se toca |
| 6 | FE-06.4 Sincronizar al recuperar conectividad | 3 | La sincronización pasa a ser manual; la consulta sin conexión del ASR-3.3 se conserva |
| 7 | FE-02.3 Firmar electrónicamente la solicitud | 3 | La firma se simula en el prototipo; la emisión y su firma digital se conservan |
| | **Total** | **18** | |

Ninguna de las siete es prerrequisito de otra historia comprometida, y ninguna deja un escenario de calidad sin mecanismo. Se cortan **en ese orden**, no por conveniencia del momento.

**Punto de recalibración obligatorio.** Al cerrar el Sprint 1 el equipo tendrá por primera vez velocidad *medida* en lugar de estimada. Ese es el momento de revisar la equivalencia de dos horas por punto y el factor de carga, y de decidir si se activa la válvula. La regla que el equipo adopta:

```
Si la velocidad medida del Sprint 1  <  16 SP/semana
   →  se activa la válvula de escape en el orden declarado
   →  se recalcula el compromiso de los Sprints 2 y 3 con la velocidad real
```

Este mecanismo es la respuesta concreta al riesgo de sobrecompromiso que suele aparecer en la fase de construcción: ese riesgo no se elimina declarando que no existe, sino decidiendo de antemano qué se sacrifica y con qué criterio.

## 6. Viabilidad: ¿es construible esta arquitectura?

La arquitectura definida en la fase de diseño no es un documento que se archiva: es el compromiso que el equipo debe cumplir en la fase de construcción, y la revisión de arquitectura validará que el código se conforme a ella. Por eso el equipo verificó explícitamente que lo propuesto sea construible en siete semanas por cuatro personas a doce horas semanales.

**Lo que efectivamente se construye:**

| Elemento de la arquitectura | Se construye en la fase de construcción | Justificación |
|---|---|---|
| Servicios del núcleo | **5 de 7** | Cotización & Rating, Perfilamiento, Suscripción & Emisión, Pólizas y Tokenización. Siniestros y Consentimientos quedan como interfaz mínima, porque sus recorridos completos están diferidos |
| Capa BFF | **2 de 2** | El BFF Móvil es indispensable para el ASR-3.3; el BFF Web para el recorrido de cotización |
| Adaptadores externos | **3 de 5** | Open Finance, pasarela de pagos y KYC. Open Data y firma electrónica se simulan, porque su integración real no aporta información arquitectural nueva |
| Plataforma de datos | **Completa** | PostgreSQL, Redis y Kafka son prerrequisito de tres ASR |
| Despliegue multi-zona | **No** | Se despliega en una sola zona. El ASR-3.2 se difiere: su validación exige infraestructura con costo que el presupuesto de esta fase no cubre |

**Por qué el estilo elegido no infla el costo de construcción.** La preocupación razonable con microservicios es que cinco servicios cuesten cinco veces más que uno. En este caso no ocurre, por tres razones: los cinco comparten un mismo esqueleto de proyecto y las mismas bibliotecas de acceso a datos y de cliente HTTP; se ejecutan con un único archivo de composición de contenedores, de modo que levantar el sistema completo es un comando; y la frontera entre ellos coincide con la frontera de responsabilidad entre integrantes, lo que reduce el costo de coordinación en lugar de aumentarlo.

**Riesgo declarado.** El elemento de mayor riesgo de cronograma no es la arquitectura sino el cliente móvil nativo, seguido de las pruebas. Son las dos actividades que la experiencia del equipo identifica como principales causas de retraso. Por eso el onboarding móvil y la billetera entran en el Sprint 3, con las tres semanas de mayor holgura, y por eso la estrategia de pruebas se revisa en cada entrega en lugar de darse por cerrada.

## 7. Calendario de la fase de diseño

| Periodo | Foco | Estado |
|---|---|---|
| 3–9 ago | Acta de constitución y backlog inicial | Completada |
| 10–16 ago | Visión de arquitectura, EDT y estrategia de pruebas | Completada |
| 17–23 ago | Escenarios de calidad, backlog de historias y definición de frameworks | Completada |
| 24–30 ago | Arquitectura detallada y diseño de experimentos | En curso |
| 31 ago – 6 sep | Cierre de la arquitectura y versión final del diseño de experimentos · wireframes | Planificada |
| 7–13 sep | Construcción y ejecución de EXP-01 y EXP-02 · mockups del recorrido web | Planificada |
| 14–20 sep | Ejecución de EXP-02 y EXP-03 · prototipo móvil | Planificada |
| 21–27 sep | Análisis de resultados, ajuste del diseño y preparación del backlog del Sprint 1 | Planificada |

## 8. Tablero

El tablero del proyecto en Jira refleja el backlog descompuesto, con épicas, estimación en puntos de historia, prioridad y la asociación de cada historia de arquitectura con su ASR y su experimento.

| Tablero | Qué muestra | Enlace |
|---|---|---|
| Jira — Tablero | Épicas, funciones e historias con estimación, prioridad y etiquetas | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/boards |
| Jira — Backlog | Backlog descompuesto de 62 historias ordenado por prioridad | https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/backlog |

## 9. Estado del tablero tras la actualización

| Tipo de incidencia | Cantidad | Puntos de historia |
|---|---|---|
| Épica | 10 | — |
| Función | 10 | — |
| Historia | 62 | 229 |
| Subtarea | 25 | — |

El tablero es un proyecto gestionado por el equipo, cuya jerarquía tiene tres niveles: **Épica** en el nivel superior; **Función** e **Historia** como tipos hermanos en el nivel intermedio; y **Subtarea** en el inferior. Como Función e Historia comparten nivel, una historia no puede colgar de una función: ambas cuelgan de la épica, y la relación entre ellas se expresa con etiquetas. Por la misma razón la estimación vive únicamente en las historias; si las funciones también la llevaran, el tablero sumaría dos veces el mismo trabajo y mostraría 298 puntos donde el backlog real son 229.

## 10. Cómo leer el tablero

| Etiqueta | Significado |
|---|---|
| `FE-01` … `FE-10` | Función a la que pertenece la historia |
| `funcion` | Marca los diez ítems de tipo Función |
| `arquitectura` | Marca las once historias de arquitectura |
| `canal-web` · `canal-movil` · `canal-api` | Canal donde se implementa |
| `prioridad-alta` · `prioridad-media` · `prioridad-baja` | **Importancia intrínseca** de la historia, que es el criterio con que se hizo el corte de alcance de §3 |
| `sprint-1` · `sprint-2` · `sprint-3` | Sprint de la fase de construcción en que se construye |
| `diferido` | Fuera del alcance comprometido |
| `valvula-escape` | Historia declarada como primera en salir ante un atraso (§5) |
| `EXP-01` … `EXP-03` | Historia de arquitectura que lleva ese experimento |

**Dos dimensiones distintas, y conviene no confundirlas.** El campo nativo *Prioridad* de Jira y la etiqueta `prioridad-*` no significan lo mismo, y por eso no siempre coinciden:

| | Qué expresa | Para qué sirve |
|---|---|---|
| Campo nativo **Prioridad** | **Orden de ejecución** | Ordenar el backlog reproduce la secuencia real de construcción |
| Etiqueta `prioridad-*` | **Importancia intrínseca** | Es el criterio con que se decidió qué entra y qué se difiere |

El campo nativo usa los cinco niveles así:

| Prioridad | Agrupa | Historias |
|---|---|---|
| Highest | Sprint 1 — los cimientos de arquitectura y el acceso web | 9 |
| High | Sprint 2 — el recorrido de cotización, latencia y tolerancia a fallos | 9 |
| Medium | Sprint 3 — emisión, pagos y móvil | 12 |
| Low | Diferidas de importancia media | 16 |
| Lowest | Diferidas de importancia baja | 16 |

Una historia puede ser importante y aun así quedar en `Lowest`: significa que no se construye en el alcance comprometido, no que no importe. Por eso ambas dimensiones se conservan por separado.

Para ver el alcance comprometido, filtrar por `sprint-1`, `sprint-2` y `sprint-3`: devuelve 30 historias y 133 puntos, exactamente el compromiso de §3. Filtrando por `diferido` se obtienen las 32 restantes con sus 96 puntos.
