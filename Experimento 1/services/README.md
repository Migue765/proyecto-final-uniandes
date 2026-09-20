# Servicios mock del experimento 1

Esta carpeta implementa el recorrido real que se someterá a carga:

`cliente -> quotation-service -> profile-service -> Redis/PostgreSQL/WireMock`

Los datos son exclusivamente sintéticos. Las dependencias, depósitos de
conexiones, caché, consultas y trabajo de CPU sí son reales. Los servicios no
usan `sleep` para fabricar latencia.

## Contratos

- `POST /api/v1/cotizaciones`: body JSON opcional. `{}` o un body vacío usa
  referencias sintéticas predeterminadas. Los campos admitidos son
  `partner_ref`, `profile_ref`, `requested_amount` y `term_months`.
- `POST /internal/v1/profiles/score`: contrato interno con `partner_ref` y
  `profile_ref`.
- `GET /health/live`, `GET /health/ready` y `GET /metrics` en ambos servicios.
- WireMock recibe únicamente `POST /open-finance/v1/profiles`; su URL base se
  obtiene de `WIREMOCK_URL`, nunca de una solicitud.

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

## Calibración

- `QUOTE_CPU_ITERATIONS` y `PROFILE_CPU_ITERATIONS` controlan trabajo de hash
  determinista por solicitud.
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
