# Servicios mock del experimento 1

Esta carpeta implementa el recorrido real que se someterá a carga:

`cliente -> quotation-service -> profile-service -> Redis/PostgreSQL/OpenFinanceMock`

Los datos son exclusivamente sintéticos. Las dependencias, depósitos de
conexiones, caché, consultas y cálculo de cotización sí son reales. Los servicios
no usan `sleep` ni ciclos de hash artificiales para fabricar latencia o carga.

## Qué hace exactamente una solicitud

### 1. Entrada

```
POST https://<rest-api-id>.execute-api.us-east-1.amazonaws.com/lab/api/v1/cotizaciones
Authorization: AWS4-HMAC-SHA256 ...   (SigV4, servicio execute-api, us-east-1)
Content-Type: application/json

{"partner_ref":"partner-01","profile_ref":"profile-00000000-0000-4000-8000-000000000101","requested_amount":10000000,"term_months":12}
```

Todos los campos son opcionales; `{}` o un body vacío usa los valores
sintéticos por defecto (`partner-01`, el perfil `...000101`, `10000000` y `12`).

### 2. Recorrido de red hasta el pod

1. API Gateway (REST, stage `lab`) valida la firma SigV4 y el principal IAM
   contra la resource policy (un solo ARN permitido) antes de aplicar el
   throttle de la cuenta.
2. VPC Link reenvía al NLB interno.
3. El NLB balancea al NodePort `30080` de uno de los dos nodos EKS.
4. El Service `solventa-exp1-quotation` enruta a uno de los pods `quotation`
   (2 réplicas, HPA 2–4 al 70 % CPU).

### 3. Dentro de `quotation-service`

1. Valida el body contra `QuoteRequest` (Pydantic, `extra=forbid`):
   formato de `partner_ref` (`partner-01`…`partner-50`), formato de
   `profile_ref` y que pertenezca a la partición de 100 perfiles asignada a
   ese socio, y rangos de `requested_amount` (100.000–1.000.000.000) y
   `term_months` (1–60). Cualquier violación devuelve `400
   {"error":"invalid_request"}` sin tocar ninguna dependencia.
2. Llama internamente a `profile-service`:
   `POST http://solventa-exp1-profile:8080/internal/v1/profiles/score`
   con `{"partner_ref":...,"profile_ref":...}`, sin reintentos, timeout de
   conexión 0,25 s y de lectura 0,75 s.

### 4. Dentro de `profile-service`

1. Revalida el mismo par `partner_ref`/`profile_ref`.
2. Cache-aside en Redis, con clave `SHA-256(partner_ref\0profile_ref)` (nunca
   se guardan las referencias en texto plano):
   - **Hit**: lee de Redis los `ProfileInputs` ya calculados
     (`age`, `monthly_income`, `debt_ratio`, `claims_count`,
     `account_age_months`, `inflow_stability`, `delinquency_count`).
     `cache_status="hit"`; no se consulta PostgreSQL ni `OpenFinanceMock`.
   - **Miss**: consulta PostgreSQL por los datos demográficos del perfil
     sembrado, y llama a `OpenFinanceMock`
     (`POST http://solventa-exp1-openfinancemock:8080/open-finance/v1/profiles`
     con `{"partner_ref":...,"profile_ref":...}`) para obtener
     `account_age_months`, `inflow_stability` y `delinquency_count`. Combina
     ambos resultados, los escribe en Redis con TTL de 900 s más un jitter
     determinista de 0–60 s, y responde `cache_status="miss"`.
3. Calcula `risk_score` (0–1000) y `risk_band` (`LOW`/`MEDIUM`/`HIGH`) con
   aritmética `Decimal` pura (`calculate_risk_score`), sin loops.
4. Responde `200`:
   ```json
   {"partner_ref":"partner-01","profile_ref":"profile-00000000-0000-4000-8000-000000000101","risk_score":373,"risk_band":"MEDIUM","cache_status":"miss","profile_version":"synthetic-v1"}
   ```

### 5. De vuelta en `quotation-service`

1. Verifica que `partner_ref`/`profile_ref` de la respuesta coincidan con los
   de la solicitud original; si no, `503
   {"error":"service_unavailable","error_id":"..."}`.
2. Consulta PostgreSQL por la tarifa del socio (`annual_rate`, `fixed_fee`,
   `version`).
3. Calcula `monthly_premium` con aritmética `Decimal` pura
   (`calculate_monthly_premium`): monto solicitado × tarifa anual / 12,
   ajustado por un multiplicador de riesgo (`0,85 + risk_score/2000`) y uno
   de plazo (recargo si `term_months > 12`), más el cargo fijo, redondeado a
   2 decimales.
4. Genera `quotation_id` y `request_id` como UUIDv4 nuevos — el cliente nunca
   los provee ni los controla.

### 6. Qué devuelve al cliente

```json
{
  "quotation_id": "5b1c2e2e-1a2b-4c3d-8e4f-0123456789ab",
  "request_id": "b6a9c1d2-3e4f-4a5b-9c6d-fedcba987654",
  "partner_ref": "partner-01",
  "profile_ref": "profile-00000000-0000-4000-8000-000000000101",
  "currency": "COP",
  "monthly_premium": "123456.78",
  "risk_score": 373,
  "tariff_version": "v1"
}
```

`HTTP 200` viaja de vuelta pod → NLB → VPC Link → API Gateway → cliente. Los
errores posibles son `400` (validación), `503 {"error":"service_unavailable","error_id":...}`
(cualquier dependencia caída, mismatch de identidad del perfil, timeout) y
`413 {"error":"request_too_large"}` (body mayor a `MAX_REQUEST_BYTES`, 4.096
bytes por defecto en ambos servicios).

## Contratos

- `POST /api/v1/cotizaciones`: body JSON opcional. `{}` o un body vacío usa
  referencias sintéticas predeterminadas. Los campos admitidos son
  `partner_ref`, `profile_ref`, `requested_amount` y `term_months`.
- `POST /internal/v1/profiles/score`: contrato interno con `partner_ref` y
  `profile_ref`.
- `GET /health/live`, `GET /health/ready` y `GET /metrics` en ambos servicios.
- OpenFinanceMock (WireMock) recibe únicamente `POST /open-finance/v1/profiles`;
  su URL base se obtiene de `OPENFINANCEMOCK_URL`, nunca de una solicitud.

`partner_ref` está limitado a `partner-01` ... `partner-50`, lo que también
acota la cardinalidad de las métricas por socio. `profile_ref` tiene la forma
`profile-00000000-0000-4000-8000-<12 dígitos>` y debe estar dentro de los 100
perfiles sembrados para el socio indicado. Para `partner-N`, el sufijo válido
va de `N * 100 + 1` a `N * 100 + 100`. JMeter reutiliza los primeros 20 de esos
perfiles por socio. Una combinación fuera de ese conjunto devuelve 400 antes
de acceder a Redis o PostgreSQL. Ninguna referencia sintética se interpreta
como identidad o credencial. En AWS, la autenticación y las cuotas pertenecen
al API Gateway; el servicio de perfil debe permanecer accesible solo dentro de
la red del clúster.

## Ejecución local

```bash
cd services
./scripts/init-local-env.sh
docker compose --env-file .env.local up --build
```

Si el script detecta un `.env.local` del formato anterior, lo conserva y sale
con código 2. Muévelo a un respaldo fuera del repositorio y ejecuta de nuevo el
script; no reutilices la credencial administrativa como credencial runtime. El
script fuerza permisos `0600` incluso sobre un archivo existente y rechaza
enlaces simbólicos.

Solicitud mínima:

```bash
curl --fail-with-body \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{}' \
  http://127.0.0.1:8080/api/v1/cotizaciones
```

El inicializador de base de datos es no interactivo e idempotente. Desde la
imagen de cotizaciones se ejecuta con:

```bash
python -m app.seed
```

Requiere `DATABASE_ADMIN_URL`, `RUNTIME_DB_USER=solventa_runtime` y
`RUNTIME_DB_PASSWORD`. El valor de `SEED_PROFILES_PER_PARTNER` está fijado en
100 para conservar el contrato acotado de 5.000 perfiles. El Job crea o rota el
rol runtime de forma idempotente, revoca escritura y solo concede
`CONNECT`, `USAGE` y `SELECT` sobre las dos tablas sintéticas. Las aplicaciones
reciben por separado `DATABASE_URL` con ese usuario runtime; nunca deben recibir
la URL administrativa.

En Amazon RDS, tanto `DATABASE_ADMIN_URL` como `DATABASE_URL` deben incluir:

```text
sslmode=verify-full&sslrootcert=/etc/ssl/certs/aws-rds-global-bundle.pem
```

Las imágenes descargan el bundle global desde el trust store oficial de RDS y
detienen el build si no coincide con SHA-256
`e5bb2084ccf45087bda1c9bffdea0eb15ee67f0b91646106e466714f9de3c7e3`.
Cuando AWS rote el bundle, se debe descargar desde la URL oficial, verificar el
nuevo SHA-256 fuera del build y actualizar el mismo valor en ambos Dockerfiles.
La conexión local a `postgres` permanece sin TLS.

Para ElastiCache, `REDIS_URL` debe usar `rediss://`, incluir la contraseña y
terminar en `/0`; no se admiten query strings ni fragments. El Compose local
usa `redis://` autenticado dentro de su red interna.

## Parámetros operativos

- `DB_POOL_MIN`, `DB_POOL_MAX`, `REDIS_POOL_MAX`,
  `HTTP_POOL_MAX_CONNECTIONS` y `HTTP_POOL_MAX_KEEPALIVE` controlan depósitos.
- `HTTP_CONNECT_TIMEOUT_SECONDS`, `HTTP_READ_TIMEOUT_SECONDS`,
  `REDIS_CONNECT_TIMEOUT_SECONDS` y `REDIS_READ_TIMEOUT_SECONDS` fijan límites.
- `CACHE_TTL_SECONDS` vale 900 por defecto; `CACHE_TTL_JITTER_SECONDS` distribuye
  vencimientos de manera determinista.

Los logs son JSON y omiten cuerpos, credenciales y URLs. La imagen ejecuta
Gunicorn como UID/GID 10001 con un worker por defecto, de modo que el escalado
se produce entre pods y las métricas de cada pod no se fragmentan entre varios
procesos.
