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
