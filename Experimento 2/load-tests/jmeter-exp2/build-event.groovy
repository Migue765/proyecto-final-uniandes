import java.util.UUID

// Deterministic, non-cryptographic traffic shaping is fine here (this only
// picks which synthetic values a smoke request carries, never security
// material). vars is thread-local, so this counter is per virtual user.
// Every 10th iteration is deliberately tampered downstream, in
// hmac_sign.groovy, to exercise the 400 invalid_signature path.
int iteration = (vars.get('smoke_iteration_counter') ?: '0') as int
iteration += 1
vars.put('smoke_iteration_counter', Integer.toString(iteration))
boolean tamper = (iteration % 10 == 0)

String externalEventId = 'smoke-' + UUID.randomUUID().toString()
long timestamp = System.currentTimeMillis() / 1000L
String partitionKey = 'riesgo-' + (ctx.getThreadNum() % 20)

def tipos = ['sismo', 'huracan', 'vuelo_retrasado', 'inundacion']
String tipo = tipos[ctx.getThreadNum() % tipos.size()]
String magnitud = String.format('%.2f', 1.0d + (ctx.getThreadNum() % 9))
String umbral = '5.00'
String sumaAsegurada = '100000.00'

// Keys must stay in alphabetical order with no extra whitespace: this must
// byte-for-byte match services/ingreso-service/app/security.py's
// json.dumps(payload, sort_keys=True, separators=(",", ":")) canonicalization.
String payloadJson = '{"magnitud":"' + magnitud + '","suma_asegurada":"' + sumaAsegurada +
    '","tipo_evento_parametrico":"' + tipo + '","umbral_activacion":"' + umbral + '"}'

vars.put('external_event_id', externalEventId)
vars.put('timestamp', Long.toString(timestamp))
vars.put('partition_key', partitionKey)
vars.put('payload_json', payloadJson)
vars.put('tamper_signature', tamper ? 'true' : 'false')
