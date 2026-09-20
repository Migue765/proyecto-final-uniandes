// Reads one row of corpus_export.csv (via CSV Data Set Config) and stamps
// it with the current time. Signing at request time — not baking in a
// timestamp from generate_corpus.py — is what lets this CSV be run at any
// point without going stale against ingreso's SIGNATURE_MAX_SKEW_SECONDS:
// the signature covers the timestamp, so it must be computed together with
// it, never precomputed once and reused later.
long timestamp = System.currentTimeMillis() / 1000L
vars.put('timestamp', Long.toString(timestamp))

// Keys must stay in alphabetical order with no extra whitespace: this must
// byte-for-byte match services/ingreso-service/app/security.py's
// json.dumps(payload, sort_keys=True, separators=(",", ":")) canonicalization,
// same as build-event.groovy uses for its synthetic events.
String payloadJson = '{"magnitud":"' + vars.get('magnitud') + '","suma_asegurada":"' +
    vars.get('suma_asegurada') + '","tipo_evento_parametrico":"' +
    vars.get('tipo_evento_parametrico') + '","umbral_activacion":"' +
    vars.get('umbral_activacion') + '"}'
vars.put('payload_json', payloadJson)

// Never tamper corpus-driven requests; hmac_sign.groovy's own tamper branch
// is only exercised by the synthetic smoke test.
vars.put('tamper_signature', 'false')
