# Plan ejecutable - Experimento 1 de Solventa

## Decisión de alcance

Esta implementación ejecutará un **baseline a 500 solicitudes por minuto
agregadas** (8,33 solicitudes por segundo) sobre infraestructura real en AWS.
Los contratos, identidades, perfiles, tarifas y respuestas externas serán
sintéticos.

Este alcance **no valida** la hipótesis publicada de escalar desde 500 hasta
50.000 cotizaciones por minuto. Tampoco valida autoscaling de nodos. Sí permite
validar el recorrido técnico, calibrar el costo de CPU por solicitud, observar
el HPA de pods y obtener una línea base reproducible antes de aumentar la
carga.

Con 50 socios y reparto uniforme, cada socio recibe 10 solicitudes por minuto.
La comparación de p95 entre socios será exploratoria: a este volumen se
requieren ventanas largas para obtener percentiles individuales estables.

## Hipótesis operativa para este baseline

Si Cotización y Perfilamiento se ejecutan con dos réplicas iniciales, HPA al
70 %, capacidad de nodos preaprovisionada y cache-aside real en Redis, entonces
el recorrido sostendrá 500 RPM agregados con:

- tasa de error inferior a 1 %;
- p95 extremo a extremo menor o igual a 250 ms;
- p99 extremo a extremo menor o igual a 500 ms;
- réplicas adicionales `Ready` en menos de 60 segundos cuando el cálculo de CPU
  calibrado produzca una señal de escalamiento.

El objetivo más estricto de p95 menor o igual a 200 ms se reportará como meta
extendida, porque aparece en la arquitectura, mientras que el documento del
experimento usa 250 ms.

## Topología elegida

```text
JMeter local (predeterminado) o ECS Fargate (opcional)
        |
        | HTTPS + SigV4, 500 RPM agregados
        v
API Gateway REST regional (AWS_IAM + allowlist de IP)
        |
        | VPC Link
        v
NLB interno -> NodePort 30080
        |
        v
Cotización y Rating (EKS, HPA)
        |
        +----> PostgreSQL 15.19 (RDS)
        |
        v
Perfilamiento y Scoring (EKS, HPA)
        |
        +----> Redis OSS 7.1 (ElastiCache)
        +----> PostgreSQL 15.19 (RDS)
        +----> WireMock dentro de EKS, solo en cache miss

CloudWatch <- API Gateway, plano de control EKS, RDS y Redis
X-Ray <- API Gateway
S3 <- archivos de evidencia bajo jtl/
```

No existe BFF en este recorrido. La API de socios entra directamente por API
Gateway, de acuerdo con la decisión de mantener simple la arquitectura del
experimento.

## Infraestructura real

| Componente | Configuración inicial | Razón |
|---|---|---|
| VPC | Dos AZ, subredes públicas, privadas y de datos | Aislar cómputo y datos |
| NAT Gateway | Uno | Salida de nodos y Fargate con costo acotado |
| EKS | Kubernetes 1.36 | Versión vigente en soporte estándar |
| Nodos | Dos `c7i-flex.large`, fijos | Cuatro vCPU y forma x86_64 compatible con el plan Free de la cuenta |
| ECR | Cotización, Perfilamiento y JMeter | Imágenes versionadas por digest |
| API Gateway | REST regional, una operación, AWS_IAM, cuenta e IP restringidas | Entrada real autenticada y trazabilidad del salto externo |
| NLB | Interno | Integración privada desde API Gateway |
| RDS | PostgreSQL 15.19, `db.t4g.micro`, 20 GiB gp3, Single-AZ | Persistencia real de laboratorio |
| ElastiCache | Redis OSS 7.1, `cache.t4g.micro`, un nodo, TLS y AUTH | Caché administrada real |
| ECS Fargate | Opcional; JMeter 5.6.3, 0,5 vCPU y 1 GiB | Alternativa al generador local |
| CloudWatch | Logs administrados con siete días de retención y métricas nativas | Evidencia y diagnóstico |
| X-Ray | Activado únicamente en API Gateway | Trazabilidad del borde sin permisos amplios en nodos |
| S3 | Estado Terraform y evidencia en buckets separados | Reproducibilidad y teardown controlado |

RDS y Redis son Single-AZ porque el objetivo es rendimiento, no conmutación por
error. WAF, dominio propio, certificados ACM, réplicas Multi-AZ, RDS Proxy,
Karpenter y una región de recuperación quedan fuera del baseline.

## Capacidad y HPA

- Cotización: `minReplicas=2`, `maxReplicas=4`.
- Perfilamiento: `minReplicas=2`, `maxReplicas=4`.
- Solicitud por pod: 250 millicores y 256 MiB.
- Límite por pod: 500 millicores y 512 MiB.
- Objetivo HPA: 70 % de CPU respecto de la solicitud.
- Scale-up: sin ventana de estabilización; observación cada 30 segundos.
- Scale-down: estabilización de 300 segundos.
- Los dos nodos se crean antes de medir y no escalan durante la prueba.
- VPC CNI aplica `NetworkPolicy`: Cotización solo recibe el tráfico de entrada
  previsto; Perfilamiento solo recibe desde Cotización; WireMock solo recibe
  desde Perfilamiento.

El trabajo de CPU será un cálculo determinista y configurable en cada servicio.
No se usarán esperas artificiales (`sleep`) para simular procesamiento. La
calibración ajustará el factor de trabajo hasta producir una señal observable
de HPA sin romper deliberadamente los objetivos de latencia.

## Contrato sintético

La operación principal es `POST /api/v1/cotizaciones`. El cuerpo contiene solo
referencias sintéticas con formato y longitud limitados, por ejemplo:

```json
{
  "partner_ref": "partner-01",
  "profile_ref": "profile-00000000-0000-4000-8000-000000000101"
}
```

El servidor genera el identificador de la solicitud. `partner_ref` es solamente
una dimensión de medición; no concede permisos ni representa autenticación.
El baseline exige una firma SigV4 del usuario IAM exacto
`solventa-terraform-operator` o, cuando se habilita, del rol exacto del runner
Fargate, y restringe el origen en API Gateway. Esa identidad autentica al
generador, no a cada socio sintético. Las cuotas productivas por socio son un
objetivo diferente y no se considerarán validadas por esta prueba.

La resource policy contiene sendos `Deny` explícitos para cualquier IP o
principal fuera de sus allowlists. Esto hace obligatorios ambos controles
incluso cuando otra identity policy de IAM conceda `execute-api:Invoke`.

La autenticación no se propaga como identidad de servicio después de API
Gateway. El NLB es interno, el NodePort solo acepta su security group y las
`NetworkPolicy` segmentan los pods, lo cual es proporcional a este clúster
aislado de vida corta. mTLS o identidad workload-to-workload serían necesarios
antes de reutilizar este diseño en un entorno compartido o productivo.

No se usarán datos personales, financieros ni credenciales reales. Los cuerpos
no se escribirán en logs, trazas ni archivos JTL.

## Comportamiento de los mocks

- PostgreSQL contiene tarifas y parámetros sintéticos versionados.
- Un Job usa temporalmente el secreto administrador de RDS, crea un rol runtime
  de solo lectura, siembra 50 tarifas y 5.000 perfiles, y luego se elimina el
  secreto Kubernetes administrador.
- Las conexiones a RDS usan `sslmode=verify-full` con el bundle de CA de AWS.
- Redis exige TLS y AUTH, y usa cache-aside, TTL base de 15 minutos y jitter.
- WireMock entrega una respuesta determinista y tiene una URL fija por
  configuración; ninguna URL proviene de la solicitud.
- Cada corrida usa 20 perfiles nuevos por socio. El warm-up de baja tasa deja
  algunos perfiles fríos deliberadamente; los misses restantes y la transición
  a hits forman parte de la ventana medida y no se ocultan del percentil.
- Un cache hit evita la llamada a WireMock, pero ambos servicios mantienen un
  cálculo CPU determinista para que el recorrido siga siendo medible.

## Preparación de acceso

1. Usar únicamente el perfil temporal `solventa-lab`; el backend S3 usa el
   perfil puente `solventa-terraform-backend`, cuyo `credential_process` exporta
   esa misma sesión sin persistir secretos.
2. Verificar antes de cada plan o apply:

   ```bash
   /opt/homebrew/bin/aws sts get-caller-identity --profile solventa-lab
   ```

3. La cuenta esperada es `969325258550` y el ARN debe terminar en
   `user/solventa-terraform-operator`.
4. Adjuntar al grupo del operador la política IAM de bootstrap incluida en el
   repositorio. Esta política solo administra roles/policies con prefijo
   `solventa-exp1-` y restringe `iam:PassRole` a los servicios usados.
5. No crear access keys ni poner secretos en Terraform, Git, Helm o JMeter.

## Herramientas locales

El equipo de desarrollo ya quedó preparado con AWS CLI 2.36.44, Terraform
1.13.1, Helm 4.3.0, kubectl 1.37.0, Docker/Colima, Docker Buildx 0.37.1, `jq`,
`xmllint`, ShellCheck 0.11.0 y kubeconform 0.8.0. JMeter 5.6.3 y Java 17 viven
dentro de una imagen reproducible; no se instalan directamente en macOS.

Buildx y las tres imágenes de ejecución usan `linux/amd64`, coherente con el
contexto `colima-x86`, los nodos EKS `c7i-flex.large` y el runner Fargate opcional.

## Secuencia de implementación

### 0. Validación local

- Ejecutar pruebas unitarias de ambos servicios.
- Construir imágenes `linux/amd64` con Colima.
- Levantar PostgreSQL, Redis, WireMock y aplicaciones con Compose.
- Ejecutar smoke test y una carga corta.

### 1. Bootstrap de estado

- Crear con Terraform el bucket S3 de estado, versionado, cifrado y sin acceso
  público.
- Inicializar el stack principal usando lockfile nativo de S3.

### 2. Plan de infraestructura

- Ejecutar `terraform fmt`, `validate` y `plan`.
- Revisar identidad, región, cantidad de recursos, CIDR permitido y costo.
- No aplicar si aparecen recursos fuera del prefijo/tag del experimento.

### 3. Aprovisionamiento

- Crear red, EKS, VPC CNI, ECR, RDS, Redis, NLB, API Gateway, CloudWatch y S3.
  ECS/Fargate solo se crea si se activa explícitamente con una imagen inmutable.
- Esperar estado saludable de RDS, Redis y nodos.
- Construir y subir las imágenes a ECR con tag de commit y conservar digest.
- Crear los secretos Kubernetes efímeros de seed, rol runtime y Redis desde
  Secrets Manager, sin imprimirlos ni guardarlos en archivos.
- Instalar metrics-server y el chart de Solventa.

### 4. Datos y calibración

- Crear esquema y tarifas sintéticas de manera idempotente.
- Permitir que el warm-up caliente solo una parte de los perfiles de la corrida;
  no precargar ni vaciar Redis artificialmente.
- Ejecutar smoke a 50 RPM.
- Ajustar únicamente el factor de cálculo CPU; congelarlo antes de las corridas
  oficiales.
- Registrar imágenes, digests, variables, réplicas y estado inicial.

### 5. Tres corridas oficiales

Cada corrida usa el mismo artefacto y configuración:

1. Cinco minutos a 50 RPM para estabilizar.
2. Salto a 500 RPM en cinco segundos o menos.
3. Treinta minutos a 500 RPM agregados, sin retries del cliente.
4. Cinco minutos de enfriamiento a 50 RPM.
5. Esperar que réplicas y caché vuelvan al estado inicial.

El primer minuto posterior al salto no se excluye al evaluar el tiempo de
recuperación. Los percentiles se calculan a partir de muestras, nunca
promediando percentiles de nodos o corridas.

### 6. Evidencia

Conservar por corrida:

- JTL crudo y reporte HTML de JMeter, sin bodies ni headers;
- tasa ofrecida, completada y válida;
- p50, p95, p99 y máximo, tanto global como por minuto;
- errores por tipo y código;
- CPU, memoria, réplicas deseadas/actuales/Ready y reinicios;
- cache hits, misses, conexiones y evictions;
- conexiones, CPU, waits y latencia de PostgreSQL;
- solicitudes recibidas por WireMock;
- manifiesto de variables, commit, valores Helm e imágenes por tag/digest;
- timestamps de inicio del salto, decisión HPA y recuperación del SLO.

### 7. Destrucción

- Descargar y verificar toda la evidencia.
- Ejecutar `terraform destroy` del stack principal el mismo día.
- Confirmar por APIs de AWS que no quedan EKS, EC2, NAT, NLB, RDS, Redis, ECS
  tasks ni log groups del experimento.
- Conservar únicamente los buckets acordados; eliminar versiones cuando se
  decida cerrar definitivamente el laboratorio.

## Regla de aceptación del baseline

Cada una de las tres corridas debe cumplir por separado:

- carga ofrecida: 500 RPM con tolerancia de 1 %;
- éxito: al menos 99 % de solicitudes HTTP válidas y respuesta de negocio con
  esquema correcto;
- p95 global menor o igual a 250 ms;
- p99 global menor o igual a 500 ms;
- sin saturación sostenida de conexiones, memoria o almacenamiento;
- si el HPA se activa, capacidad suficiente `Ready` y recuperación simultánea
  de throughput, latencia y error en 60 segundos o menos.

Los `429`, timeouts, fallos de conexión, respuestas 5xx y respuestas 2xx con
esquema de negocio inválido cuentan como error.

## Abortos controlados

Abortar una corrida sin destruir evidencia si ocurre cualquiera de estos casos:

- error superior a 5 % durante dos minutos consecutivos;
- p99 superior a dos segundos durante dos minutos;
- agotamiento de conexiones de PostgreSQL o Redis;
- nodos sin capacidad para programar pods;
- generador por encima de 80 % de CPU o incapaz de sostener la tasa;
- réplicas creciendo sin límite útil o reinicios continuos.

## Costo y permanencia

La parte fija estimada es aproximadamente USD 0,39 por hora antes de logs,
trazas, solicitudes y transferencia. Mantenerla 24 horas se acerca a USD 10 y
un mes completo ronda USD 285. El experimento debe crearse, medirse y destruirse
en una ventana corta. El plan final de Terraform se revisará antes de incurrir
en costo.

## Trabajo futuro para validar el experimento publicado

Para probar 50.000 RPM se necesita otro dimensionamiento basado en capacidad
medida por pod, aumento de cuota EC2, generadores distribuidos, revisión de
límites de API Gateway, Redis y PostgreSQL, y una subprueba de noisy-neighbor.
Ese cambio no consiste en multiplicar réplicas a ciegas y no forma parte de
este baseline.
