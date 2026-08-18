# Estrategia de Pruebas — Solventa
**Proyecto:** MISW4501 · Proyecto Final — Universidad de los Andes
**Versión:** 1.0.0 | **Fecha:** 16 de agosto de 2026

---

## SECCIÓN 1: Aplicación Bajo Pruebas

**Nombre:** Solventa
**Versión:** 1.0.0
**Descripción:**
Solventa es una aseguradora digital (insurtech) greenfield, nativa en la nube, construida sobre Open Finance y Open Data. Su propuesta de valor es permitir cotizar, suscribir, emitir y pagar siniestros de forma casi instantánea, embebiendo seguros directamente en el punto de necesidad del cliente (API-first / embedded insurance). Opera en los ramos de viaje, protección de dispositivos, microseguros de vida, seguro paramétrico y protección de pagos.

### Funcionalidades Core

| # | Componente | Descripción |
|---|---|---|
| 1 | Cotización y oferta (Web) | Motor de rating con señales Open Finance; cotización en tiempo real |
| 2 | Suscripción y emisión (Web) | Cobro, firma digital y emisión automática de póliza |
| 3 | Administración de pólizas (Web) | Ciclo de vida: alta, cambios, renovación, cancelación |
| 4 | Gestión de siniestros (Web) | Evaluación, aprobación, pago y enrutamiento a perito |
| 5 | Onboarding y biometría (Móvil) | Verificación de identidad, selfie/prueba de vida, autenticación biométrica |
| 6 | Billetera de pólizas (Móvil) | Visualización offline, sincronización y gestión de pólizas desde el celular |
| 7 | Reporte de siniestros (Móvil) | Captura de fotos/video con geoetiquetado |
| 8 | Notificaciones y asistencia (Móvil) | Push (pagos paramétricos, renovaciones), geolocalización de prestadores |
| 9 | Open Finance / Open Data | Integración con fuentes financieras y datos abiertos para perfilamiento |
| 10 | KYC / AML | Verificación de identidad y prevención de lavado de activos |
| 11 | Pagos y recaudo | Procesamiento de pagos con idempotencia y alta disponibilidad |
| 12 | Firma electrónica | Firma digital de pólizas y documentos |

**Diagrama de Arquitectura:** *(pendiente — se adjuntará en la visión de arquitectura)*
**Diagrama de Contexto:** *(pendiente — se adjuntará en la visión de arquitectura)*
**Modelo de Datos:** *(pendiente — se adjuntará en el modelo de dominio)*
**Modelo de GUI:** *(pendiente — se adjuntará con los prototipos de los clientes web y móvil)*

---

## SECCIÓN 2: Contexto de la Estrategia de Pruebas

### 2.1 Objetivos

| # | Objetivo |
|---|---|
| O1 | Verificar que los journeys críticos (cotización, suscripción, siniestro) funcionan correctamente en los canales web y móvil de extremo a extremo |
| O2 | Validar que las APIs de integración (Open Finance, KYC, Pagos) responden dentro de los umbrales de latencia definidos (p95 ≤ 120 ms por dependencia externa) |
| O3 | Comprobar que el sistema mantiene disponibilidad ≥ 99,97 % en los journeys críticos bajo carga variable |
| O4 | Detectar vulnerabilidades de seguridad en el manejo de PII, autenticación y endpoints expuestos, alineado con PCI-DSS y Ley 1581/2012 |
| O5 | Verificar la correcta presentación e internacionalización de la aplicación para los mercados objetivo (Colombia, México, Chile, Perú) |

**Duración:** 3 de agosto de 2026 – 30 de septiembre de 2026 (8 semanas)
El esfuerzo de pruebas se distribuye de forma incremental, alineado con los hitos de entrega del proyecto.

---

### 2.2 Presupuesto de Pruebas

#### Recursos Humanos

El equipo está conformado por 4 integrantes con formación en ingeniería de sistemas y experiencia en desarrollo de software y arquitectura:

| Integrante | Rol en pruebas | Horas/semana dedicadas a pruebas |
|---|---|---|
| Jazmin Natalia Córdoba | Coordinación de estrategia y pruebas de usabilidad | 12 h |
| Juan Esteban Mejía | Pruebas de integración y API (Postman) | 12 h |
| Miguel Alejandro Gómez | Pruebas de rendimiento (JMeter) y seguridad | 12 h |
| Angie Natalia Arandio | Pruebas funcionales / unitarias y de módulo | 12 h |
| **Total equipo** | | **48 h/semana** |

#### Recursos Computacionales

Las pruebas se ejecutarán sobre infraestructura en la nube AWS:

| Recurso | Detalle |
|---|---|
| AWS EC2 (t3.medium) | Ejecución de suites de JMeter para pruebas de rendimiento |
| AWS Device Farm | Pruebas automatizadas sobre dispositivos Android e iOS para el canal móvil |
| AWS CloudWatch | Monitoreo de métricas durante pruebas de carga |
| Laptops del equipo | Desarrollo y ejecución local de pruebas unitarias y de exploración |
| Postman Cloud (free tier) | Colecciones de pruebas API compartidas en equipo |

#### Recursos Económicos para contratación de servicios/personal

La estrategia se apoya exclusivamente en herramientas open source y niveles gratuitos de servicios cloud. No se contratarán servicios de outsourcing ni herramientas pagas.

| Herramienta | Costo | Uso |
|---|---|---|
| Apache JMeter | $0 (open source) | Pruebas de rendimiento |
| Postman (free tier) | $0 | Pruebas de API e integración |
| OWASP ZAP | $0 (open source) | Pruebas de seguridad |
| JUnit 5 | $0 (open source) | Pruebas unitarias y de módulo |
| AWS Free Tier / créditos académicos | $0 | Infraestructura cloud |

---

### 2.3 TNT — Técnicas, Niveles y Tipos de Pruebas

| ID | Tipo | Nivel | Técnica | Herramienta | Componentes a probar | Objetivo relacionado |
|---|---|---|---|---|---|---|
| T1 | Manual | Unitario | Caja blanca | JUnit 5 | Motor de rating, lógica de cotización, cálculo de primas, motor de siniestros | O1 |
| T2 | Automática | Módulo | Caja negra | JUnit 5 + Postman | APIs internas: cotización, suscripción, emisión de póliza | O1, O2 |
| T3 | Automática | Integración | Caja negra | Postman | Open Finance, KYC/AML, Pagos y recaudo, Firma electrónica | O2 |
| T4 | Automática | Sistema | Caja negra | JMeter | Motor de cotización (p95 ≤ 250 ms), suscripción (p95 ≤ 1,5 s), APIs de integración | O3 |
| T5 | Manual | Aceptación | Exploratoria | N/A | Flujo completo web (cotización → emisión), onboarding móvil, reporte de siniestro | O1 |
| T6 | Manual + Automática | Sistema | Caja negra | OWASP ZAP | Autenticación, manejo de PII, endpoints REST, consentimiento Open Finance | O4 |
| T7 | Manual | Sistema | Caja negra | N/A | Presentación en español (CO/MX/CL/PE), formatos de moneda, fechas y regulación local | O5 |

---

### 2.4 Distribución de Esfuerzo

**Total de horas disponibles:** 8 semanas × 48 h/semana = **384 horas**

| Tipo de prueba | Semanas activas | Horas asignadas | % del total | Responsable principal |
|---|---|---|---|---|
| Unitarias y de módulo (T1, T2) | 5, 6 | 96 h | 25 % | Angie Arandio |
| Integración / API (T3) | 6, 7, 8 | 96 h | 25 % | Juan Mejía |
| Rendimiento (T4) | 5, 6 | 72 h | 19 % | Miguel Gómez |
| Usabilidad / exploratoria (T5) | 6, 7 | 60 h | 16 % | Jazmin Córdoba |
| Seguridad (T6) | 7, 8 | 36 h | 9 % | Miguel Gómez |
| Internacionalización (T7) | 8 | 24 h | 6 % | Todo el equipo |
| **Total** | | **384 h** | **100 %** | |

#### Cronograma de pruebas por hito

| Semana | Fechas | Actividad de pruebas |
|---|---|---|
| 1–2 | 3–16 ago | Diseño de casos de prueba, configuración de entornos (AWS, Postman, JMeter) |
| 3–4 | 17–30 ago | Pruebas de hipótesis de calidad; diseño y ejecución de experimentos de arquitectura (rendimiento) |
| 5 | 31 ago–6 sep | Ejecución de pruebas de rendimiento con JMeter; análisis de resultados |
| 6 | 7–13 sep | Pruebas unitarias, de módulo e integración del cliente web |
| 7 | 14–20 sep | Pruebas funcionales del cliente móvil; pruebas de usabilidad y seguridad |
| 8 | 21–30 sep | Pruebas de integración final (Open Finance, pagos, KYC); internacionalización; cierre |
