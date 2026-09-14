import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.time.ZoneOffset
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

String authMode = props.getProperty('auth_mode', 'aws_iam')
if (authMode == 'none') {
    vars.put('sigv4_authorization', '')
    vars.put('sigv4_amz_date', '')
    vars.put('sigv4_session_token', '')
    return
}
if (authMode != 'aws_iam') {
    throw new IllegalArgumentException('Unsupported auth_mode')
}

def runtimeCredentials = props.get('solventa.runtime.aws.credentials')
String accessKey
String secretKey
String sessionToken

if (runtimeCredentials != null) {
    try {
        long expirationEpochSecond = runtimeCredentials.getExpirationEpochSecond()
        if (expirationEpochSecond <= (System.currentTimeMillis() / 1000L) + 30L) {
            ctx.getEngine()?.stopTest(true)
            throw new IllegalStateException('Temporary AWS credentials expired during the test')
        }
        accessKey = runtimeCredentials.getAccessKeyId()
        secretKey = runtimeCredentials.getSecretAccessKey()
        sessionToken = runtimeCredentials.getSessionToken()
    } catch (Exception ignored) {
        ctx.getEngine()?.stopTest(true)
        throw new IllegalStateException('In-memory AWS credentials are invalid')
    }
} else {
    accessKey = System.getenv('AWS_ACCESS_KEY_ID')
    secretKey = System.getenv('AWS_SECRET_ACCESS_KEY')
    sessionToken = System.getenv('AWS_SESSION_TOKEN')
}
if (!accessKey || !secretKey || !sessionToken) {
    ctx.getEngine()?.stopTest(true)
    throw new IllegalStateException('Temporary AWS credentials are required for SigV4')
}

String region = props.getProperty('aws_region', 'us-east-1')
String service = props.getProperty('aws_service', 'execute-api')
URI target = new URI(props.getProperty('target_url'))
if (target.scheme != 'https' || target.rawQuery != null || target.rawFragment != null) {
    throw new IllegalArgumentException('SigV4 target must be HTTPS without query or fragment')
}

String host = target.host
int port = target.port
if (port != -1 && port != 443) {
    host += ':' + port
}
String canonicalUri = target.rawPath ?: '/'
String payload = vars.get('request_body')
if (payload == null) {
    throw new IllegalStateException('request_body must be created before SigV4 signing')
}

def sha256Hex = { String value ->
    MessageDigest.getInstance('SHA-256')
        .digest(value.getBytes(StandardCharsets.UTF_8))
        .collect { String.format('%02x', it & 0xff) }
        .join()
}
def hmac = { byte[] key, String value ->
    Mac mac = Mac.getInstance('HmacSHA256')
    mac.init(new SecretKeySpec(key, 'HmacSHA256'))
    mac.doFinal(value.getBytes(StandardCharsets.UTF_8))
}

ZonedDateTime now = ZonedDateTime.now(ZoneOffset.UTC)
String amzDate = now.format(DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'"))
String dateStamp = now.format(DateTimeFormatter.ofPattern('yyyyMMdd'))
String canonicalHeaders = 'content-type:application/json\n' +
    'host:' + host + '\n' +
    'x-amz-date:' + amzDate + '\n' +
    'x-amz-security-token:' + sessionToken.trim() + '\n'
String signedHeaders = 'content-type;host;x-amz-date;x-amz-security-token'
String canonicalRequest = 'POST\n' + canonicalUri + '\n\n' + canonicalHeaders + '\n' +
    signedHeaders + '\n' + sha256Hex(payload)
String scope = dateStamp + '/' + region + '/' + service + '/aws4_request'
String stringToSign = 'AWS4-HMAC-SHA256\n' + amzDate + '\n' + scope + '\n' +
    sha256Hex(canonicalRequest)

byte[] dateKey = hmac(('AWS4' + secretKey).getBytes(StandardCharsets.UTF_8), dateStamp)
byte[] regionKey = hmac(dateKey, region)
byte[] serviceKey = hmac(regionKey, service)
byte[] signingKey = hmac(serviceKey, 'aws4_request')
String signature = hmac(signingKey, stringToSign)
    .collect { String.format('%02x', it & 0xff) }
    .join()

vars.put('sigv4_amz_date', amzDate)
vars.put('sigv4_session_token', sessionToken.trim())
vars.put('sigv4_authorization', 'AWS4-HMAC-SHA256 Credential=' + accessKey + '/' + scope +
    ', SignedHeaders=' + signedHeaders + ', Signature=' + signature)
