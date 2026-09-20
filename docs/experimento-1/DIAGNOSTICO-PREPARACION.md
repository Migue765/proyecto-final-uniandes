# Diagnóstico de preparación — corrida GUI de 500 RPM

Revisión estática realizada el `2026-09-14` sobre la rama
`feature/experimento-500-a-50k`, commit `e12f67e` (merge del PR #103).
No se ejecutó carga, no se contactó AWS y no se modificó infraestructura.

Documentos relacionados: [runbook completo](EJECUCION.md) ·
[catálogo de experimentos](../../documentos/semana-5/solventa_experimentos_replanteados.md).

## 1. Qué prueba es y qué prueba no es

La prueba que se va a ejecutar localmente es el **diagnóstico GUI**, no el
baseline oficial. Son dos artefactos distintos:

| | Diagnóstico GUI | Baseline de tres corridas |
|---|---|---|
| Lanzador | `scripts/experiment-1/open-jmeter-gui.sh` | `scripts/experiment-1/run-local.sh` |
| Plan | `load-tests/jmeter/gui-500rpm.jmx` | `load-tests/jmeter/experiment-1.jmx` |
| Motor | JMeter GUI de Homebrew, en macOS | JMeter 5.6.3 en contenedor `linux/amd64` |
| Duración | 600 s de carga medida, sin warm-up ni cooldown | 3 × (60 s warm-up + 480 s medidos + 30 s cooldown + 30 s observación) |
| Muestras esperadas | 5.000 (500 RPM × 10 min) | 4.000 por corrida, tolerancia ±40 |
| Evidencia persistida | **ninguna** | JTL + reporte HTML + snapshots + análisis |
| Sirve para | ver el recorrido en pantalla, confirmar plomería SigV4, leer percentiles y señal de HPA | emitir veredicto de Fase A |

El diagnóstico GUI es observable e interactivo: `View Results Tree`,
`View Results in Table` y `Aggregate Report`. Eso es su valor y también su
límite.

### 1.1 Parámetros efectivos del diagnóstico

Todos vienen fijados por el lanzador, ninguno queda al criterio del operador:

- 50 hilos, ramp de 5 s, `scheduler=true`, duración 600 s — el plan se detiene
  solo, no hay riesgo de bucle infinito;
- `ConstantThroughputTimer` con `calcMode=4`, es decir 500 RPM **agregadas y
  compartidas** entre los 50 hilos, no 500 por hilo. Equivale a 8,33 RPS y a
  10 solicitudes por minuto por hilo;
- `connect_timeout=2000 ms`, `response_timeout=5000 ms`, `keepalive` activo y
  cero retries de cliente (`httpclient4.retrycount=0`);
- SigV4 sobre `execute-api`, con credenciales temporales resueltas en memoria
  por `refresh-aws-credentials.groovy` al presionar Play.

8,33 RPS consume cerca del 42 % del límite de 20 RPS de API Gateway, con burst
de 40 disponible. El borde no es el cuello de botella a esta tasa.

## 2. Lo que resolvió el merge #103

Tres defectos que estaban abiertos en la revisión anterior ya están cerrados en
el código; no hay que volver a tocarlos:

1. **Guarda de independencia entre corridas.** `run-local.sh` ahora tiene
   `wait_for_baseline_capacity()`, que exige `spec.replicas`, `readyReplicas`,
   `availableReplicas`, `currentReplicas` y `desiredReplicas` iguales a 2 en
   Cotización y Perfilamiento antes de cada repetición, con timeout de 600 s.
   Antes era una verificación manual sobre `autoscaling.jsonl`.
2. **Ventana del monitor.** Dejó de estar fija en 7.500 s. Ahora se calcula:
   `(60+480+30+30) × 3 + 600 × 2 + 300 = 3.300 s`. Con la duración anterior de
   121,5 min el monitor moría antes de terminar la corrida 3 y perdía la
   evidencia final de HPA.
3. **Expiración de credenciales a mitad del grupo.** Cada corrida exige ahora
   `60+480+30+30+120 = 720 s` de vida restante, no 2.730 s. Con el protocolo
   anterior la corrida 2 arrancaba a los 41 min con ~19 min de sesión y
   abortaba después de haber generado carga real.

El protocolo oficial se acortó de 30 a 8 minutos medidos, y `run.sh` y
`run-local.sh` coinciden en 60/480 — no hay contradicción entre la guarda del
contenedor y los valores por defecto del orquestador.

## 3. Bloqueantes antes de presionar Play

| # | Bloqueante | Verificación | Efecto si se ignora |
|---|---|---|---|
| B1 | Sesión AWS | `open-jmeter-gui.sh` corre `verify_aws_identity` y exige exactamente `arn:aws:iam::969325258550:user/solventa-terraform-operator` | El script aborta antes de abrir la GUI |
| B2 | IP pública en la resource policy de API Gateway | Comparar la IP pública actual con la allowlist antes de abrir la GUI | 403 en el 100 % de las 5.000 muestras |
| B3 | Rol de mínimo privilegio del generador | No existe todavía | La GUI hereda la sesión del operador, muy superior a `execute-api:Invoke` |

B1 y B2 son operativos y se resuelven en minutos. **B3 no se resuelve hoy**, y
es la razón por la cual esta corrida es un ensayo técnico: mientras el generador
firme con la identidad del operador, la evidencia no califica como oficial. Es
la misma brecha ya documentada en la sección 3.2 del runbook (CWE-266,
privilegio excesivo asignado a un proceso de carga).

Durante la corrida no se debe cambiar de red, activar o desactivar VPN. Si la IP
pública cambia a mitad del tráfico, API Gateway empieza a rechazar y la corrida
se anota como abortada, no se corrige en caliente.

## 4. Hallazgos

### 4.1 El diagnóstico GUI no deja evidencia — severidad alta

`open-jmeter-gui.sh` no pasa `-l`, no arranca `monitor.sh` y no llama a
`collect.sh`. Consecuencias concretas:

- no se escribe JTL, así que `analyze.py` no tiene entrada y no habrá
  `analysis.json` ni veredicto reproducible;
- **no se captura ningún snapshot de HPA, deployments, pods ni Metrics Server.**
  Si el objetivo incluye ver si el HPA pasa de 2 a 3 réplicas, hay que levantar
  `monitor.sh` en una segunda terminal antes de presionar Play, o la señal se
  pierde por completo;
- todo lo que muestre `Aggregate Report` vive solo en memoria de la GUI y
  desaparece al cerrar la ventana.

Para esta corrida eso es aceptable si se asume explícitamente que es un
diagnóstico visual. Deja de ser aceptable en el momento en que alguien quiera
citar el p95 que apareció en pantalla.

### 4.2 La carga golpea una sola clave — severidad alta

El preprocesador `Create visible synthetic request body` fija el mismo cuerpo
para los 50 hilos y las 5.000 muestras:

```
partner_ref = partner-01
profile_ref = profile-00000000-0000-4000-8000-000000000101
requested_amount = 10000000
term_months = 12
```

El contrato acepta ese cuerpo: `QuoteRequest` declara `requested_amount` y
`term_months` con esos mismos valores por defecto, y `validate_synthetic_pair`
confirma que el perfil `101` pertenece a la partición `101–200` de
`partner-01`. No hay riesgo de 422 masivo por campos extra.

Lo que sí cambia es qué se está midiendo:

- después de la primera solicitud, Redis sirve esa clave al 100 %, así que
  **no se ejercita la lectura de perfil en PostgreSQL ni WireMock**;
- la latencia observada es un piso optimista, no el baseline;
- en cambio, la señal de CPU **sí es representativa**: en
  `services/profile-service/app/application.py` el consumo sintético de
  `profile_cpu_iterations` ocurre después de la rama de caché, sin condicional,
  igual que en Cotización. Ambos servicios quemarían CPU en cada solicitud
  aunque el caché acierte.

Conclusión utilizable: **el diagnóstico GUI vale para calibrar CPU y observar el
HPA; no vale para reportar latencia de baseline.**

### 4.3 La corrida GUI precalienta una clave del baseline — severidad media

`profile-...000101` pertenece al rango `101–120` que usa la **corrida oficial 1**.
La calibración documentada evita esto a propósito usando perfiles `181–200`
(`-Jprofile_offset=80`); el plan GUI no lo hace.

El TTL de caché es de 900 s con jitter de hasta 60 s
(`services/profile-service/app/config.py`). Por lo tanto, después del
diagnóstico hay dos salidas limpias:

- esperar al menos 16 minutos antes de iniciar la corrida oficial 1, o
- cambiar el perfil del plan GUI a `profile-00000000-0000-4000-8000-000000000181`,
  que cae en el rango reservado para calibración.

Si no se hace ninguna de las dos, la corrida 1 arranca con una clave caliente
que las corridas 2 y 3 no tendrán, y se rompe la regla 6 de reproducibilidad.

### 4.4 `jmeter.log` quedó versionado — severidad media

El merge #103 agregó `load-tests/jmeter/jmeter.log` al repositorio, y
`load-tests/.gitignore` solo ignora `results/**`. Cualquier invocación manual de
`jmeter` desde ese directorio sin `-j` lo sobreescribe, deja `load-tests/` sucio
y entonces `run-local.sh` aborta el baseline con *"Refusing evidence runs while
services/ or load-tests/ has uncommitted changes"*.

`open-jmeter-gui.sh` está a salvo porque redirige con
`-j /private/tmp/solventa-jmeter-gui-500rpm.log`. El riesgo es el lanzamiento
manual. Limpieza sugerida: `git rm --cached load-tests/jmeter/jmeter.log` y
agregar `jmeter/*.log` a `load-tests/.gitignore`.

Relacionado: **no guardar el plan desde la GUI.** JMeter escribe un respaldo
junto al `.jmx` y eso también ensucia `load-tests/`.

### 4.5 El listener promete cuerpos que su configuración desactiva — severidad baja

El listener se llama `View Results Tree - response body`, pero su `saveConfig`
trae `responseData=false` y `responseDataOnError=false`. En modo GUI el cuerpo
normalmente se renderiza desde el resultado vivo en memoria, así que lo más
probable es que se vea bien. Conviene confirmarlo en la primera muestra: si el
panel de respuesta aparece vacío, esa bandera es la causa.

La redacción de credenciales sí está bien resuelta: el postprocesador
`Redact temporary AWS headers before listeners` reemplaza los headers de firma y
las variables `sigv4_*` antes de que cualquier listener los vea, y
`refresh-aws-credentials.groovy` mantiene secreto y token en `char[]` que limpia
al terminar, con `toString()` redactado (mitiga CWE-532, exposición de
credenciales en logs).

### 4.6 El runbook quedó desfasado del código — severidad media

`EJECUCION.md` sigue describiendo el protocolo anterior: 5 min de warm-up,
30 min medidos, 121 min 30 s de duración total y **15.000 muestras** por corrida
en la tabla de veredicto del paso A8. El código ya exige 60 s y 480 s.

Quien siga el documento literalmente va a chocar con
*"Experiment 1 warm-up is fixed at 60 seconds"*, y el criterio de 15.000
muestras es inalcanzable con 480 s medidos — el número correcto ahora es 4.000
±40. `analyze.py` no tiene este problema porque lee `target_rpm` y
`measured_seconds` del manifiesto.

### 4.7 Dos parámetros perdieron su guarda de inmutabilidad — severidad baja

`run.sh` ya no fija `COOLDOWN_SECONDS` ni
`POST_COOLDOWN_OBSERVATION_SECONDS`; solo conserva las guardas de warm-up,
ventana medida, RPM, socios, número de corridas y ramp. `run-local.sh` los pasa
en 30 y 30, así que en la práctica son estables, pero la garantía de protocolo
inmutable que declara el README ya no los cubre.

## 5. Correcciones aplicadas en esta sesión

Solo en `scripts/experiment-1/analyze.py`, las dos que autorizaste:

1. **Umbral de error estricto.** `valid_success_at_least_99_percent` con
   `>= 99.0` pasó a ser `valid_success_above_99_percent` con `> 99.0`. El ASR
   exige error técnico menor a 1 %, así que una corrida con exactamente 99,0 %
   de respuestas válidas ahora es `FAIL` en el JSON y no requiere corrección
   manual del veredicto.
2. **Separación de intentadas y completadas.** `completed_rpm` se deriva de
   `valid_count` en lugar de repetir `sample_count`. Se agregó el campo
   `rpm_basis`, una columna *RPM completadas* en el reporte Markdown y una
   verificación manual explícita para reconciliar ambas cifras contra las
   métricas `Count`, `4XXError`, `5XXError` y throttling de API Gateway, porque
   el JTL sigue viendo el tráfico solo desde el cliente.

El auto-test del analizador pasa y la ejecución contra la evidencia de
validación existente produce `analysis.json` y `analysis.md` correctos.

El `.gitignore` que iba a corregir ya venía resuelto en el merge #103: la raíz
recuperó `**/temp/*` y `services/.gitignore` volvió a existir. No hice cambios
ahí.

## 6. Secuencia sugerida

### Antes de abrir la GUI

```bash
cd /Users/mgomezalarco/Documents/laboratorio-analitica
export PATH="/opt/homebrew/bin:$PATH"
export AWS_PROFILE="solventa-lab"
export AWS_REGION="us-east-1"

# 1. Renovar sesión, sin crear access keys
/opt/homebrew/bin/aws login --profile "$AWS_PROFILE" --region "$AWS_REGION"

# 2. Confirmar identidad exacta
/opt/homebrew/bin/aws --profile "$AWS_PROFILE" --region "$AWS_REGION" \
  sts get-caller-identity --query '{Account:Account,Arn:Arn}' --output json

# 3. Validación estática, sin contactar AWS
scripts/experiment-1/validate.sh

# 4. Worktree limpio en las rutas que bloquean el baseline
git status --porcelain -- services load-tests deploy infra

# 5. Plomería extremo a extremo, una sola solicitud firmada sin retries
scripts/experiment-1/smoke.sh
```

Además, verificar que la IP pública actual siga en la allowlist de la resource
policy de API Gateway, y que Cotización y Perfilamiento estén en `2/2` Ready con
ambos HPA en 2–4 al 70 %.

### Si se quiere señal de HPA — segunda terminal, antes de Play

```bash
RUN_ID="exp1-gui-$(date -u +%Y%m%dT%H%M%SZ)" \
MONITOR_DURATION_SECONDS=900 \
SKIP_CONTEXT_UPDATE=true \
  scripts/experiment-1/monitor.sh
```

Sin esto no queda ningún registro de escalamiento.

### La corrida

```bash
caffeinate -dimsu scripts/experiment-1/open-jmeter-gui.sh
```

Presionar el **Play global**, nunca *Start Selected*: ese atajo omite el
`SetupThreadGroup` que resuelve las credenciales y el plan saldría sin firmar.

Durante los 10 minutos: computador conectado a energía, sin cambios de red, sin
otra carga significativa en la máquina ni en la cuenta, y CPU del host por
debajo del 80 %.

### Qué leer al terminar

- `Aggregate Report`: throughput y percentiles. Esperado 8,33 RPS y ~5.000
  muestras; una cifra materialmente menor significa que el generador o el borde
  no sostuvieron la tasa ofrecida.
- `View Results in Table`: latencia y `Connect` muestra a muestra.
- `View Results Tree`: confirmar en una muestra que el esquema de negocio llega
  completo y que los headers aparecen redactados.
- Si se levantó el monitor: `k8s/autoscaling.jsonl`, buscando
  `current_replicas` y `desired_replicas` de Cotización y Perfilamiento.

## 7. Qué se puede y qué no se puede concluir

Se puede concluir, con esta corrida:

- que el recorrido firmado atraviesa API Gateway, VPC Link, NLB, Cotización,
  Perfilamiento, PostgreSQL y Redis a 500 RPM agregadas sin errores de
  transporte;
- que la tasa ofrecida de 8,33 RPS se sostiene desde un generador local;
- una primera lectura de CPU por pod y de la decisión del HPA, útil para
  calibrar `QUOTE_CPU_ITERATIONS` y `PROFILE_CPU_ITERATIONS`, que siguen en
  150.000 como hipótesis sin congelar.

No se puede concluir:

- latencia de baseline, por la clave única de la sección 4.2;
- cumplimiento de `ASR-ESC-01`, que exige 50.506 RPM ofrecidas y las Fases B–E;
- nada con carácter de evidencia oficial, mientras el generador firme con la
  identidad del operador (B3).

Si el HPA no escala y los SLO se cumplen, la lectura correcta es *"500 RPM caben
en la capacidad inicial"*, no *"se demostró elasticidad"*.
