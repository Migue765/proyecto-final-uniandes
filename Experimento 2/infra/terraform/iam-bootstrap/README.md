# IAM bootstrap del operador

`PowerUserAccess` permite administrar los servicios del experimento, pero no
permite crear los roles que EKS y API Gateway necesitan. La política
[`policy.json`](policy.json) añade únicamente la administración de roles cuyo
nombre comience por `solventa-exp1-`, permite adjuntar solo las políticas AWS
enumeradas de EKS, ECR y API Gateway, y restringe `PassRole` a los servicios
usados. No concede `PutRolePolicy`, de modo que el operador no pueda insertar
políticas inline ni convertir el prefijo del laboratorio en una vía de
escalamiento de privilegios. También permite crear exclusivamente los roles
vinculados a servicio que EKS, el node group, RDS, ElastiCache, ELB y el runner
ECS pueden necesitar la primera vez que se usan en la cuenta. EKS también
valida si ya existe `AWSServiceRoleForAmazonEKSNodegroup` antes de crear un
node group; por eso se permite `iam:GetRole` únicamente sobre ese rol vinculado
exacto.

La creación del rol vinculado de ElastiCache se cubre con
`iam:CreateServiceLinkedRole` condicionado a `elasticache.amazonaws.com`. No se
incluye `iam:PutRolePolicy`: la consola de IAM marca `iam:AWSServiceName` como
una condición no aplicable a esa acción y las políticas administradas vigentes
de ElastiCache no la requieren. Si una operación futura la solicitara, detenga
el despliegue y precree el rol vinculado desde una sesión administradora; no
amplíe los permisos del operador.

Esta política es un bootstrap manual. No puede ser creada por el mismo operador
antes de que tenga los permisos y no debe resolverse creando access keys.

## Asociación desde la consola

1. Iniciar una sesión con un administrador de la cuenta protegido por MFA. Usar
   el usuario raíz solo si todavía no existe otro administrador.
2. Ir a **IAM → Políticas → Crear política → JSON**.
3. Pegar el contenido exacto de `policy.json` y crearla con el nombre
   `solventa-exp1-terraform-iam-bootstrap`.
4. Ir a **IAM → Grupos de usuarios → solventa-terraform-operators → Permisos →
   Agregar permisos → Asociar políticas**.
5. Asociar `solventa-exp1-terraform-iam-bootstrap`.
6. Cerrar inmediatamente la sesión raíz y volver a
   `solventa-terraform-operator`.

No se deben crear access keys, incluir contraseñas en archivos ni copiar
credenciales de consola. La CLI usa únicamente la sesión temporal del perfil
`solventa-lab` mediante `aws login`.

No amplíe esta política a `iam:*`. Si AWS solicita un rol vinculado distinto de
los seis servicios enumerados, detenga el `apply` y revise el servicio exacto
antes de cambiar la allowlist de `iam:AWSServiceName`.

El plan predeterminado, con el runner local, no necesita políticas inline de
IAM. La alternativa Fargate está desactivada porque su task role sí requiere
una política inline exacta para invocar API Gateway y escribir evidencia. Esta
política de bootstrap no autoriza crearla. Si se habilita Fargate, ese cambio
debe aplicarlo un administrador después de revisar el documento de permisos;
no agregue un `iam:PutRolePolicy` genérico al operador.

## Adición: proveedor OIDC para el Cluster Autoscaler

Para la fase de caracterización de capacidad a mayor RPM (`PLAN-PROYECCION-CPU.md`)
se agregó `aws_iam_openid_connect_provider.eks` y un rol IRSA para el Cluster
Autoscaler (`infra/terraform/exp1/cluster-autoscaler.tf`). Crear ese proveedor
OIDC requiere `iam:CreateOpenIDConnectProvider`, que tampoco está en
`PowerUserAccess`-menos-restricciones ni en la política original de este
bootstrap. Se agregó el statement `ManageOnlyExperimentEksOidcProvider`,
acotado por recurso al proveedor OIDC exacto del clúster
(`oidc.eks.us-east-1.amazonaws.com/*`), sin conceder `iam:*` sobre proveedores
OIDC de otras cuentas o servicios.

Como la política ya existe y está asociada, un administrador no la vuelve a
crear: en **IAM → Políticas → `solventa-exp1-terraform-iam-bootstrap` → Editar
política → JSON**, reemplazar el contenido por el de `policy.json` actualizado
y guardar como nueva versión (IAM la marca como versión activa
automáticamente). El operador no puede hacer este paso por sí mismo.

## Adición: `iam:PutRolePolicy` acotado a `solventa-exp1-*`

El rol del Cluster Autoscaler (`aws_iam_role.cluster_autoscaler`) necesita una
política inline con permisos de Auto Scaling (`SetDesiredCapacity`,
`TerminateInstanceInAutoScalingGroup`, `UpdateAutoScalingGroup`, acotados por
`autoscaling:ResourceTag/k8s.io/cluster-autoscaler/solventa-exp1=owned`, más
lectura de descripción de ASG/EC2 sin acotar por ser solo lectura). Crear esa
política inline requiere `iam:PutRolePolicy`, que el bootstrap original omitía
a propósito para impedir que el operador se autoconceda permisos arbitrarios.

En vez de agregar `iam:PutRolePolicy` sin acotar, se agregó al mismo statement
`ManageOnlyExperimentRoles` que ya tenía `iam:DeleteRolePolicy` con idéntico
alcance (`role/solventa-exp1-*`) — el operador ya controlaba el ciclo de vida
completo de esos roles (crear, adjuntar las seis políticas administradas
enumeradas, borrar); esto solo completa el par crear/borrar de políticas
inline que ya existía a medias, sin ampliar a otros roles ni a `iam:*`. El
contenido exacto de cada política inline igual debe revisarse en el `terraform
plan` antes de cada `apply`, como con cualquier otro cambio de este stack.

## Adición: roles de Experimento 2 (`solventa-exp2-*`)

Experimento 2 (`infra/terraform/exp2/`) reutiliza el clúster EKS y el
proveedor OIDC ya creados por exp1 (no crea uno nuevo, por lo que no hace
falta tocar el statement `ManageOnlyExperimentEksOidcProvider`), pero
necesita tres roles IRSA propios (Adaptador de Ingreso, Reclamos, Pagos), cada
uno con una política inline de mínimo privilegio sobre colas SQS específicas.
Como el statement `ManageOnlyExperimentRoles` original está acotado por
recurso a `role/solventa-exp1-*`, no autoriza crear ni administrar roles con
el prefijo `solventa-exp2-*`.

Se agregó el statement `ManageOnlyExperiment2Roles`, un espejo exacto de
`ManageOnlyExperimentRoles` (incluye `iam:PutRolePolicy` desde el inicio,
porque ya se sabe que estos roles solo llevan políticas inline, nunca
políticas administradas de AWS) pero acotado por recurso a
`role/solventa-exp2-*`. No se le agregó `AttachOnlyRequiredAWSManagedPolicies`
ni `PassOnlyExperimentRolesToRequiredServices`: los roles IRSA de
Experimento 2 no adjuntan políticas administradas de AWS y no requieren
`PassRole` (el pod asume el rol vía `sts:AssumeRoleWithWebIdentity` federado
con el proveedor OIDC existente, no vía un servicio de AWS que necesite
recibir el rol). No se amplió el prefijo `solventa-exp1-*` a un comodín más
amplio; cada experimento conserva su propio statement acotado.
