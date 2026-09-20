import java.nio.charset.StandardCharsets
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

String secret = props.getProperty('hmac_shared_secret', System.getenv('HMAC_SHARED_SECRET'))
if (!secret) {
    ctx.getEngine()?.stopTest(true)
    throw new IllegalStateException(
        'Set -Jhmac_shared_secret=<secret> or the HMAC_SHARED_SECRET environment variable'
    )
}

String externalEventId = vars.get('external_event_id')
String timestamp = vars.get('timestamp')
String payloadJson = vars.get('payload_json')
String canonical = externalEventId + '|' + timestamp + '|' + payloadJson

Mac mac = Mac.getInstance('HmacSHA256')
mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), 'HmacSHA256'))
byte[] digest = mac.doFinal(canonical.getBytes(StandardCharsets.UTF_8))
String signatureHex = digest.collect { String.format('%02x', it & 0xff) }.join()

boolean tamper = vars.get('tamper_signature') == 'true'
if (tamper) {
    // Flip one hex nibble: still well-formed (64 lowercase hex chars) but
    // wrong, so the request is rejected for signature reasons specifically,
    // not because it failed basic shape validation.
    char first = signatureHex.charAt(0)
    String replacement = (first == '0') ? '1' : '0'
    signatureHex = replacement + signatureHex.substring(1)
}

vars.put('signature', signatureHex)
vars.put('expected_status', tamper ? '400' : '202')
vars.put(
    'request_body',
    '{"external_event_id":"' + externalEventId + '","timestamp":' + timestamp +
        ',"partition_key":"' + vars.get('partition_key') + '","signature":"' + signatureHex +
        '","payload":' + payloadJson + '}'
)
