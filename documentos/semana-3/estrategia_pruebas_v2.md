# Estrategia de Pruebas — Solventa v2.0
**Proyecto:** MISW4501 · Proyecto Final — Universidad de los Andes
**Versión:** 2.0.0 | **Fecha:** 19 de agosto de 2026 | **Semana:** 3

---

## SECCIÓN 1: Aplicación Bajo Pruebas

**Nombre:** Solventa
**Versión:** 1.0.0 (MVP)
**Descripción:**
Solventa es una aseguradora digital (insurtech) greenfield, nativa en la nube, construida sobre Open Finance y Open Data. Su propuesta de valor es permitir cotizar, suscribir, emitir y gestionar siniestros de forma casi instantánea, embebiendo seguros directamente en el punto de necesidad del cliente (API-first / embedded insurance). Opera en los ramos de viaje, protección de dispositivos, microseguros de vida, seguro paramétrico y protección de pagos.

### Stack tecnológico confirmado

| Capa | Tecnología |
|---|---|
| Backend (microservicios) | Python 3.11 + Flask |
| Frontend web | React 18 + TypeScript |
| Frontend móvil | React Native 0.74 |
| Base de datos relacional | PostgreSQL 15 |
| Caché y sesiones | Redis 7 |
| Mensajería asíncrona | Apache Kafka 3.x (KRaft, Docker local) / Amazon MSK (prod) |
| Infraestructura cloud | AWS EKS + RDS + MSK + S3 + KMS |
| Orquestación local | Docker Compose |
| IaC | Terraform |

### Componentes funcionales bajo prueba

| # | Componente | Canal | Descripción |
|---|---|---|---|
| 1 | Cotización y oferta | Web | Motor de rating con señales Open Finance; cotización en tiempo real |
| 2 | Suscripción y emisión | Web | Cobro, firma digital y emisión automática de póliza |
| 3 | Administración de pólizas | Web | Ciclo de vida: alta, cambios, renovación, cancelación |
| 4 | Gestión de siniestros | Web | Evaluación, aprobación, pago y enrutamiento a perito |
| 5 | Autenticación biométrica | Móvil | Verificación de identidad, selfie/prueba de vida, KYC/AML |
| 6 | Billetera de pólizas | Móvil | Visualización offline, sincronización y gestión desde el celular |
| 7 | Reporte de siniestros | Móvil | Captura de fotos/video con geoetiquetado |
| 8 | Notificaciones y asistencia | Móvil | Push notifications, geolocalización de prestadores |
| 9 | Open Finance / Open Data | API | Integración con fuentes financieras para perfilamiento |
| 10 | KYC / AML | API | Verificación de identidad y prevención de lavado de activos |
| 11 | Pagos y recaudo | API | Procesamiento de pagos con idempotencia y alta disponibilidad |
| 12 | Event Bus Kafka | Infra | Eventos de dominio: cotización, siniestros, pagos |

---

## SECCIÓN 2: Contexto de la Estrategia de Pruebas

### 2.1 Objetivos

| # | Objetivo |
|---|---|
| O1 | Verificar que los journeys críticos (cotización, suscripción, siniestro) funcionan correctamente en los canales web y móvil de extremo a extremo |
| O2 | Validar que las APIs de integración (Open Finance, KYC, Pagos) responden dentro de los umbrales de latencia definidos en los ASR (p95 ≤ 200 ms) |
| O3 | Comprobar que el sistema mantiene disponibilidad ≥ 99,9% en journeys críticos bajo carga variable y ante fallos de componentes (Redis, zona AWS) |
| O4 | Detectar vulnerabilidades de seguridad en el manejo de PII, autenticación y endpoints expuestos, alineado con PCI-DSS y Ley 1581/2012 |
| O5 | Verificar la correcta presentación e internacionalización para los mercados objetivo (Colombia, México, Chile, Perú) |
| O6 | Validar las hipótesis de calidad definidas en los ASR mediante experimentos controlados |

**Duración:** 3 de agosto de 2026 – 23 de septiembre de 2026 (7 semanas)

---

### 2.2 Presupuesto de Pruebas

#### Recursos Humanos

| Integrante | Rol en pruebas | Horas/semana |
|---|---|---|
| Jazmin Natalia Córdoba | Coordinación de estrategia y pruebas de usabilidad | 12 h |
| Juan Esteban Mejía | Pruebas de integración y API (Postman) | 12 h |
| Miguel Alejandro Gómez | Pruebas de rendimiento (JMeter) y seguridad | 12 h |
| Angie Natalia Arandio | Pruebas funcionales / unitarias | 12 h |
| **Total** | | **48 h/semana · 336 h totales (7 semanas)** |

#### Recursos Computacionales

| Recurso | Uso |
|---|---|
| Docker Compose (local) | Entorno de desarrollo integrado: Flask + PostgreSQL + Redis + Kafka KRaft |
| AWS EC2 (t3.medium) | Ejecución de suites JMeter para pruebas de rendimiento |
| AWS Device Farm | Pruebas automatizadas en dispositivos Android e iOS (React Native) |
| AWS CloudWatch | Monitoreo de métricas durante pruebas de carga |
| Laptops del equipo | Desarrollo y ejecución local de pruebas unitarias |
| Postman Cloud (free tier) | Colecciones de pruebas API compartidas |

#### Recursos Económicos

| Herramienta | Costo | Uso |
|---|---|---|
| pytest + pytest-cov | $0 (open source) | Pruebas unitarias e integración backend (Python/Flask) |
| Jest + React Testing Library | $0 (open source) | Pruebas unitarias y de componentes web (React) |
| Jest + Detox | $0 (open source) | Pruebas E2E móvil (React Native) |
| Apache JMeter | $0 (open source) | Pruebas de rendimiento |
| Postman (free tier) | $0 | Pruebas de API e integración |
| OWASP ZAP | $0 (open source) | Pruebas de seguridad |
| AWS Free Tier / créditos académicos | $0 | Infraestructura cloud |

---

## SECCIÓN 3: Frameworks y Ambientes de Prueba

### 3.1 Framework de pruebas por capa

| Capa | Framework principal | Framework E2E / integración | Cobertura mínima |
|---|---|---|---|
| **Backend Python/Flask** | pytest 8 + pytest-cov | Postman (Newman CLI) | 80% líneas |
| **Frontend web (React)** | Jest 29 + React Testing Library | Playwright | 70% líneas |
| **Frontend móvil (React Native)** | Jest 29 + React Native Testing Library | Detox 20 | 70% líneas |
| **Rendimiento** | Apache JMeter 5.6 | — | p95 por ASR |
| **Seguridad** | OWASP ZAP 2.14 | — | 0 vulnerabilidades críticas |

### 3.2 Framework componente web — React 18

- **Pruebas unitarias:** Jest + React Testing Library para componentes, hooks y lógica de negocio
- **Pruebas de integración:** Playwright para flujos completos (cotización → emisión)
- **Internacionalización:** `react-i18next` con pruebas de renderizado por locale (es-CO, es-MX, es-CL, es-PE)
- **Accesibilidad:** `@testing-library/jest-dom` + axe-core (WCAG 2.1 AA)
- **Cobertura:** Jest con `--coverage`, umbral mínimo 70%

```bash
# Ejecutar pruebas unitarias web
npm test -- --coverage --watchAll=false

# Ejecutar E2E con Playwright
npx playwright test --project=chromium
```

### 3.3 Framework componente móvil — React Native 0.74

- **Pruebas unitarias:** Jest + React Native Testing Library para componentes y stores
- **Pruebas E2E:** Detox 20 en emulador Android (API 34) y simulador iOS 17
- **Pruebas offline:** Detox con simulación de red desconectada (modo avión) para validar ASR-3.1
- **Internacionalización:** `react-i18next` con pruebas por locale igual que web
- **Cobertura:** Jest con `--coverage`, umbral mínimo 70%

```bash
# Ejecutar pruebas unitarias móvil
npx jest --coverage

# Ejecutar E2E Detox en Android
detox test --configuration android.emu.debug
```

### 3.4 Framework backend — Python 3.11 / Flask

- **Pruebas unitarias:** pytest con fixtures para cada servicio (cotización, siniestros, pagos, emisión)
- **Pruebas de integración:** pytest + testcontainers-python (PostgreSQL + Redis en Docker)
- **Pruebas de contrato API:** Postman Collections exportadas + Newman CLI en CI
- **Cobertura:** pytest-cov, umbral mínimo 80%

```bash
# Ejecutar pruebas unitarias backend
pytest --cov=src --cov-report=html tests/

# Ejecutar pruebas de integración con testcontainers
pytest tests/integration/ -v
```

### 3.5 Ambiente cloud para backend y herramientas de test

| Ambiente | Descripción | Herramientas |
|---|---|---|
| **Local (dev)** | Docker Compose: Flask + PostgreSQL + Redis + Kafka KRaft | pytest, Jest, Detox emulador |
| **Staging (AWS)** | EKS (2 nodos t3.medium) + RDS PostgreSQL + ElastiCache Redis + MSK | Postman Newman, JMeter agente |
| **Rendimiento** | EC2 t3.medium dedicado para carga JMeter + CloudWatch métricas | JMeter 5.6 distributed mode |
| **Seguridad** | Instancia aislada igual a staging | OWASP ZAP en modo activo |
| **Móvil** | AWS Device Farm (Android API 34 + iOS 17) | Detox test runner |

---

## SECCIÓN 4: Técnicas, Niveles y Tipos de Pruebas (TNT)

| ID | Tipo | Nivel | Técnica | Herramienta | Componentes | Objetivo |
|---|---|---|---|---|---|---|
| T1 | Automática | Unitario | Caja blanca | pytest / Jest | Motor de rating, lógica cotización, cálculo de primas, motor siniestros, componentes React/RN | O1 |
| T2 | Automática | Módulo | Caja negra | pytest + testcontainers / Postman | APIs internas: cotización, suscripción, emisión de póliza | O1, O2 |
| T3 | Automática | Integración | Caja negra | Postman (Newman) | Open Finance, KYC/AML, Pagos y recaudo, Firma electrónica, Kafka Event Bus | O2 |
| T4 | Automática | Sistema | Caja negra | JMeter | Motor de cotización (ASR-1.1/1.2), autoscaling (ASR-3.2), failover Redis (ASR-3.1) | O3, O6 |
| T5 | Manual | Aceptación | Exploratoria | Playwright / Detox | Flujo completo web (cotización → emisión), onboarding móvil, reporte de siniestro | O1 |
| T6 | Automática | Sistema | Caja negra | OWASP ZAP | Autenticación, manejo PII, endpoints REST, consentimiento Open Finance | O4 |
| T7 | Manual | Sistema | Caja negra | — | Presentación en español (CO/MX/CL/PE), formatos de moneda, fechas y regulación local | O5 |
| T8 | Automática | Hipótesis | Caja negra | JMeter + scripts Python | Experimentos de validación de ASR (ver Sección 5) | O6 |

---

## SECCIÓN 5: Pruebas de Hipótesis por ASR

Cada ASR tiene un experimento de prueba controlado que valida la hipótesis de calidad. Los experimentos se ejecutan en semanas 4–5.

### ASR-1.1 — Scoring en carga normal

| Campo | Detalle |
|---|---|
| **Hipótesis** | El 95% de solicitudes de cotización responden en < 200ms con 500 req/min |
| **Herramienta** | JMeter 5.6 |
| **Configuración** | 500 hilos concurrentes, ramp-up 60s, duración 10 min |
| **Endpoint** | `POST /api/v1/cotizaciones` |
| **Criterio de éxito** | p95 < 200ms, p99 < 400ms, 0% errores |
| **Historia relacionada** | SOL-28 (HU-ARQ-07) |

### ASR-1.2 — Scoring con proveedor externo degradado

| Campo | Detalle |
|---|---|
| **Hipótesis** | Con Open Finance respondiendo > 700ms, el sistema usa caché y responde en < 200ms sin pérdida de solicitudes |
| **Herramienta** | JMeter + WireMock (simula latencia Open Finance) |
| **Configuración** | 5.000 req concurrentes; WireMock introduce delay de 800ms en el mock de Open Finance |
| **Criterio de éxito** | p95 < 200ms usando caché; 0% solicitudes perdidas por timeout |
| **Historia relacionada** | SOL-37 (HU-ARQ-08) |

### ASR-2.1 — Nueva pasarela de pagos regional

| Campo | Detalle |
|---|---|
| **Hipótesis** | Un nuevo adaptador de pagos puede integrarse y desplegarse en < 4 horas-hombre sin modificar el core |
| **Herramienta** | Medición manual + git diff (verificar 0 cambios en servicios core) |
| **Configuración** | Sprint de integración con mock de pasarela nueva; contador de horas y líneas modificadas en core |
| **Criterio de éxito** | ≤ 4h-hombre; 0 commits en servicios de negocio distintos al adaptador |
| **Historia relacionada** | SOL-20 (HU-ARQ-02) |

### ASR-2.2 — Nuevo ramo de seguro

| Campo | Detalle |
|---|---|
| **Hipótesis** | Un nuevo ramo puede configurarse en ≤ 2 semanas-equipo sin cambiar lógica del motor de rating |
| **Herramienta** | Medición de calendario + git diff |
| **Configuración** | Agregar ramo "seguro de mascota" solo via configuración YAML/DB; verificar 0 cambios en motor |
| **Criterio de éxito** | Disponible en staging en ≤ 2 semanas; 0 modificaciones en motor de rating |
| **Historia relacionada** | SOL-21 (HU-ARQ-01) |

### ASR-3.1 — Caída de Redis

| Campo | Detalle |
|---|---|
| **Hipótesis** | Al desconectar Redis, el sistema detecta el fallo y recupera operación en < 30 segundos sin pérdida de transacciones |
| **Herramienta** | Docker (`docker stop redis`) + JMeter midiendo disponibilidad + logs de recuperación |
| **Configuración** | Carga de 100 req/min durante 5 min; apagar Redis en minuto 2; medir tiempo hasta recuperación |
| **Criterio de éxito** | Recuperación automática < 30s; 0 transacciones perdidas; disponibilidad mensual proyectada ≥ 99,9% |
| **Historia relacionada** | SOL-29 (HU-ARQ-06) |

### ASR-3.2 — Caída de zona AWS

| Campo | Detalle |
|---|---|
| **Hipótesis** | Al fallar una zona EKS, el tráfico migra a la zona secundaria con RTO ≤ 10 minutos y RPO ≤ 30 segundos |
| **Herramienta** | AWS FIS (Fault Injection Simulator) + CloudWatch + JMeter |
| **Configuración** | Experimento FIS: terminar todos los nodos EKS de us-east-1a; medir tiempo de recuperación y pérdida de datos |
| **Criterio de éxito** | RTO ≤ 10 min; RPO ≤ 30s; disponibilidad mensual ≥ 99,9% |
| **Historia relacionada** | SOL-43 (HU-ARQ-09) |

### ASR-4.1 — Confidencialidad Open Finance

| Campo | Detalle |
|---|---|
| **Hipótesis** | El 100% de transmisiones usan TLS 1.3 y 0 campos PII quedan en texto plano en logs/BD/Kafka |
| **Herramienta** | OWASP ZAP (interceptación TLS) + consulta directa a BD y topics Kafka |
| **Configuración** | Flujo completo de cotización; ZAP como proxy; inspección de logs en CloudWatch y mensajes en Kafka |
| **Criterio de éxito** | ZAP no detecta downgrade a TLS 1.2; 0 registros PII en texto plano en BD, logs ni Kafka |
| **Historia relacionada** | SOL-23 (HU-ARQ-03) |

### ASR-4.2 — Integridad de pólizas emitidas

| Campo | Detalle |
|---|---|
| **Hipótesis** | Cualquier modificación no autorizada a una póliza en S3 es detectada y registrada en < 1 segundo |
| **Herramienta** | Script Python (modificación directa S3) + CloudWatch Events + log de auditoría |
| **Configuración** | Modificar objeto S3 con credenciales de prueba; verificar alerta en CloudWatch y entrada en log de auditoría |
| **Criterio de éxito** | Alerta generada en < 1s; registro completo en log de auditoría; póliza bloqueada para lectura posterior |
| **Historia relacionada** | SOL-45 (HU-ARQ-11) |

---

## SECCIÓN 6: Distribución de Esfuerzo y Cronograma

**Total de horas disponibles:** 7 semanas × 48 h/semana = **336 horas**

| Tipo de prueba | Semanas activas | Horas asignadas | % | Responsable |
|---|---|---|---|---|
| Unitarias y módulo — backend (pytest) | 5, 6 | 48 h | 14% | Angie Arandio |
| Unitarias y módulo — web (Jest + RTL) | 5, 6 | 24 h | 7% | Angie Arandio |
| Unitarias y módulo — móvil (Jest + Detox) | 6, 7 | 24 h | 7% | Juan Mejía |
| Integración / API (Postman Newman) | 6, 7 | 48 h | 14% | Juan Mejía |
| Hipótesis ASR / Rendimiento (JMeter) | 4, 5 | 72 h | 21% | Miguel Gómez |
| Usabilidad / exploratoria (Playwright) | 6, 7 | 60 h | 18% | Jazmin Córdoba |
| Seguridad (OWASP ZAP) | 7 | 36 h | 11% | Miguel Gómez |
| Internacionalización | 7 | 24 h | 7% | Todo el equipo |
| **Total** | | **336 h** | **100%** | |

### Cronograma por semana

| Semana | Fechas | Actividad |
|---|---|---|
| 1–2 | 3–16 ago | Diseño de casos de prueba, configuración Docker Compose, entornos AWS |
| 3 | 17–23 ago | Definición de hipótesis ASR, diseño de experimentos de rendimiento |
| 4–5 | 24 ago – 6 sep | Ejecución experimentos ASR con JMeter y FIS; análisis de resultados |
| 5–6 | 31 ago – 13 sep | Pruebas unitarias pytest, Jest (web y móvil); pruebas de módulo |
| 6–7 | 7–20 sep | Pruebas de integración API (Newman); Playwright web; Detox móvil; usabilidad |
| 7 | 14–23 sep | OWASP ZAP seguridad; i18n; cierre y reporte final |
