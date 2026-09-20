# Experimento 2 — Terraform (SQS + IAM/IRSA)

Este stack solo provisiona la mensajería durable y los roles IRSA de
Experimento 2 (ASR-EVT-01). Reutiliza, mediante *data sources* de solo
lectura, la VPC, el clúster EKS, el nodo/security groups y el proveedor OIDC
ya aplicados por `infra/terraform/exp1/` — no crea un clúster nuevo, no toca
el estado de exp1 y se puede destruir de forma independiente.

## Qué crea

- Dos colas SQS FIFO con contrapresión y partición por clave de negocio:
  `entrada-parametrica.fifo` y `ordenes-pagos.fifo`, cada una con su DLQ.
- Un único rol IAM con IRSA (`solventa-exp2-workload`), compartido por los
  tres servicios (Adaptador de Ingreso, Reclamos, Pagos) — decisión explícita
  del laboratorio: al ser un entorno de pruebas, no se justificó la
  separación en tres roles distintos. El rol sigue acotado por ARN a las
  cuatro colas de experimento 2 exactas (nunca `sqs:*` sobre `Resource: "*"`),
  así que aunque no hay separación de privilegios *entre* Ingreso/Reclamos/Pagos,
  sigue sin poder tocar ninguna otra cola de la cuenta (incluida cualquier
  cola de otro experimento).

## Qué NO crea (y por qué)

- El namespace de Kubernetes `solventa-exp2` — se crea con `kubectl`/Helm al
  desplegar los servicios, igual que exp1 no gestiona sus propios namespaces
  desde Terraform. Los roles IRSA ya quedan condicionados a
  `system:serviceaccount:solventa-exp2:<service-account>`, así que el
  namespace debe existir con ese nombre exacto antes de desplegar.
- Bases de datos nuevas en PostgreSQL — Experimento 2 reutiliza la misma
  instancia RDS de exp1 (`solventa-exp1-postgres`); los nodos EKS ya tienen
  acceso de red porque comparten el mismo `security_group` de nodos que RDS ya
  permite. Crear los esquemas/bases de Reclamos y Pagos es una tarea a nivel de
  aplicación (migraciones), no de esta infraestructura.
- Un clúster EKS o VPC nuevos — se reutiliza deliberadamente el de exp1 para
  no duplicar costo ni tiempo de aprovisionamiento.

## Decisión de diseño importante: `content_based_deduplication = false`

El corpus de prueba envía a propósito duplicados exactos y reentregas tardías
del mismo `externalEventId` para comprobar que el patrón Inbox (restricción de
unicidad en PostgreSQL) los colapsa correctamente. Si se activara la
deduplicación por contenido de SQS, la propia cola absorbería en silencio la
mayoría de esos duplicados intencionales dentro de su ventana de 5 minutos, y
Reclamos/Pagos nunca los verían — invalidando la prueba. Por eso el productor
debe enviar un `MessageDeduplicationId` explícito y aleatorio en cada intento
(nunca derivado del `externalEventId`), dejando que la idempotencia real se
resuelva únicamente en el Inbox de cada servicio.

## Requisito previo: ampliar el bootstrap IAM del operador

La política `iam-bootstrap/policy.json` solo permite administrar roles con
prefijo `solventa-exp1-*`. Antes de poder aplicar `iam.tf` en este stack, un
administrador de la cuenta (no el operador, no este asistente) debe pegar la
versión actualizada de `../iam-bootstrap/policy.json` — que agrega un
statement mirror `ManageOnlyExperiment2Roles` acotado a
`role/solventa-exp2-*` — siguiendo el mismo procedimiento documentado en
`../iam-bootstrap/README.md`. `terraform plan` funciona sin este cambio (solo
lee/simula); `terraform apply` fallará en `aws_iam_role.workload` con
`AccessDenied` hasta que la política esté actualizada.

## Aplicar

```bash
cd infra/terraform/exp2
terraform init -backend-config=backend.hcl
terraform plan
# revisar el plan, luego:
terraform apply
```
