# Historias de Usuario y Capacidad del Equipo — Solventa

**Universidad de los Andes · Maestría en Ingeniería de Software · MISW4501**
**Proyecto Integrador — Grupo 2**
**Versión 2.0 · 30 de agosto de 2026**

| Integrante | Rol |
|---|---|
| Jazmin Natalia Córdoba Puerto | Gerente — Usabilidad y entrega |
| Juan Esteban Mejía Izasa | Web front, integración API, pagos |
| Miguel Alejandro Gómez Alarcón | Arquitectura, Open Finance, KYC, rendimiento, seguridad |
| Angie Natalia Arandio Niño | Dominio, web back, móvil, pruebas unitarias |

---

## Control de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 19 ago 2026 | Versión inicial — 9 ASRs + catálogo de 20 historias con enlace a Jira |
| 1.1 | 20 ago 2026 | Se agrega frase narrativa a los 9 ASRs; corrección de ASR-3.3 |
| **2.0** | **30 ago 2026** | **Corrección por retroalimentación de semana 3: backlog descompuesto a 62 historias, detalle completo de cada historia en este documento, y evidencia del cálculo de capacidad del equipo** |

---

## 1. Correcciones aplicadas en esta versión

Esta versión responde a la retroalimentación recibida sobre la entrega de la semana 3, donde el documento de historias de usuario obtuvo 10 de 40 puntos.

| # | Observación recibida | Corrección aplicada | Sección |
|---|---|---|---|
| 1 | *"Se esperaba la lista completa de historias de usuario del proyecto, no solo 20"* | El backlog se descompuso de 20 a **62 historias**. Al revisar el tablero se confirmó el origen del problema: ocho de las veinte estaban tipadas en Jira como **Función**, no como Historia, y ninguna tenía historias hijas. Es decir, el backlog v1.1 tenía en realidad 12 historias y 8 funciones sin descomponer. Cada función se partió en historias verificables de forma independiente. Se identificó además una funcionalidad ausente del backlog —la autenticación web— y se agregó como épica y función propias. | §3, §4 |
| 2 | *"No se encontró la evidencia de cálculo de la capacidad del equipo"* | Se incorpora el cálculo completo de capacidad **dentro de este documento**, con la aritmética paso a paso. En la versión 1.1 el cálculo existía en un archivo auxiliar del repositorio (`documentos/semana-3/README.md`) pero no en el entregable. | §2 |
| 3 | *"Esto se refleja cuando se muestra un backlog de 152 puntos de historia con sólo 20 HUs"* | El promedio pasó de **7,6 SP/historia** a **3,7 SP/historia**. Ninguna historia supera 8 SP; ninguna historia funcional supera 5 SP. Se re-estimó de abajo hacia arriba: el backlog total subió de 152 SP a **229 SP**, lo que refleja alcance que antes estaba oculto dentro de historias demasiado gruesas. | §3, §4 |
| 4 | *(Detectado por el equipo)* Las historias no eran legibles sin abrir Jira | Cada historia se presenta ahora completa en este documento: enunciado *Como / Quiero / Para*, criterios de aceptación, estimación, prioridad, canal y ASR relacionado. | §4 |
| 5 | *(Detectado por el equipo)* El backlog excedía la capacidad sin un plan de alcance | Se define explícitamente qué entra en el **Proyecto Final 1** (76 SP) y qué se difiere al **Proyecto Final 2** (153 SP), con el criterio de corte documentado. | §5 |

---

## 2. Capacidad del equipo

### 2.1 Datos base

| Parámetro | Valor | Fuente |
|---|---|---|
| Integrantes del equipo | 4 personas | Acta de constitución |
| Dedicación comprometida por persona | 12 horas/semana | Acta de constitución |
| Duración total del proyecto | 8 semanas (3 ago – 27 sep 2026) | Cronograma del curso |
| Convención de estimación | 1 Story Point = 2 horas de trabajo efectivo | Definida por el equipo, semana 3 |

### 2.2 Cálculo paso a paso

**Paso 1 — Capacidad bruta semanal en horas**

```
4 personas  ×  12 horas/semana  =  48 horas/semana
```

**Paso 2 — Capacidad bruta semanal en story points**

```
48 horas/semana  ÷  2 horas/SP  =  24 SP/semana
```

**Paso 3 — Aplicar factor de carga real**

No todas las horas comprometidas son horas productivas de construcción. Se descuenta el tiempo dedicado a ceremonias, coordinación, revisión entre pares e imprevistos. El equipo adopta un **factor de carga del 80%**, valor conservador estándar para equipos que no han establecido todavía una velocidad histórica medida.

```
24 SP/semana  ×  0,80  =  19,2  ≈  19 SP/semana
```

> **Velocidad efectiva del equipo: 19 SP por semana.**

**Paso 4 — Capacidad total del Proyecto Final 1**

```
19 SP/semana  ×  8 semanas  =  152 SP
```

**Paso 5 — Capacidad realmente disponible para construcción**

Las semanas 1 a 4 se dedicaron a actividades de arquitectura y planeación (acta de constitución, EDT, visión de arquitectura, escenarios de calidad, estrategia de pruebas, diseño de experimentos), no a construir historias del backlog de producto. Esa capacidad ya está consumida.

```
Capacidad total del proyecto          8 semanas × 19 SP  =  152 SP
Consumida en semanas 1–4 (arquitectura)  4 semanas × 19 SP  =   76 SP
─────────────────────────────────────────────────────────────────────
Disponible para construcción (semanas 5–8)  4 semanas × 19 SP  =   76 SP
```

> **Capacidad disponible para construir historias: 76 SP.**

### 2.3 Distribución individual (semanas 5–8)

| Integrante | Horas comprometidas | SP equivalentes | Foco principal |
|---|---|---|---|
| Jazmin Córdoba | 48 h | 19 SP | Gerencia, usabilidad, entrega |
| Juan Mejía | 48 h | 19 SP | Web front, integración API, pagos |
| Miguel Gómez | 48 h | 19 SP | Arquitectura, Open Finance, KYC, rendimiento, seguridad |
| Angie Arandio | 48 h | 19 SP | Dominio, web back, móvil, pruebas unitarias |
| **Total bruto** | **192 h** | **96 SP** | |
| **Total con factor de carga 80%** | **154 h** | **76 SP** | |

### 2.4 Capacidad frente al backlog

| Concepto | Story Points | Historias |
|---|---|---|
| Backlog total del producto | 229 SP | 62 |
| Capacidad disponible (semanas 5–8) | 76 SP | — |
| **Diferencia** | **−153 SP** | — |

El backlog completo del producto **triplica** la capacidad disponible del equipo para el Proyecto Final 1. Esto no es un error de estimación: es la consecuencia de que Solventa es un producto de plataforma completo y el Proyecto Final 1 cubre solamente una parte del ciclo. La respuesta correcta no es reducir estimaciones sino **declarar el alcance explícitamente**, lo que se hace en la sección §5.

---

## 3. Estructura del backlog

### 3.1 Estructura jerárquica del backlog

El tablero del proyecto usa cuatro niveles de jerarquía: **Épica → Función → Historia → Subtarea**. La revisión del tablero durante esta corrección reveló el origen preciso del hallazgo: las ocho funcionalidades web y móvil que se presentaron como historias de usuario en la semana 3 están tipadas en Jira como **Función**, no como Historia, y ninguna tenía historias hijas. El backlog v1.1 contenía en realidad 12 historias y 8 funciones sin descomponer.

La corrección consiste en poblar el nivel que faltaba: 51 historias nuevas bajo las funciones existentes.

| Épica | Función | Historias | SP |
|---|---|---|---|
| **EP-01** Gestión de seguros Web (SOL-1) | FE-01 Cotización de seguros (SOL-3) | FE-01.1 a FE-01.6 | 15 |
| | FE-02 Suscripción y emisión (SOL-4) | FE-02.1 a FE-02.6 | 16 |
| | FE-03 Administración de pólizas (SOL-5) | FE-03.1 a FE-03.5 | 13 |
| **EP-02** Gestión de siniestros Web (SOL-2) | FE-04 Gestión y seguimiento de siniestros (SOL-6) | FE-04.1 a FE-04.5 | 15 |
| **EP-03** Acceso y gestión de pólizas Móvil (SOL-7) | FE-05 Autenticación biométrica y KYC (SOL-10) | FE-05.1 a FE-05.6 | 19 |
| | FE-06 Billetera de pólizas (SOL-11) | FE-06.1 a FE-06.5 | 12 |
| **EP-04** Siniestros y asistencia Móvil (SOL-8) | FE-07 Notificaciones y asistencia (SOL-13) | FE-07.1 a FE-07.4 | 10 |
| | FE-08 Reporte de siniestros con evidencia (SOL-12) | FE-08.1 a FE-08.5 | 12 |
| **EP-05** Portal de Socios y Distribución (SOL-30) | FE-09 Portal de socios distribuidores (SOL-31) | FE-09.1 a FE-09.5 | 16 |
| **EP-06** Acceso y autenticación Web *(nueva)* | FE-10 Autenticación web *(nueva)* | FE-10.1 a FE-10.4 | 9 |
| **EP-ARQ-01** Multi-región e internacionalización (SOL-15) | — | HU-ARQ-01, HU-ARQ-02 | 16 |
| **EP-ARQ-02** Cumplimiento regulatorio y privacidad (SOL-16) | — | HU-ARQ-03, HU-ARQ-04, HU-ARQ-11 | 21 |
| **EP-ARQ-03** Contenedores y plataforma de datos (SOL-25) | — | HU-ARQ-05, HU-ARQ-08, HU-ARQ-10 | 21 |
| **EP-ARQ-04** Escalabilidad y desempeño (SOL-27) | — | HU-ARQ-06, HU-ARQ-07, HU-ARQ-09 | 34 |
| **Total** | **10 funciones** | **62 historias** | **229** |

Las historias de arquitectura cuelgan directamente de su épica sin nivel de función intermedio, porque no representan funcionalidad de cara al usuario sino propiedades transversales del sistema.

### 3.2 Comparación con la versión anterior

| Métrica | v1.1 (semana 3) | v2.0 (esta versión) |
|---|---|---|
| Historias en el backlog | 20 | 62 |
| Story points totales | 152 SP | 229 SP |
| Promedio por historia | 7,6 SP | 3,7 SP |
| Historia más grande | 13 SP | 13 SP (solo arquitectura) |
| Historia funcional más grande | 8 SP | 5 SP |
| Historias > 8 SP | 2 | 2 (ambas de arquitectura) |
| Funcionalidades sin cubrir | Autenticación web | — |

### 3.3 Criterio de descomposición aplicado

Cada historia del backlog v2.0 cumple las siguientes reglas:

1. **Verificable de forma independiente** — se puede probar y demostrar sin depender de que otra historia de la misma épica esté terminada.
2. **Cabe en una semana de trabajo del equipo** — ninguna historia funcional supera 5 SP (10 horas).
3. **Entrega valor observable** — el resultado es visible para un usuario o para un sistema consumidor, no es una tarea técnica interna.
4. **Tiene criterios de aceptación explícitos** — mínimo tres, redactados de forma verificable.

Las historias de arquitectura (HU-ARQ) se mantienen sin descomponer porque representan atributos de calidad transversales cuya validación es un experimento único e indivisible: partir "tolerancia a fallos" en fragmentos produciría piezas que no se pueden verificar por separado contra su escenario de calidad.

---

## 4. Backlog detallado

> **Convención de prioridad:**
> **Alta** — entra en el alcance del Proyecto Final 1 (semanas 5–8).
> **Media** — se difiere al Proyecto Final 2; necesaria para el producto completo.
> **Baja** — se difiere al Proyecto Final 2; deseable, no crítica.

---

### EP-01 · Gestión de seguros Web (SOL-1) — Funciones FE-01, FE-02 y FE-03 · 17 historias · 44 SP

*Deriva de la historia original SOL-3 (Cotización de seguros en tiempo real, 8 SP) y SOL-4 (Suscripción y emisión de póliza, 8 SP).*

#### FE-01.1 — Iniciar cotización seleccionando ramo

**Como** cliente potencial que visita el portal web de Solventa,
**quiero** seleccionar el tipo de seguro que necesito e iniciar una cotización,
**para** comenzar el proceso de compra sin tener que registrarme previamente.

**Criterios de aceptación**
- El portal muestra los ramos activos disponibles (viaje, dispositivos, vida, paramétrico, protección de pagos) tomados del catálogo de configuración, no de una lista fija en código.
- Al seleccionar un ramo, el sistema crea una cotización en estado *borrador* con identificador único.
- La cotización se puede iniciar sin sesión iniciada; los datos se asocian a la sesión anónima.
- Si un ramo está desactivado en configuración, no aparece en el selector.

**SP:** 2 · **Prioridad:** Alta · **Canal:** Web · **ASR:** — · **Función padre:** SOL-3

---

#### FE-01.2 — Autorizar la consulta de datos por Open Finance

**Como** cliente potencial que está cotizando un seguro de vida hipotecario,
**quiero** autorizar de forma explícita que Solventa consulte mi información financiera vía Open Finance,
**para** obtener una prima ajustada a mi perfil real sin tener que cargar documentos manualmente.

**Criterios de aceptación**
- El sistema presenta el detalle de qué datos se consultarán, con qué finalidad y por cuánto tiempo, antes de solicitar la autorización.
- El cliente puede aceptar o rechazar; si rechaza, la cotización continúa por el flujo manual sin bloquearse.
- El consentimiento otorgado queda registrado con fecha, hora, alcance y versión del texto legal aceptado.
- El cliente puede revocar el consentimiento en cualquier momento y la revocación surte efecto en menos de 5 minutos.

**SP:** 3 · **Prioridad:** Alta · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** SOL-3

---

#### FE-01.3 — Ingresar los datos del bien o persona a asegurar

**Como** cliente potencial en proceso de cotización,
**quiero** ingresar la información del bien o de la persona que quiero asegurar,
**para** que el sistema calcule una prima acorde al riesgo real.

**Criterios de aceptación**
- El formulario se adapta al ramo seleccionado: los campos de un seguro de viaje son distintos de los de un seguro de vida hipotecario.
- Los campos obligatorios se validan en el cliente y en el servidor antes de permitir avanzar.
- Los datos ingresados se guardan de forma incremental: si el cliente abandona y regresa, no pierde lo escrito.
- Los campos de información personal se tokenizan antes de persistirse.

**SP:** 2 · **Prioridad:** Alta · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** SOL-3

---

#### FE-01.4 — Ver la prima calculada con su desglose

**Como** cliente potencial que completó los datos de cotización,
**quiero** ver la prima calculada junto con el desglose de cómo se compone,
**para** entender qué estoy pagando y decidir con información clara.

**Criterios de aceptación**
- El sistema devuelve la prima estimada en menos de 200 ms para el 95% de las solicitudes bajo carga normal.
- El desglose muestra prima pura, gastos de administración, impuestos y prima total.
- Si el motor de perfilamiento no responde dentro del tiempo límite, se muestra una prima basada en el perfil cacheado con una nota indicando que es una estimación preliminar.
- La prima calculada queda asociada a la cotización con marca de tiempo y vigencia.

**SP:** 3 · **Prioridad:** Alta · **Canal:** Web · **ASR:** ASR-1.1, ASR-1.2 · **Función padre:** SOL-3

---

#### FE-01.5 — Comparar planes de cobertura

**Como** cliente potencial que ya tiene una prima cotizada,
**quiero** comparar los distintos planes de cobertura disponibles para ese ramo,
**para** elegir el que mejor se ajusta a mi presupuesto y necesidad.

**Criterios de aceptación**
- Se muestran al menos tres niveles de cobertura con su prima correspondiente, lado a lado.
- La comparación indica de forma explícita qué incluye y qué excluye cada plan.
- Al cambiar de plan, la prima se recalcula sin recargar la página completa.
- La selección de plan queda registrada en la cotización.

**SP:** 3 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-3

---

#### FE-01.6 — Guardar, recuperar y vencer una cotización

**Como** cliente potencial que no quiere decidir en el momento,
**quiero** guardar mi cotización y recuperarla más tarde,
**para** tomarme el tiempo de decidir sin repetir todo el proceso.

**Criterios de aceptación**
- El cliente recibe por correo un enlace único para recuperar su cotización.
- La cotización tiene una vigencia configurable por ramo; al vencer, el enlace deja de permitir la compra y ofrece recotizar.
- Recuperar una cotización vigente restaura todos los datos ingresados y la prima calculada.
- Una cotización vencida conserva sus datos para recotización, pero recalcula la prima con las tarifas actuales.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-3

---

#### FE-02.1 — Completar los datos del tomador y de los asegurados

**Como** cliente que decidió comprar una póliza,
**quiero** completar los datos legales del tomador y de las personas aseguradas,
**para** que la póliza se emita a nombre correcto y con cobertura válida.

**Criterios de aceptación**
- El sistema solicita los datos mínimos exigidos por regulación: identificación, fecha de nacimiento, dirección y contacto.
- Se valida que el tomador sea mayor de edad y que la identificación tenga formato válido según el país.
- Se pueden agregar múltiples asegurados cuando el ramo lo permite.
- Todos los campos de información personal se tokenizan antes de persistirse.

**SP:** 2 · **Prioridad:** Alta · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** SOL-4

---

#### FE-02.2 — Cargar y validar los documentos requeridos

**Como** cliente en proceso de suscripción,
**quiero** cargar los documentos que exige el ramo que estoy contratando,
**para** completar los requisitos de suscripción sin ir a una oficina.

**Criterios de aceptación**
- El sistema indica qué documentos son obligatorios según el ramo y el monto asegurado.
- Se aceptan formatos PDF, JPG y PNG con un límite de tamaño definido; se rechaza cualquier otro formato.
- Cada documento cargado se almacena cifrado y queda asociado a la solicitud.
- Si un documento es ilegible o no corresponde al tipo esperado, el sistema lo marca y solicita reemplazo.

**SP:** 3 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-4

---

#### FE-02.3 — Firmar electrónicamente la solicitud

**Como** cliente que completó los datos y documentos,
**quiero** firmar electrónicamente la solicitud de seguro,
**para** formalizar la contratación con validez legal sin necesidad de firma física.

**Criterios de aceptación**
- El sistema presenta el documento completo de la solicitud antes de solicitar la firma.
- La firma se realiza mediante un mecanismo con validez legal en Colombia, con doble factor de verificación.
- El documento firmado queda con sello de tiempo y hash verificable.
- El cliente recibe copia del documento firmado en su correo.

**SP:** 3 · **Prioridad:** Media · **Canal:** Web · **ASR:** ASR-4.2 · **Función padre:** SOL-4

---

#### FE-02.4 — Pagar la primera prima

**Como** cliente que firmó la solicitud,
**quiero** pagar la primera prima con el medio de pago que prefiera,
**para** activar mi cobertura inmediatamente.

**Criterios de aceptación**
- Se ofrecen al menos dos medios de pago: tarjeta de crédito/débito y débito bancario (PSE).
- El sistema no almacena en ningún momento los datos completos de la tarjeta; se usa tokenización de la pasarela.
- Si el pago es rechazado, se informa el motivo y se permite reintentar con otro medio sin perder la solicitud.
- Al confirmarse el pago, se dispara automáticamente la emisión de la póliza.

**SP:** 3 · **Prioridad:** Alta · **Canal:** Web · **ASR:** ASR-2.1 · **Función padre:** SOL-4

---

#### FE-02.5 — Emitir la póliza y generar el certificado

**Como** cliente que pagó la primera prima,
**quiero** que mi póliza se emita y se genere el certificado correspondiente,
**para** tener la prueba formal de mi cobertura.

**Criterios de aceptación**
- La póliza se emite automáticamente en menos de 30 segundos tras confirmarse el pago.
- Se genera un certificado en PDF con número de póliza, vigencia, coberturas, exclusiones y datos del tomador.
- El certificado se firma digitalmente y se almacena con verificación de integridad.
- La emisión publica un evento de dominio que consumen los servicios de notificación y de administración de pólizas.

**SP:** 3 · **Prioridad:** Alta · **Canal:** Web · **ASR:** ASR-4.2 · **Función padre:** SOL-4

---

#### FE-02.6 — Recibir la póliza por correo y descargarla

**Como** cliente con una póliza recién emitida,
**quiero** recibir mi póliza por correo y poder descargarla desde el portal,
**para** tenerla disponible cuando la necesite.

**Criterios de aceptación**
- El correo con el certificado adjunto se envía dentro de los 5 minutos siguientes a la emisión.
- El certificado también queda disponible para descarga desde el portal, en la sección de pólizas del cliente.
- Si el envío del correo falla, el sistema reintenta y registra el fallo para seguimiento.
- La descarga desde el portal verifica la firma digital del documento antes de entregarlo.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** ASR-4.2 · **Función padre:** SOL-4

---

### EP-02 · Gestión de siniestros Web (SOL-2) — Función FE-04 · 5 historias · 15 SP

*Deriva de las historias originales SOL-5 (Administración de pólizas, 5 SP) y SOL-6 (Gestión y seguimiento de siniestros, 8 SP).*

#### FE-03.1 — Consultar el listado de pólizas

**Como** cliente asegurado,
**quiero** ver el listado de todas mis pólizas con su estado,
**para** saber qué coberturas tengo activas.

**Criterios de aceptación**
- Se listan las pólizas vigentes, vencidas y canceladas, diferenciadas visualmente por estado.
- Cada fila muestra número de póliza, ramo, vigencia y prima.
- El listado se pagina cuando supera veinte registros.
- Un cliente solo puede ver sus propias pólizas; el acceso se valida en el servidor contra la identidad de la sesión.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-5

---

#### FE-03.2 — Ver el detalle y las coberturas de una póliza

**Como** cliente asegurado,
**quiero** consultar el detalle completo de una póliza,
**para** conocer exactamente qué cubre y qué no.

**Criterios de aceptación**
- Se muestran coberturas contratadas, sumas aseguradas, deducibles y exclusiones.
- Se muestra el histórico de movimientos de la póliza (emisión, endosos, renovaciones).
- Se puede descargar el certificado vigente desde esta vista.
- El acceso a una póliza que no pertenece al cliente autenticado se rechaza.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-5

---

#### FE-03.3 — Renovar una póliza próxima a vencer

**Como** cliente con una póliza próxima a su vencimiento,
**quiero** renovarla desde el portal,
**para** mantener mi cobertura sin interrupción.

**Criterios de aceptación**
- El sistema notifica al cliente 30, 15 y 5 días antes del vencimiento.
- La renovación presenta la prima recalculada con las tarifas vigentes y explica cualquier variación respecto al periodo anterior.
- Al confirmar y pagar, se emite la póliza renovada sin corte de cobertura.
- Si el cliente no renueva, la póliza pasa a estado vencido en la fecha correspondiente.

**SP:** 3 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-5

---

#### FE-03.4 — Modificar datos de una póliza (endoso)

**Como** cliente asegurado cuya situación cambió,
**quiero** solicitar la modificación de los datos de mi póliza,
**para** que la cobertura refleje mi situación real.

**Criterios de aceptación**
- Se pueden solicitar cambios de datos de contacto, beneficiarios y suma asegurada.
- Los cambios que afectan el riesgo disparan un recálculo de prima y requieren aprobación.
- Cada endoso genera un documento nuevo, firmado, que no reemplaza sino que complementa el original.
- Toda modificación queda registrada en el histórico con autor, fecha y valores anterior y nuevo.

**SP:** 3 · **Prioridad:** Baja · **Canal:** Web · **ASR:** ASR-4.2 · **Función padre:** SOL-5

---

#### FE-03.5 — Cancelar una póliza y calcular la devolución

**Como** cliente asegurado que ya no necesita la cobertura,
**quiero** cancelar mi póliza y saber cuánto se me devuelve,
**para** dejar de pagar por algo que no uso.

**Criterios de aceptación**
- El sistema calcula la prima no devengada según el tiempo de cobertura efectivamente transcurrido.
- Se informa al cliente el monto exacto de devolución antes de confirmar la cancelación.
- La cancelación requiere confirmación explícita y queda registrada con fecha y motivo.
- La devolución se procesa por el mismo medio de pago usado originalmente.

**SP:** 3 · **Prioridad:** Baja · **Canal:** Web · **ASR:** — · **Función padre:** SOL-5

---

#### FE-04.1 — Registrar el aviso de un siniestro

**Como** cliente asegurado que sufrió un evento cubierto,
**quiero** reportar el siniestro desde el portal,
**para** iniciar el proceso de indemnización de inmediato.

**Criterios de aceptación**
- El cliente selecciona la póliza afectada de entre sus pólizas vigentes.
- Se capturan fecha, hora, lugar y descripción del evento.
- El sistema valida que la fecha del evento esté dentro de la vigencia de la póliza y rechaza el aviso si no lo está.
- Al registrarse, se genera un número de siniestro y se notifica al cliente.

**SP:** 3 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-6

---

#### FE-04.2 — Adjuntar la documentación de soporte del siniestro

**Como** cliente con un siniestro reportado,
**quiero** adjuntar los documentos que soportan mi reclamación,
**para** que se pueda evaluar y resolver.

**Criterios de aceptación**
- El sistema indica qué documentos requiere el tipo de siniestro reportado.
- Se pueden cargar documentos en varias sesiones, no necesariamente todos de una vez.
- Cada documento queda asociado al siniestro, cifrado y con registro de quién lo cargó y cuándo.
- El cliente ve cuáles documentos faltan por entregar.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-6

---

#### FE-04.3 — Consultar el estado de un siniestro

**Como** cliente con un siniestro en trámite,
**quiero** consultar en qué etapa está mi reclamación,
**para** saber qué esperar y qué debo hacer.

**Criterios de aceptación**
- Se muestra la etapa actual del siniestro y las etapas ya superadas, con sus fechas.
- Si el siniestro requiere una acción del cliente, se indica de forma destacada cuál es.
- El cliente recibe notificación ante cada cambio de estado.
- Se muestra el tiempo estimado de resolución según el tipo de siniestro.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** — · **Función padre:** SOL-6

---

#### FE-04.4 — Asignar y gestionar el perito

**Como** analista de siniestros de Solventa,
**quiero** asignar un perito al siniestro y hacer seguimiento a su informe,
**para** resolver la reclamación con sustento técnico.

**Criterios de aceptación**
- El analista puede asignar un perito de la red disponible según ubicación y especialidad.
- El perito recibe notificación con los datos del siniestro y accede a la documentación cargada.
- El perito carga su informe con conclusión y valor estimado del daño.
- El siniestro no puede pasar a liquidación sin informe de perito cuando el ramo lo exige.

**SP:** 3 · **Prioridad:** Baja · **Canal:** Web · **ASR:** — · **Función padre:** SOL-6

---

#### FE-04.5 — Aprobar o rechazar y liquidar la indemnización

**Como** analista de siniestros de Solventa,
**quiero** aprobar o rechazar la reclamación y liquidar la indemnización,
**para** cerrar el siniestro y pagar lo que corresponde.

**Criterios de aceptación**
- La decisión requiere motivación escrita, tanto para aprobación como para rechazo.
- La liquidación aplica deducible y límites de cobertura de forma automática según la póliza.
- Aprobada la liquidación, se dispara la orden de pago al cliente por el medio registrado.
- Toda decisión queda registrada de forma inmutable con el usuario que la tomó y su justificación.

**SP:** 5 · **Prioridad:** Baja · **Canal:** Web · **ASR:** ASR-4.2 · **Función padre:** SOL-6

---

### EP-06 · Acceso y autenticación Web (nueva) — Función FE-10 (nueva) · 4 historias · 9 SP

> **Épica nueva.** La autenticación web aparecía como recorrido crítico en la definición de alcance del proyecto pero no tenía ninguna historia asociada en el backlog v1.1. Se agrega aquí para cerrar esa brecha.

#### FE-10.1 — Registrarse en el portal con verificación de correo

**Como** cliente nuevo de Solventa,
**quiero** crear una cuenta en el portal,
**para** gestionar mis pólizas y siniestros en un solo lugar.

**Criterios de aceptación**
- El registro solicita correo, contraseña e identificación, y valida que el correo no esté ya registrado.
- La contraseña debe cumplir una política mínima de complejidad, verificada en el servidor.
- La cuenta permanece inactiva hasta que el cliente confirma su correo mediante un enlace con vencimiento.
- La contraseña se almacena con función de derivación de clave resistente a fuerza bruta, nunca en texto plano ni con hash simple.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** *(nueva)*

---

#### FE-10.2 — Iniciar sesión con segundo factor

**Como** cliente registrado,
**quiero** iniciar sesión de forma segura en el portal,
**para** acceder a mi información con la confianza de que nadie más puede hacerlo.

**Criterios de aceptación**
- El inicio de sesión exige un segundo factor cuando se detecta un dispositivo o ubicación no reconocidos.
- Tras cinco intentos fallidos consecutivos, la cuenta se bloquea temporalmente con retardo incremental.
- El mensaje de error no revela si el fallo fue por usuario inexistente o contraseña incorrecta.
- La sesión se establece con un token de vigencia limitada, transmitido y almacenado de forma segura.

**SP:** 3 · **Prioridad:** Alta · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** *(nueva)*

---

#### FE-10.3 — Recuperar el acceso a la cuenta

**Como** cliente registrado que olvidó su contraseña,
**quiero** restablecerla,
**para** recuperar el acceso a mi cuenta.

**Criterios de aceptación**
- El restablecimiento se solicita con el correo registrado y envía un enlace de un solo uso con vencimiento corto.
- El sistema responde igual exista o no la cuenta, para no revelar qué correos están registrados.
- Al restablecer la contraseña se invalidan todas las sesiones activas de esa cuenta.
- El cliente recibe notificación del cambio de contraseña en su correo.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** *(nueva)*

---

#### FE-10.4 — Cerrar sesión y expirar por inactividad

**Como** cliente que usa el portal desde un equipo compartido,
**quiero** que mi sesión se cierre al salir o tras un periodo de inactividad,
**para** que nadie acceda a mi información después de que termino.

**Criterios de aceptación**
- El cierre de sesión invalida el token en el servidor, no solamente en el navegador.
- La sesión expira automáticamente tras un periodo de inactividad configurable.
- Se avisa al cliente antes de expirar la sesión y se le ofrece extenderla.
- El cliente puede ver sus sesiones activas y cerrarlas remotamente.

**SP:** 2 · **Prioridad:** Media · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** *(nueva)*

---

### EP-03 · Acceso y gestión de pólizas Móvil (SOL-7) — Funciones FE-05 y FE-06 · 11 historias · 31 SP

*Deriva de la historia original SOL-10 (Autenticación biométrica y KYC/AML, 8 SP).*

#### FE-05.1 — Capturar el documento de identidad

**Como** cliente nuevo que se registra desde la app móvil,
**quiero** fotografiar mi documento de identidad y que los datos se extraigan solos,
**para** no tener que digitar todo manualmente.

**Criterios de aceptación**
- La app guía la captura del anverso y el reverso con marco de encuadre y validación de nitidez.
- Los datos se extraen automáticamente y se presentan al cliente para confirmación o corrección.
- Si la imagen no permite extraer los datos, se solicita repetir la captura indicando el motivo.
- Las imágenes del documento se transmiten cifradas y no quedan almacenadas en la galería del dispositivo.

**SP:** 3 · **Prioridad:** Alta · **Canal:** Móvil · **ASR:** ASR-4.1 · **Función padre:** SOL-10

---

#### FE-05.2 — Verificar la identidad con prueba de vida

**Como** cliente nuevo en proceso de onboarding,
**quiero** verificar que soy yo mediante una prueba de vida,
**para** completar mi registro sin ir a una oficina.

**Criterios de aceptación**
- La app solicita una secuencia de gestos aleatoria para evitar suplantación con fotografías o video pregrabado.
- El resultado compara el rostro capturado contra la fotografía del documento y devuelve un nivel de confianza.
- Si el nivel de confianza está por debajo del umbral, el caso se deriva a revisión manual en lugar de rechazarse automáticamente.
- Los datos biométricos se procesan y descartan; no se persisten en el dispositivo ni en el backend.

**SP:** 5 · **Prioridad:** Alta · **Canal:** Móvil · **ASR:** ASR-4.1 · **Función padre:** SOL-10

---

#### FE-05.3 — Validar contra listas restrictivas

**Como** oficial de cumplimiento de Solventa,
**quiero** que todo cliente nuevo se valide contra listas restrictivas y de personas expuestas políticamente,
**para** cumplir con la regulación de prevención de lavado de activos.

**Criterios de aceptación**
- La validación se ejecuta automáticamente al completar la verificación de identidad.
- Una coincidencia positiva bloquea el onboarding y genera un caso para revisión del oficial de cumplimiento.
- El resultado de la consulta queda registrado con fecha, fuente consultada y resultado.
- La consulta se reintenta con degradación controlada si el proveedor externo no responde, sin dejar pasar al cliente sin validar.

**SP:** 3 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-1.2 · **Función padre:** SOL-10

---

#### FE-05.4 — Otorgar consentimiento Open Finance desde el móvil

**Como** cliente que completó su onboarding en la app,
**quiero** autorizar la consulta de mi información financiera desde el móvil,
**para** acceder a primas personalizadas.

**Criterios de aceptación**
- Se presenta el mismo alcance y finalidad que en el canal web, con el mismo texto legal versionado.
- El consentimiento otorgado en móvil es válido en web y viceversa: es único por cliente, no por canal.
- El cliente puede consultar y revocar sus consentimientos activos desde la app.
- La revocación surte efecto en menos de 5 minutos en todos los canales.

**SP:** 3 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-4.1 · **Función padre:** SOL-10

---

#### FE-05.5 — Iniciar sesión con la biometría del dispositivo

**Como** cliente con onboarding completado,
**quiero** entrar a la app con mi huella o rostro,
**para** acceder rápido sin escribir contraseña cada vez.

**Criterios de aceptación**
- La app usa el mecanismo biométrico nativo del sistema operativo; no implementa comparación biométrica propia.
- Si la biometría falla o no está disponible, se ofrece el ingreso con contraseña como alternativa.
- La credencial que habilita el ingreso biométrico se almacena en el almacén seguro del dispositivo.
- Al cambiar la biometría registrada en el dispositivo, se invalida la credencial y se exige reautenticación completa.

**SP:** 3 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-4.1 · **Función padre:** SOL-10

---

#### FE-05.6 — Reintentar el onboarding tras un rechazo

**Como** cliente cuyo onboarding fue rechazado,
**quiero** entender por qué y poder intentarlo de nuevo,
**para** no quedarme sin poder usar el servicio.

**Criterios de aceptación**
- Se informa al cliente el motivo del rechazo en lenguaje claro, sin exponer detalles del mecanismo de detección.
- El cliente puede reintentar desde el paso que falló, sin repetir los pasos ya superados.
- Se limita el número de reintentos en una ventana de tiempo y se registra cada intento.
- Superado el límite, el caso se deriva a atención humana.

**SP:** 2 · **Prioridad:** Baja · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-10

---

### EP-04 · Siniestros y asistencia Móvil (SOL-8) — Funciones FE-07 y FE-08 · 9 historias · 22 SP

*Deriva de las historias originales SOL-11 (Billetera de pólizas, 5 SP), SOL-12 (Reporte de siniestros con evidencia, 5 SP) y SOL-13 (Notificaciones y asistencia geolocalizada, 5 SP).*

#### FE-06.1 — Ver las pólizas activas en la billetera

**Como** cliente asegurado con la app instalada,
**quiero** ver mis pólizas activas en la billetera,
**para** tenerlas siempre a la mano.

**Criterios de aceptación**
- La billetera lista las pólizas vigentes con número, ramo, vigencia y estado.
- Cada póliza muestra su certificado accesible con un toque.
- La billetera se actualiza automáticamente cuando se emite o modifica una póliza.
- Solo se muestran las pólizas del cliente autenticado en la sesión.

**SP:** 2 · **Prioridad:** Alta · **Canal:** Móvil · **ASR:** ASR-3.3 · **Función padre:** SOL-11

---

#### FE-06.2 — Consultar las pólizas sin conexión

**Como** cliente asegurado sin señal de datos,
**quiero** consultar mis pólizas de todos modos,
**para** poder mostrar mi cobertura cuando la necesito, aunque no tenga internet.

**Criterios de aceptación**
- El 100% de las consultas de póliza está disponible sin conexión una vez sincronizada la billetera.
- Los datos se almacenan cifrados en el dispositivo; no quedan accesibles a otras aplicaciones.
- Se muestra número, vigencia y coberturas sin requerir conexión.
- El almacenamiento local no conserva más información personal de la estrictamente necesaria para mostrar la póliza.

**SP:** 3 · **Prioridad:** Alta · **Canal:** Móvil · **ASR:** ASR-3.3 · **Función padre:** SOL-11

---

#### FE-06.3 — Descargar el certificado al dispositivo

**Como** cliente asegurado,
**quiero** guardar el certificado de mi póliza en el dispositivo,
**para** compartirlo cuando alguien me lo pida.

**Criterios de aceptación**
- El certificado se descarga en PDF y se puede compartir por los mecanismos nativos del sistema.
- Antes de entregarlo, la app verifica la firma digital del documento.
- La descarga funciona sin conexión si el certificado ya fue sincronizado.
- El certificado descargado conserva la firma digital verificable por terceros.

**SP:** 2 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-4.2 · **Función padre:** SOL-11

---

#### FE-06.4 — Sincronizar al recuperar conectividad

**Como** cliente que recupera la señal después de estar sin conexión,
**quiero** que mis datos se actualicen solos,
**para** ver siempre información vigente sin tener que hacer nada.

**Criterios de aceptación**
- La sincronización se dispara automáticamente al detectar conectividad, sin intervención del usuario.
- La sincronización completa toma 10 segundos o menos en condiciones normales de red.
- Las acciones realizadas sin conexión se envían al servidor en el orden en que se ejecutaron.
- Si un dato cambió en el servidor y en el dispositivo, prevalece el del servidor y se informa al cliente.

**SP:** 3 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-3.3 · **Función padre:** SOL-11

---

#### FE-06.5 — Ver alerta de datos desactualizados

**Como** cliente que lleva mucho tiempo sin conexión,
**quiero** saber si la información que veo puede estar desactualizada,
**para** no confiarme de datos viejos.

**Criterios de aceptación**
- Los datos almacenados localmente tienen una vigencia de 24 horas.
- Superada la vigencia, la app muestra un aviso visible indicando que los datos pueden no estar actualizados.
- El aviso no bloquea la consulta: el cliente sigue viendo su póliza.
- Al sincronizar, el aviso desaparece y se actualiza la marca de tiempo.

**SP:** 2 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-3.3 · **Función padre:** SOL-11

---

#### FE-08.1 — Reportar un siniestro con fotografías

**Como** cliente asegurado que acaba de sufrir un siniestro,
**quiero** reportarlo desde la app tomando fotos en el momento,
**para** dejar registro inmediato de lo ocurrido.

**Criterios de aceptación**
- La app permite tomar fotos desde la cámara o seleccionarlas de la galería, con un máximo definido por siniestro.
- Cada imagen se comprime antes de enviarse para no consumir datos en exceso.
- Las imágenes se transmiten cifradas y quedan asociadas al siniestro.
- Se muestra el progreso de carga y se puede continuar el reporte mientras las imágenes suben.

**SP:** 3 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-12

---

#### FE-08.2 — Adjuntar la ubicación del evento

**Como** cliente que reporta un siniestro,
**quiero** que se registre dónde ocurrió,
**para** que el análisis del caso sea más rápido y preciso.

**Criterios de aceptación**
- La app solicita permiso de ubicación explicando para qué se usará, y funciona aunque el cliente lo niegue.
- Si se otorga el permiso, se captura la ubicación en el momento del reporte con su precisión.
- El cliente puede corregir manualmente la ubicación si la detectada no es correcta.
- La ubicación queda asociada al siniestro y es visible para el analista.

**SP:** 2 · **Prioridad:** Baja · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-12

---

#### FE-08.3 — Describir el siniestro por voz o texto

**Como** cliente que reporta un siniestro en una situación de estrés,
**quiero** poder describir lo ocurrido hablando en lugar de escribiendo,
**para** reportar más rápido y con menos fricción.

**Criterios de aceptación**
- La app permite grabar una descripción por voz o escribirla en texto, a elección del cliente.
- La grabación de voz se transcribe automáticamente y el cliente puede corregir la transcripción.
- Tanto el audio como la transcripción quedan asociados al siniestro.
- Existe un límite de duración de la grabación, comunicado al cliente antes de grabar.

**SP:** 2 · **Prioridad:** Baja · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-12

---

#### FE-08.4 — Enviar el reporte en modo diferido

**Como** cliente que sufrió un siniestro en una zona sin señal,
**quiero** completar el reporte de todos modos y que se envíe cuando haya conexión,
**para** no perder el registro del momento en que ocurrió.

**Criterios de aceptación**
- El reporte completo, incluidas fotografías, se guarda cifrado en el dispositivo cuando no hay conexión.
- Se conserva la fecha y hora reales del evento, no la del momento del envío.
- Al recuperar conectividad, el reporte se envía automáticamente y el cliente recibe confirmación.
- Si el envío falla, se reintenta con espera creciente y se informa al cliente el estado.

**SP:** 3 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-3.3 · **Función padre:** SOL-12

---

#### FE-08.5 — Seguir el estado del siniestro desde el móvil

**Como** cliente con un siniestro reportado desde la app,
**quiero** ver en qué va mi reclamación,
**para** estar tranquilo y saber si debo hacer algo.

**Criterios de aceptación**
- La app muestra la etapa actual y el histórico de cambios de estado.
- Si se requiere una acción del cliente, se destaca y se puede resolver desde la app.
- Cada cambio de estado genera una notificación al dispositivo.
- El estado se consulta desde caché cuando no hay conexión, con marca de última actualización.

**SP:** 2 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** ASR-3.3 · **Función padre:** SOL-12

---

#### FE-07.1 — Recibir notificaciones de póliza y siniestro

**Como** cliente asegurado,
**quiero** recibir avisos de lo que pasa con mis pólizas y siniestros,
**para** enterarme sin tener que revisar la app.

**Criterios de aceptación**
- Se notifican al menos: emisión de póliza, próximo vencimiento, cambio de estado de siniestro y vencimiento de pago.
- La notificación no incluye información personal sensible en el texto visible en pantalla bloqueada.
- Al tocar la notificación, la app abre directamente en la pantalla correspondiente.
- Si el envío falla, el aviso queda igualmente disponible en el centro de notificaciones dentro de la app.

**SP:** 3 · **Prioridad:** Media · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-13

---

#### FE-07.2 — Configurar las preferencias de notificación

**Como** cliente que no quiere recibir todos los avisos,
**quiero** elegir qué notificaciones recibir,
**para** que la app no me moleste con lo que no me interesa.

**Criterios de aceptación**
- El cliente puede activar o desactivar cada categoría de notificación de forma independiente.
- Las notificaciones de carácter regulatorio u obligatorio no se pueden desactivar y se indica por qué.
- Las preferencias se sincronizan con el servidor y aplican a todos los dispositivos del cliente.
- El cambio de preferencias tiene efecto inmediato.

**SP:** 2 · **Prioridad:** Baja · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-13

---

#### FE-07.3 — Solicitar asistencia geolocalizada

**Como** cliente que necesita ayuda en el lugar de un siniestro,
**quiero** solicitar asistencia y que sepan dónde estoy,
**para** que me atiendan rápido sin tener que explicar mi ubicación.

**Criterios de aceptación**
- El cliente solicita asistencia indicando el tipo de ayuda que necesita.
- La solicitud incluye la ubicación actual si el cliente autorizó el permiso.
- Se muestra al cliente el tiempo estimado de llegada y el estado de la solicitud.
- La solicitud queda asociada a la póliza y al siniestro si existe uno abierto.

**SP:** 3 · **Prioridad:** Baja · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-13

---

#### FE-07.4 — Contactar a un asesor desde la app

**Como** cliente con una duda sobre mi póliza,
**quiero** comunicarme con un asesor desde la app,
**para** resolver sin tener que llamar por teléfono.

**Criterios de aceptación**
- La app ofrece al menos un canal de contacto directo con un asesor.
- La conversación llega con el contexto del cliente y su póliza ya cargado, sin que deba repetirlo.
- Se indica el horario de atención y, fuera de él, se ofrece dejar el mensaje para respuesta posterior.
- El histórico de conversaciones queda disponible para el cliente.

**SP:** 2 · **Prioridad:** Baja · **Canal:** Móvil · **ASR:** — · **Función padre:** SOL-13

---

### EP-05 · Portal de Socios y Distribución (SOL-30) — Función FE-09 · 5 historias · 16 SP

*Deriva de la historia original SOL-31 (Portal de socios distribuidores API B2B, 8 SP).*

#### FE-09.1 — Registrar un socio distribuidor

**Como** empresa interesada en distribuir seguros de Solventa,
**quiero** registrarme como socio,
**para** empezar a integrar la oferta en mis propios canales.

**Criterios de aceptación**
- El registro captura razón social, identificación tributaria, contacto técnico y tipo de integración deseada.
- La solicitud queda en estado pendiente hasta que Solventa la aprueba.
- Al aprobarse, se notifica al socio y se habilita el acceso al portal.
- Los datos del socio quedan asociados a un identificador único usado en toda la integración.

**SP:** 3 · **Prioridad:** Baja · **Canal:** Web · **ASR:** — · **Función padre:** SOL-31

---

#### FE-09.2 — Generar y rotar las llaves de API

**Como** socio distribuidor aprobado,
**quiero** obtener y poder rotar mis llaves de acceso a la API,
**para** integrarme de forma segura y responder ante un incidente sin cortar el servicio.

**Criterios de aceptación**
- Al aprobarse el socio, se generan automáticamente dos pares de llaves: uno de pruebas y uno de producción.
- La llave se muestra completa una sola vez, al generarse; después solo se muestra parcialmente.
- La rotación genera una llave nueva y mantiene la anterior válida durante un periodo de gracia configurable.
- Cada llave tiene registro de fecha de creación, último uso y estado.

**SP:** 3 · **Prioridad:** Baja · **Canal:** Web · **ASR:** ASR-4.1 · **Función padre:** SOL-31

---

#### FE-09.3 — Consultar el catálogo de ramos por API

**Como** sistema del socio distribuidor,
**quiero** consultar qué productos puedo ofrecer y con qué parámetros,
**para** presentarlos correctamente a mis usuarios.

**Criterios de aceptación**
- La API expone los ramos habilitados para ese socio con sus parámetros y coberturas.
- El catálogo refleja automáticamente los ramos nuevos configurados, sin requerir cambios en la API.
- La respuesta se entrega en el idioma y con la moneda del país del socio.
- Las llamadas sin llave válida se rechazan sin revelar información del catálogo.

**SP:** 2 · **Prioridad:** Baja · **Canal:** API · **ASR:** ASR-2.2 · **Función padre:** SOL-31

---

#### FE-09.4 — Monitorear el consumo y la cuota de API

**Como** socio distribuidor con una integración activa,
**quiero** ver cuántas llamadas he consumido y cuánta cuota me queda,
**para** planear mi operación y evitar quedarme sin servicio.

**Criterios de aceptación**
- El portal muestra el consumo del periodo actual y el límite contratado.
- Se notifica al socio al alcanzar umbrales de consumo definidos.
- Al superar la cuota, las llamadas se rechazan con un código y mensaje que lo explican claramente.
- El histórico de consumo está disponible por al menos los últimos doce meses.

**SP:** 3 · **Prioridad:** Baja · **Canal:** Web · **ASR:** — · **Función padre:** SOL-31

---

#### FE-09.5 — Cotizar y emitir de forma embebida por API

**Como** sistema del socio distribuidor,
**quiero** cotizar y emitir pólizas directamente por API,
**para** ofrecer el seguro dentro de mi propio flujo sin redirigir al usuario.

**Criterios de aceptación**
- La API permite cotizar enviando los datos del riesgo y devuelve prima y planes disponibles.
- La API permite emitir a partir de una cotización vigente, confirmando el pago.
- Cada operación queda trazada con el identificador del socio que la originó.
- Los tiempos de respuesta de la API cumplen el mismo objetivo de latencia que el canal propio.

**SP:** 5 · **Prioridad:** Baja · **Canal:** API · **ASR:** ASR-1.1 · **Función padre:** SOL-31

---

### Historias de arquitectura · 11 historias · 92 SP

Las historias de arquitectura se conservan sin descomponer. Cada una corresponde a un atributo de calidad transversal cuya validación es un experimento único: fragmentarlas produciría piezas no verificables de forma independiente contra su escenario de calidad. Su detalle completo, con la tabla SEI/Bass de seis campos y la frase narrativa del escenario, está en el documento de escenarios de calidad de la semana 3.

| ID | Historia | Jira | Épica | SP | Prioridad | ASR |
|---|---|---|---|---|---|---|
| HU-ARQ-01 | Parametrización multitenant y multirregión | SOL-21 | EP-ARQ-01 | 8 | Media | ASR-2.2 |
| HU-ARQ-02 | Abstracciones de pasarelas de pago (Adapter) | SOL-20 | EP-ARQ-01 | 8 | Media | ASR-2.1 |
| HU-ARQ-03 | Tokenización de PII y trazabilidad | SOL-23 | EP-ARQ-02 | 8 | **Alta** | ASR-4.1 |
| HU-ARQ-04 | Gestión de consentimientos Open Finance | SOL-22 | EP-ARQ-02 | 5 | Media | — |
| HU-ARQ-05 | Persistencia PostgreSQL + Redis | SOL-26 | EP-ARQ-03 | 5 | **Alta** | — |
| HU-ARQ-06 | Tolerancia a fallos y failover (Circuit Breaker) | SOL-29 | EP-ARQ-04 | 13 | **Alta** | ASR-3.1 |
| HU-ARQ-07 | Optimización de latencia del motor de scoring | SOL-28 | EP-ARQ-04 | 8 | **Alta** | ASR-1.1 |
| HU-ARQ-08 | Event Bus Kafka y degradación elegante | SOL-37 | EP-ARQ-03 | 8 | **Alta** | ASR-1.2 |
| HU-ARQ-09 | Autoescalado horizontal EKS y multi-AZ | SOL-43 | EP-ARQ-04 | 13 | Media | ASR-3.2 |
| HU-ARQ-10 | Sincronización offline del BFF móvil | SOL-44 | EP-ARQ-03 | 8 | Media | ASR-3.3 |
| HU-ARQ-11 | Integridad y auditoría de pólizas emitidas | SOL-45 | EP-ARQ-02 | 8 | Media | ASR-4.2 |
| | **Total** | | | **92** | | |

---

## 5. Priorización y alcance

### 5.1 Criterio de priorización

La prioridad de cada historia se asignó combinando tres criterios, en este orden:

1. **¿Valida un ASR que el proyecto debe demostrar?** Las historias de arquitectura ligadas a los escenarios de calidad que se experimentan en las semanas 5 y 6 tienen prioridad máxima: sin ellas no hay evidencia que presentar.
2. **¿Pertenece al recorrido crítico mínimo?** El recorrido *cotizar → emitir* en web y *onboarding → consultar póliza* en móvil es el mínimo que hace demostrable el prototipo. Sin ese recorrido completo no hay producto que mostrar.
3. **¿Es prerrequisito de algo de prioridad alta?** Una historia sin la cual otra de prioridad alta no puede completarse hereda su prioridad.

Las historias que no cumplen ninguno de los tres criterios se difieren al Proyecto Final 2.

### 5.2 Alcance del Proyecto Final 1 (76 SP)

**Historias de arquitectura — 42 SP**

| Orden | Historia | SP | Justificación |
|---|---|---|---|
| 1 | HU-ARQ-05 Persistencia PostgreSQL + Redis | 5 | Base sobre la que se montan los demás experimentos |
| 2 | HU-ARQ-07 Latencia del motor de scoring | 8 | Valida ASR-1.1 — experimento de la semana 5 |
| 3 | HU-ARQ-06 Tolerancia a fallos y failover | 13 | Valida ASR-3.1 — experimento de la semana 5 |
| 4 | HU-ARQ-03 Tokenización de PII | 8 | Valida ASR-4.1 — experimento de la semana 6 |
| 5 | HU-ARQ-08 Event Bus Kafka | 8 | Valida ASR-1.2 — degradación elegante |
| | **Subtotal** | **42** | |

**Historias funcionales — 34 SP**

| Orden | Historia | Canal | SP | Justificación |
|---|---|---|---|---|
| 6 | FE-10.2 Iniciar sesión con segundo factor | Web | 3 | Puerta de entrada de todo el recorrido web |
| 7 | FE-01.1 Iniciar cotización seleccionando ramo | Web | 2 | Inicio del recorrido crítico |
| 8 | FE-01.2 Autorizar consulta Open Finance | Web | 3 | Diferenciador del producto; habilita ASR-4.1 |
| 9 | FE-01.3 Ingresar datos del bien a asegurar | Web | 2 | Prerrequisito del cálculo de prima |
| 10 | FE-01.4 Ver la prima calculada con desglose | Web | 3 | Donde se observa ASR-1.1 y ASR-1.2 |
| 11 | FE-02.1 Completar datos del tomador | Web | 2 | Prerrequisito de la emisión |
| 12 | FE-02.4 Pagar la primera prima | Web | 3 | Cierra el recorrido de venta |
| 13 | FE-02.5 Emitir la póliza y generar certificado | Web | 3 | Resultado observable del recorrido web |
| 14 | FE-05.1 Capturar el documento de identidad | Móvil | 3 | Inicio del recorrido móvil |
| 15 | FE-05.2 Verificar identidad con prueba de vida | Móvil | 5 | Núcleo del onboarding móvil |
| 16 | FE-06.1 Ver pólizas activas en la billetera | Móvil | 2 | Resultado observable del recorrido móvil |
| 17 | FE-06.2 Consultar las pólizas sin conexión | Móvil | 3 | Donde se observa ASR-3.3 |
| | **Subtotal** | | **34** | |

| | SP |
|---|---|
| Historias de arquitectura | 42 |
| Historias funcionales | 34 |
| **Total alcance Proyecto Final 1** | **76** |
| **Capacidad disponible (semanas 5–8)** | **76** |
| **Holgura** | **0** |

> El alcance se ajustó deliberadamente a la capacidad exacta. No hay holgura, lo que significa que **cualquier historia adicional que entre desplaza a otra**. El equipo asume este compromiso de forma explícita: la respuesta ante un imprevisto será sacar alcance, no extender horas.

### 5.3 Diferido al Proyecto Final 2 (153 SP)

| Bloque | Historias | SP |
|---|---|---|
| Completar el recorrido de venta web (comparar planes, documentos, firma, entrega) | 5 | 13 |
| Administración de pólizas web (consulta, renovación, endosos, cancelación) | 5 | 13 |
| Gestión de siniestros web completa (aviso, soporte, peritaje, liquidación) | 5 | 15 |
| Autenticación web (registro, recuperación, gestión de sesiones) | 3 | 6 |
| Completar identidad móvil (listas restrictivas, consentimiento, biometría, reintentos) | 4 | 11 |
| Completar autogestión móvil (certificados, sincronización, siniestros, notificaciones) | 12 | 29 |
| Portal de socios distribuidores completo | 5 | 16 |
| Historias de arquitectura restantes | 6 | 50 |
| **Total** | **45** | **153** |

### 5.4 Distribución por sprint semanal

| Semana | Historias comprometidas | SP |
|---|---|---|
| Semana 5 (31 ago – 6 sep) | HU-ARQ-05, HU-ARQ-07, FE-10.2, FE-01.1 | 18 |
| Semana 6 (7 – 13 sep) | HU-ARQ-06, FE-01.2, FE-01.3 | 18 |
| Semana 7 (14 – 20 sep) | HU-ARQ-03, HU-ARQ-08, FE-01.4 | 19 |
| Semana 8 (21 – 27 sep) | FE-02.1, FE-02.4, FE-02.5, FE-05.1, FE-05.2, FE-06.1, FE-06.2 | 21 |
| **Total** | **17 historias** | **76** |

---

## 6. Trazabilidad entre escenarios de calidad e historias

Cada uno de los nueve escenarios de calidad definidos en la semana 3 se valida a través de al menos una historia de arquitectura y se observa en al menos una historia funcional.

| ASR | Atributo | Historia de arquitectura que lo implementa | Historia funcional donde se observa | En Proyecto 1 |
|---|---|---|---|---|
| ASR-1.1 | Latencia | HU-ARQ-07 (SOL-28) | FE-01.4 Ver prima calculada | Sí |
| ASR-1.2 | Latencia bajo degradación | HU-ARQ-08 (SOL-37) | FE-01.4 Ver prima calculada | Sí |
| ASR-2.1 | Modificabilidad | HU-ARQ-02 (SOL-20) | FE-02.4 Pagar la primera prima | No |
| ASR-2.2 | Modificabilidad | HU-ARQ-01 (SOL-21) | FE-01.1 Iniciar cotización · FE-09.3 Catálogo API | No |
| ASR-3.1 | Disponibilidad | HU-ARQ-06 (SOL-29) | FE-01.4 Ver prima calculada | Sí |
| ASR-3.2 | Disponibilidad multi-AZ | HU-ARQ-09 (SOL-43) | Transversal a todo el sistema | No |
| ASR-3.3 | Continuidad offline | HU-ARQ-10 (SOL-44) | FE-06.2 Consultar pólizas sin conexión | Parcial |
| ASR-4.1 | Confidencialidad | HU-ARQ-03 (SOL-23) | FE-01.2 Autorizar Open Finance | Sí |
| ASR-4.2 | Integridad | HU-ARQ-11 (SOL-45) | FE-02.5 Emitir póliza y certificado | No |

> ASR-3.3 se marca como parcial: la historia funcional que lo evidencia (FE-06.2) entra en el Proyecto Final 1, pero la historia de arquitectura que lo implementa por completo (HU-ARQ-10) se difiere. En el Proyecto Final 1 se demuestra la consulta sin conexión; la sincronización bidireccional completa queda para el Proyecto Final 2.

---

## 7. Anexo — Mapeo entre el backlog anterior y el actual

| Función en Jira | Tipo en Jira | SP v1.1 | Se descompone en | Historias | SP v2.0 |
|---|---|---|---|---|---|
| SOL-3 Cotización de seguros | Función | 8 | FE-01.1 a FE-01.6 | 6 | 15 |
| SOL-4 Suscripción y emisión de póliza | Función | 8 | FE-02.1 a FE-02.6 | 6 | 16 |
| SOL-5 Administración de pólizas | Función | 5 | FE-03.1 a FE-03.5 | 5 | 13 |
| SOL-6 Gestión y seguimiento de siniestros | Función | 8 | FE-04.1 a FE-04.5 | 5 | 15 |
| SOL-10 Autenticación biométrica y KYC/AML | Función | 8 | FE-05.1 a FE-05.6 | 6 | 19 |
| SOL-11 Billetera de pólizas móvil | Función | 5 | FE-06.1 a FE-06.5 | 5 | 12 |
| SOL-13 Notificaciones y asistencia | Función | 5 | FE-07.1 a FE-07.4 | 4 | 10 |
| SOL-12 Reporte de siniestros con evidencia | Función | 5 | FE-08.1 a FE-08.5 | 5 | 12 |
| SOL-31 Portal de socios distribuidores | Historia ⚠ | 8 | FE-09.1 a FE-09.5 | 5 | 16 |
| *(ausente en v1.1)* Autenticación web | — | — | FE-10.1 a FE-10.4 | 4 | 9 |
| SOL-20 a SOL-45 · HU-ARQ-01 a HU-ARQ-11 | Historia | 92 | *(sin descomponer)* | 11 | 92 |
| **Total** | | **152** | | **62** | **229** |

> ⚠ **SOL-31 está tipada como Historia cuando debería ser Función**, igual que sus ocho hermanas FE-01 a FE-08. Es la única funcionalidad de cara al usuario que cuelga directamente de su épica sin nivel de función intermedio. Se corrige junto con la carga de las historias nuevas.

**Tablero Jira del proyecto:** https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/boards
