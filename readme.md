
# Solventa — Proyecto Final MISW4501

**Universidad de los Andes · Departamento de Ingeniería de Sistemas y Computación**
Curso MISW4501 · Proyecto Final · 2026-II

---

## Sobre Solventa

Solventa es una aseguradora digital (*insurtech*) greenfield, nativa en la nube, construida sobre **Finanzas Abiertas (Open Finance)** y **Datos Abiertos (Open Data)**. Su propuesta de valor es permitir cotizar, suscribir, emitir y pagar siniestros de forma casi instantánea, embebiendo seguros directamente en el punto de necesidad del cliente (API-first / embedded insurance).

Opera en los ramos de viaje, protección de dispositivos, microseguros de vida, seguro paramétrico (clima/vuelos) y protección de pagos ligada a crédito. El caso insignia es el **seguro de vida hipotecario**, donde el perfil de riesgo se construye en tiempo real combinando señales de Open Finance y Open Data durante el flujo de originación del crédito.

El proyecto diseña, justifica y construye la arquitectura de Solventa de extremo a extremo, con clientes **web** y **móvil**, y la defiende con evidencia experimental frente a seis atributos de calidad: **latencia, escalabilidad, disponibilidad, seguridad, facilidad de modificación y facilidad de integración**.

---

## Equipo — Grupo 2

| Rol | Integrante |
|---|---|
| Gerente del proyecto | Jazmin Natalia Cordoba Puerto |
| Integrante | Juan Esteban Mejia Isaza |
| Integrante | Miguel Alejandro Gomez Alarcon |
| Integrante | Angie Natalia Arandio |

---

## Estructura del repositorio

```
documentos/
  Diagramas/                   ← Diagramas de arquitectura (C4, dominio, despliegue)
  enunciados-proyecto-tesis.pdf
  objetivo-semanales.pdf

Experimento 1/                 ← Baseline de escalabilidad (500 RPM)
  terraform/                    infraestructura AWS
  services/                     servicios sintéticos (profile, quotation)
  load-tests/                   generador y protocolo JMeter

Experimento 2/                 ← Escalabilidad 500 a 50k RPM
  infra/terraform/               infraestructura AWS
  services/                      servicios (ingreso, pagos, profile, quotation, reclamos)
  load-tests/                    JMeter (jmeter, jmeter-exp2)
```

## Accesos rapidos

| Recurso | Enlace |
| --- | --- |
| Prototipo web | [Abrir aplicacion](https://juanes545.github.io/solventa-web/) |
| Aplicacion movil | [Descargar APK](https://github.com/JUANES545/solventa-app/releases/latest/download/solventa.apk) |
| Repositorio principal | [Proyecto Final Uniandes](https://github.com/Migue765/proyecto-final-uniandes) |
| Repositorio web | [Solventa Web](https://github.com/JUANES545/solventa-web) |
| Repositorio movil | [Solventa App](https://github.com/JUANES545/solventa-app) |
| Tablero de trabajo | [Jira - Proyecto SOL](https://proyectointegradorgrupo2.atlassian.net/jira/software/projects/SOL/boards/2/backlog) |
| Pruebas exploratorias | [Inventario V3](https://uniandes-my.sharepoint.com/:x:/g/personal/ma_gomeza1_uniandes_edu_co/IQDwII5CJqksQLqjId5G72GpAZDM_5AIyVvgfZzRHT4R6uk?e=bsxn5m) |
| Experimentos de arquitectura | [Experimentos](https://github.com/Migue765/proyecto-final-uniandes/wiki/Semana-7-Experimentos) |
