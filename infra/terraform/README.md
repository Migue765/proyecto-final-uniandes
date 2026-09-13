# Infraestructura — experimento 1

Terraform crea la infraestructura real del experimento 1 en `us-east-1`; los
contratos y datos de cotización pueden ser mocks, pero la ruta de red y los
servicios administrados son reales.

## Alcance

- VPC propia en dos zonas, con dos subredes públicas, dos privadas de aplicación
  y dos subredes de datos aisladas.
- Un NAT Gateway compartido por las dos subredes privadas.
- EKS 1.36 con un grupo fijo de dos nodos `c7i.large` (2 vCPU cada uno) y el
  add-on administrado VPC CNI con enforcement de `NetworkPolicy` habilitado.
- ECR privado para `quote`, `profile` y `load-runner`.
- RDS PostgreSQL 15.19 `db.t4g.micro`, 20 GB gp3, Single-AZ y contraseña maestra
  administrada por RDS en Secrets Manager.
- ElastiCache Redis OSS 7.1 `cache.t4g.micro`, un nodo, privado, con TLS y token
  de autenticación generado de forma efímera y guardado en Secrets Manager.
- NLB interno hacia el NodePort fijo `30080` y API Gateway REST regional con
  VPC Link. La resource policy permite únicamente CIDRs explícitos de
  laboratorio y la EIP del NAT usada por el runner Fargate, y únicamente
  al operador `solventa-terraform-operator` y, cuando se habilita, al rol
  específico del runner Fargate. Sendos `Deny` explícitos para cualquier
  origen o principal fuera de esas allowlists impiden que una identity policy
  IAM omita cualquiera de los dos controles. Solo expone
  `POST /api/v1/cotizaciones`, exige firma SigV4 mediante `AWS_IAM` y usa la
  política TLS 1.3 `SecurityPolicy_TLS13_1_3_2025_09` en modo `STRICT`.
  El security group del NLB no acepta clientes directos; la evaluación inbound
  se desactiva únicamente para el tráfico PrivateLink de API Gateway. Sus IP
  privadas son estáticas y se usan como allowlist de `NetworkPolicy` hacia
  Cotización.
- Logs del plano de control de EKS, API Gateway, RDS, Redis y el load runner con
  retención de 7 días; trazas X-Ray activas en API Gateway.
- Bucket S3 privado para archivos JTL bajo `jtl/`, con expiración a 14 días.
- Runner de carga ECS/Fargate opcional y desactivado por defecto.

No incluye BFF, WAF, dominio personalizado, Multi-AZ ni autoscaling del node
group. Esas ausencias son deliberadas para el laboratorio y no representan una
arquitectura de producción.

Este baseline no instala CloudWatch Agent, Fluent Bit ni Container Insights en
EKS. Por tanto, el log group de EKS contiene únicamente logs del plano de
control; los logs de los pods y las métricas de Container Insights no se
exportan a CloudWatch. El `containerInsights` del cluster ECS opcional solo
aplica al runner Fargate y no cambia esta limitación de EKS.

## Prerrequisitos

- Terraform 1.10 o posterior.
- AWS CLI v2 en `/opt/homebrew/bin/aws`.
- Perfil `solventa-lab` autenticado sin access keys.
- Perfil puente `solventa-terraform-backend`, sin secretos persistidos, para
  que el backend S3 consuma la sesión temporal de `aws login` mediante
  `credential_process`.
- Política de [`iam-bootstrap`](iam-bootstrap/README.md) asociada al grupo
  `solventa-terraform-operators`.
- Cuota EC2 On-Demand Standard de al menos 4 vCPU. La configuración fija dos
  nodos para permanecer dentro de la cuota de 5 vCPU observada.

Compruebe la identidad antes de cada operación:

```bash
/opt/homebrew/bin/aws login --profile solventa-lab --region us-east-1
/opt/homebrew/bin/aws sts get-caller-identity --profile solventa-lab
/opt/homebrew/bin/aws configure set credential_process \
  '/opt/homebrew/bin/aws configure export-credentials --profile solventa-lab' \
  --profile solventa-terraform-backend
/opt/homebrew/bin/aws configure set region us-east-1 \
  --profile solventa-terraform-backend
/opt/homebrew/bin/aws sts get-caller-identity \
  --profile solventa-terraform-backend
```

Ambas verificaciones deben devolver `Account` `969325258550` y un ARN terminado
en `user/solventa-terraform-operator`. El perfil puente ejecuta al AWS CLI para
obtener las mismas credenciales temporales en formato `credential_process`; no
crea ni guarda access keys. El provider también aplica este guardrail.

## 1. Bootstrap del state

El state tiene un root module separado para evitar un ciclo de dependencia. Su
state inicial es local y no contiene secretos de aplicación.

```bash
cd infra/terraform/bootstrap
terraform init
terraform fmt -check
terraform validate
terraform plan -out=bootstrap.tfplan
terraform apply bootstrap.tfplan
terraform output -json backend_config
```

La última salida debe coincidir con `exp1/backend.hcl.example`. Cree el archivo
local, ignorado por Git:

```bash
cd ../exp1
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
```

Edite `terraform.tfvars` y reemplace `203.0.113.10/32` por la IP pública actual
del operador terminada en `/32`, tanto para
`cluster_endpoint_public_access_cidrs` como para
`api_allowed_source_cidrs`. Terraform rechaza explícitamente `0.0.0.0/0`.

## 2. Inicialización y plan del experimento

```bash
terraform init -backend-config=backend.hcl
terraform fmt -check -recursive ..
terraform validate
terraform plan -out=exp1.tfplan
terraform show exp1.tfplan
```

Antes del `apply`, verifique en el plan:

- cuenta `969325258550` y región `us-east-1`;
- exactamente dos nodos `c7i.large`;
- RDS y Redis sin acceso público y Single-AZ;
- endpoint público de EKS restringido al `/32` elegido;
- API Gateway restringido a los CIDRs de laboratorio y la EIP del NAT;
- `Deny` explícito de API Gateway para cualquier origen fuera de esos CIDRs;
- `Deny` explícito para cualquier principal distinto del operador y el rol
  opcional del runner;
- principal de la resource policy restringido al operador exacto y, si se
  habilita, al rol exacto del runner Fargate; método con `authorization =
  "AWS_IAM"`;
- ningún valor de contraseña en variables, plan o repositorio;
- `enable_ecs_load_runner = false`, salvo que se vaya a ejecutar desde Fargate.

Solo después de revisar el plan completo:

```bash
terraform apply exp1.tfplan
terraform output -json
```

Este repositorio no ejecuta `apply` automáticamente.

`partner_ref` es solamente una etiqueta sintética en el body de prueba. No es
una identidad, una credencial ni un mecanismo de autorización. El acceso al
endpoint requiere que el principal sea el usuario IAM
`solventa-terraform-operator` o, cuando se habilita, el rol exacto del runner
Fargate; además debe tener `execute-api:Invoke`, presentar una firma SigV4
válida y provenir de una IP permitida. Las cuotas o autorizaciones
productivas por socio quedan fuera del baseline y nunca se infieren de esa
etiqueta.

El secreto maestro de RDS solo se entrega al Job idempotente de inicialización.
Ese Job crea un rol `solventa_runtime` con permisos de lectura sobre las tablas
sintéticas; los Deployments reciben exclusivamente la URL de ese rol. El
secreto Kubernetes temporal con el usuario administrador se elimina después de
que el Job termina correctamente. Las conexiones verifican el certificado de
RDS con `sslmode=verify-full` y el bundle de CA de AWS fijado en las imágenes.

## 3. Runner opcional en ECS/Fargate

El baseline predeterminado usa el runner local. La política IAM de bootstrap no
permite escribir políticas inline en roles del operador, por lo que no autoriza
la creación del task role de Fargate. Esto evita una vía de escalamiento de
privilegios. Para activar esta opción, un administrador debe revisar el
`aws_iam_role_policy.load_runner_evidence` y aplicar este cambio puntual con una
sesión administrativa; no se debe ampliar el operador con
`iam:PutRolePolicy` genérico.

Para crear el cluster y task definition del runner, establezca en el archivo
local `terraform.tfvars`:

```hcl
enable_ecs_load_runner = true
```

No existe una imagen predeterminada ni un fallback a `latest`. Antes de activar
Fargate, establezca `load_runner_image` con el tag inmutable basado en el commit
o, preferiblemente, con el digest de ECR producido por el build. Terraform
rechaza la creación de la task definition si falta ese valor. La tarea se
ejecuta en las subredes privadas, sin IP pública, y su role de aplicación solo
puede escribir objetos en `s3://<evidence_bucket_name>/jtl/`. Los permisos de
ECR y CloudWatch están separados en el execution role administrado por ECS.

La tarea obtiene credenciales temporales de su task role, firma cada request a
API Gateway mediante SigV4 y nunca recibe access keys estáticas. La task
definition declara `X86_64`, igual que los nodos EKS y el builder local
`colima-x86`; la imagen debe construirse para `linux/amd64`. Un build explícito
para esta task es, por ejemplo:

```bash
docker buildx build --platform linux/amd64 \
  --file load-tests/jmeter/Dockerfile \
  --tag <ecr-load-runner>:<tag-inmutable> \
  --push load-tests/jmeter
```

Una imagen únicamente `linux/arm64` fallará al iniciar en esta task definition.

## Observabilidad disponible

API Gateway envía trazas a X-Ray mediante la integración administrada de AWS.
No se despliega un collector dentro de EKS ni se concede escritura a X-Ray al
role compartido de los nodos. Los servicios exponen métricas Prometheus dentro
del clúster para inspección durante la corrida, pero este baseline no instala
un backend persistente de métricas. Las métricas administradas de API Gateway,
RDS y ElastiCache y sus log groups de siete días son la evidencia persistente
en CloudWatch; los JTL quedan en el bucket de evidencia.

## Costos y advertencias

Con los precios unitarios verificados para `us-east-1`, el costo fijo de
referencia es aproximadamente USD 0,378/h o USD 276/mes a 730 horas:

| Recurso | Referencia por hora |
| --- | ---: |
| EKS control plane | USD 0,10000 |
| 2 × c7i.large | USD 0,17850 |
| RDS db.t4g.micro | USD 0,01600 |
| Redis cache.t4g.micro | USD 0,01600 |
| NAT Gateway | USD 0,04500 |
| NLB | USD 0,02250 |

No incluye almacenamiento, snapshots, solicitudes de API Gateway, LCUs del
NLB, procesamiento/transferencia del NAT, logs, X-Ray, S3 ni Fargate. Confirme
siempre el precio vigente en AWS antes de ejecutar. El NAT, EKS y los nodos
siguen facturando aunque no exista tráfico.

El NAT único reduce costo, pero introduce un único punto de falla y posible
tráfico entre zonas. RDS, Redis y los nodos fijos tampoco ofrecen la resiliencia
ni el escalado que se exigirían en producción.

## Destrucción

Conserve primero la evidencia que necesite. El bucket de evidencia usa
`force_destroy = true`, por lo que sus JTL se eliminan junto con el stack.

```bash
cd infra/terraform/exp1
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

Después de comprobar que el state del experimento ya no contiene recursos,
destruya el bucket de backend por separado. El bucket de state no tiene
`force_destroy`; sus versiones deben eliminarse de forma consciente antes de
destruirlo.

```bash
cd ../bootstrap
terraform destroy
```

Nunca elimine manualmente el bucket de state antes del stack principal y nunca
suba `backend.hcl`, `terraform.tfvars`, planes ni archivos de state a Git.
