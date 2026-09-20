import groovy.json.JsonSlurper

import java.nio.charset.StandardCharsets
import java.time.OffsetDateTime
import java.util.Arrays
import java.util.concurrent.TimeUnit

class SolventaTemporaryAwsCredentials {
    private final String accessKeyId
    private final char[] secretAccessKey
    private final char[] sessionToken
    private final long expirationEpochSecond

    SolventaTemporaryAwsCredentials(
        String accessKeyId,
        String secretAccessKey,
        String sessionToken,
        long expirationEpochSecond
    ) {
        this.accessKeyId = accessKeyId
        this.secretAccessKey = secretAccessKey.toCharArray()
        this.sessionToken = sessionToken.toCharArray()
        this.expirationEpochSecond = expirationEpochSecond
    }

    String getAccessKeyId() {
        accessKeyId
    }

    String getSecretAccessKey() {
        new String(secretAccessKey)
    }

    String getSessionToken() {
        new String(sessionToken)
    }

    long getExpirationEpochSecond() {
        expirationEpochSecond
    }

    void clear() {
        Arrays.fill(secretAccessKey, (char) 0)
        Arrays.fill(sessionToken, (char) 0)
    }

    @Override
    String toString() {
        '[redacted temporary AWS credentials]'
    }
}

final String credentialsKey = 'solventa.runtime.aws.credentials'
def previousCredentials = props.remove(credentialsKey)
if (previousCredentials != null) {
    try {
        previousCredentials.clear()
    } catch (Exception ignored) {
        // The next validated bundle replaces any incompatible in-memory value.
    }
}

String failureCode = 'CONFIGURATION_INVALID'
String failureMessage = 'The JMeter AWS credential configuration is invalid.'

try {
    String awsCliPath = props.getProperty('aws_cli_path', '')
    String awsProfile = props.getProperty('aws_profile', '')
    String awsRegion = props.getProperty('aws_region', '')
    String expectedAccount = props.getProperty('expected_aws_account_id', '')
    String expectedArn = props.getProperty('expected_aws_principal_arn', '')

    File awsCli = new File(awsCliPath)
    if (!awsCli.isAbsolute() || !awsCli.isFile() || !awsCli.canExecute()) {
        throw new IllegalArgumentException('AWS CLI path is not an executable absolute file')
    }
    if (!(awsProfile ==~ /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/)) {
        throw new IllegalArgumentException('AWS profile name is invalid')
    }
    if (!(awsRegion ==~ /^[a-z0-9-]{3,32}$/)) {
        throw new IllegalArgumentException('AWS region is invalid')
    }
    if (!(expectedAccount ==~ /^\d{12}$/)) {
        throw new IllegalArgumentException('Expected AWS account is invalid')
    }
    if (!(expectedArn ==~ /^arn:aws:iam::\d{12}:user\/[A-Za-z0-9+=,.@_-]{1,64}$/)) {
        throw new IllegalArgumentException('Expected AWS principal ARN is invalid')
    }

    int durationSeconds = Integer.parseInt(props.getProperty('gui_duration_seconds', '600'))
    int marginSeconds = Integer.parseInt(props.getProperty('credential_ttl_margin_seconds', '60'))
    if (durationSeconds < 1 || durationSeconds > 86400 || marginSeconds < 60 || marginSeconds > 3600) {
        throw new IllegalArgumentException('Credential lifetime parameters are outside allowed bounds')
    }

    def runAws = { List<String> serviceArguments ->
        List<String> command = [
            awsCli.canonicalPath,
            '--profile', awsProfile,
            '--region', awsRegion,
            '--no-cli-pager',
            '--cli-connect-timeout', '10',
            '--cli-read-timeout', '20'
        ] + serviceArguments

        ProcessBuilder builder = new ProcessBuilder(command)
        Map<String, String> processEnvironment = builder.environment()
        processEnvironment.remove('AWS_ACCESS_KEY_ID')
        processEnvironment.remove('AWS_SECRET_ACCESS_KEY')
        processEnvironment.remove('AWS_SESSION_TOKEN')
        processEnvironment.remove('AWS_CREDENTIAL_EXPIRATION_EPOCH')

        Process process = builder.start()
        if (!process.waitFor(30, TimeUnit.SECONDS)) {
            process.destroyForcibly()
            throw new IllegalStateException('AWS CLI command timed out')
        }

        byte[] stdoutBytes = process.inputStream.readAllBytes()
        byte[] stderrBytes = process.errorStream.readAllBytes()
        try {
            if (process.exitValue() != 0 || stdoutBytes.length == 0 || stdoutBytes.length > 65536) {
                throw new IllegalStateException('AWS CLI command failed')
            }
            new String(stdoutBytes, StandardCharsets.UTF_8)
        } finally {
            Arrays.fill(stdoutBytes, (byte) 0)
            Arrays.fill(stderrBytes, (byte) 0)
        }
    }

    failureCode = 'AWS_SESSION_UNAVAILABLE'
    failureMessage = 'The solventa-lab AWS login session is unavailable.'
    def identity = new JsonSlurper().parseText(
        runAws(['sts', 'get-caller-identity', '--output', 'json'])
    )

    failureCode = 'AWS_IDENTITY_MISMATCH'
    failureMessage = 'The active AWS identity is not the allowed Solventa operator.'
    if (!(identity instanceof Map) || identity.Account != expectedAccount || identity.Arn != expectedArn) {
        throw new IllegalStateException('AWS identity does not match the allowed operator')
    }

    failureCode = 'AWS_CREDENTIAL_EXPORT_FAILED'
    failureMessage = 'AWS CLI could not export temporary credentials from solventa-lab.'
    def exported = new JsonSlurper().parseText(
        runAws(['configure', 'export-credentials', '--format', 'process'])
    )

    failureCode = 'AWS_CREDENTIAL_EXPORT_INVALID'
    failureMessage = 'AWS CLI returned an invalid temporary credential response.'
    if (!(exported instanceof Map) || exported.Version != 1) {
        throw new IllegalStateException('AWS credential response has an invalid schema')
    }

    String accessKeyId = exported.AccessKeyId instanceof String ? exported.AccessKeyId : ''
    String secretAccessKey = exported.SecretAccessKey instanceof String ? exported.SecretAccessKey : ''
    String sessionToken = exported.SessionToken instanceof String ? exported.SessionToken : ''
    String expiration = exported.Expiration instanceof String ? exported.Expiration : ''
    if (!(accessKeyId ==~ /^[A-Z0-9]{16,128}$/) ||
        secretAccessKey.length() < 16 || secretAccessKey.length() > 256 ||
        sessionToken.length() < 16 || sessionToken.length() > 8192 ||
        expiration.isEmpty()) {
        throw new IllegalStateException('AWS credential response has invalid fields')
    }

    long expirationEpochSecond = OffsetDateTime.parse(expiration).toInstant().epochSecond
    long remainingSeconds = expirationEpochSecond - Math.floorDiv(System.currentTimeMillis(), 1000L)
    long requiredSeconds = durationSeconds + marginSeconds
    if (remainingSeconds < requiredSeconds) {
        failureCode = 'AWS_CREDENTIAL_TTL_INSUFFICIENT'
        failureMessage = 'Temporary AWS credentials have ' + Math.max(0L, remainingSeconds) +
            ' seconds remaining; ' + requiredSeconds + ' seconds are required for this run.'
        throw new IllegalStateException('AWS credentials do not cover the complete test window')
    }

    props.put(
        credentialsKey,
        new SolventaTemporaryAwsCredentials(
            accessKeyId,
            secretAccessKey,
            sessionToken,
            expirationEpochSecond
        )
    )

    SampleResult.setSuccessful(true)
    SampleResult.setResponseCode('200')
    SampleResult.setResponseMessage('AWS credentials refreshed and validated in memory')
    SampleResult.setResponseData('Temporary AWS credentials are ready; values are redacted.', 'UTF-8')
    SampleResult.setIgnore()
} catch (Exception ignored) {
    props.remove(credentialsKey)
    SampleResult.setSuccessful(false)
    SampleResult.setResponseCode('AUTH_' + failureCode)
    SampleResult.setResponseMessage(failureMessage)
    SampleResult.setResponseData(
        failureMessage + ' No traffic was sent. Run aws login --profile solventa-lab --region us-east-1, then use the global Play button.',
        'UTF-8'
    )
    log.error(
        'AWS credential setup stopped before traffic: {}; no credential values were logged or stored',
        failureCode
    )
    ctx.getEngine()?.stopTest(true)
}
