import groovy.json.JsonSlurper

import java.nio.charset.StandardCharsets
import java.util.Arrays
import java.util.concurrent.TimeUnit

final String allowedAccount = '969325258550'
final String allowedPrincipalArn =
    'arn:aws:iam::969325258550:user/solventa-terraform-operator'
final Map<Integer, Integer> expectedThreadsByRpm = [
    (500): 50,
    (2000): 50,
    (5000): 125,
    (10000): 250,
    (25000): 625,
    (50000): 1250
]

String failureCode = 'CONFIGURATION_INVALID'
String failureMessage = 'The capacity-step JMeter configuration is invalid.'

try {
    String confirmation = props.getProperty('confirm_capacity_step', '')
    int targetRpm = Integer.parseInt(props.getProperty('target_rpm', '0'))
    int threads = Integer.parseInt(props.getProperty('gui_threads', '0'))
    int rampSeconds = Integer.parseInt(props.getProperty('gui_ramp_seconds', '0'))
    int stableSeconds = Integer.parseInt(props.getProperty('capacity_stable_seconds', '0'))
    int totalDurationSeconds = Integer.parseInt(props.getProperty('gui_duration_seconds', '0'))
    int connectTimeoutMs = Integer.parseInt(props.getProperty('connect_timeout_ms', '0'))
    int responseTimeoutMs = Integer.parseInt(props.getProperty('response_timeout_ms', '0'))
    int rateMarginPercent = Integer.parseInt(
        props.getProperty('gateway_rate_margin_percent', '0')
    )
    int burstSeconds = Integer.parseInt(props.getProperty('gateway_burst_seconds', '0'))
    String targetUrl = props.getProperty('target_url', '')
    String restApiId = props.getProperty('rest_api_id', '')
    String stageName = props.getProperty('api_stage', '')
    String awsCliPath = props.getProperty('aws_cli_path', '')
    String awsProfile = props.getProperty('aws_profile', '')
    String awsRegion = props.getProperty('aws_region', '')
    String expectedAccount = props.getProperty('expected_aws_account_id', '')
    String expectedArn = props.getProperty('expected_aws_principal_arn', '')

    if (confirmation != 'SOLVENTA_EXP1_CAPACITY_STEP') {
        throw new IllegalArgumentException('explicit capacity-step confirmation is missing')
    }
    if (!expectedThreadsByRpm.containsKey(targetRpm)) {
        throw new IllegalArgumentException(
            'target_rpm must be one of 500, 2000, 5000, 10000, 25000 or 50000'
        )
    }
    if (threads != expectedThreadsByRpm[targetRpm]) {
        throw new IllegalArgumentException('gui_threads does not match the selected target_rpm')
    }
    if (rampSeconds != 5 || stableSeconds < 60 || stableSeconds > 1800 ||
        totalDurationSeconds != rampSeconds + stableSeconds) {
        throw new IllegalArgumentException(
            'timeline must use a 5-second transition and 60-1800 stable seconds'
        )
    }
    if (connectTimeoutMs != 2000 || responseTimeoutMs != 5000) {
        throw new IllegalArgumentException('HTTP timeouts must remain fixed at 2000/5000 ms')
    }
    if (rateMarginPercent != 20 || burstSeconds != 2) {
        throw new IllegalArgumentException(
            'gateway margins must remain fixed at 20 percent rate and 2 seconds burst'
        )
    }
    if (!(restApiId ==~ /^[a-z0-9]{10}$/) || stageName != 'lab') {
        throw new IllegalArgumentException('API Gateway identifier or stage is invalid')
    }
    if (awsProfile != 'solventa-lab' || awsRegion != 'us-east-1') {
        throw new IllegalArgumentException('AWS profile or region is outside the experiment boundary')
    }
    if (expectedAccount != allowedAccount || expectedArn != allowedPrincipalArn) {
        throw new IllegalArgumentException('expected AWS identity is outside the experiment boundary')
    }

    URI target = new URI(targetUrl)
    String expectedHost = restApiId + '.execute-api.' + awsRegion + '.amazonaws.com'
    String expectedPath = '/' + stageName + '/api/v1/cotizaciones'
    if (target.scheme != 'https' || target.host != expectedHost || target.port != -1 ||
        target.rawPath != expectedPath || target.rawQuery != null || target.rawFragment != null) {
        throw new IllegalArgumentException(
            'target_url is not the exact Solventa quotation API Gateway endpoint'
        )
    }

    File awsCli = new File(awsCliPath)
    if (!awsCli.isAbsolute() || !awsCli.isFile() || !awsCli.canExecute()) {
        throw new IllegalArgumentException('AWS CLI path is not an executable absolute file')
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
            if (process.exitValue() != 0 || stdoutBytes.length == 0 ||
                stdoutBytes.length > 65536) {
                throw new IllegalStateException('AWS CLI command failed')
            }
            new String(stdoutBytes, StandardCharsets.UTF_8)
        } finally {
            Arrays.fill(stdoutBytes, (byte) 0)
            Arrays.fill(stderrBytes, (byte) 0)
        }
    }

    failureCode = 'AWS_IDENTITY_UNAVAILABLE'
    failureMessage = 'The active AWS identity could not be verified; no traffic was sent.'
    def identity = new JsonSlurper().parseText(
        runAws(['sts', 'get-caller-identity', '--output', 'json'])
    )

    failureCode = 'AWS_IDENTITY_MISMATCH'
    failureMessage = 'The active AWS identity is not the allowed Solventa operator; no traffic was sent.'
    if (!(identity instanceof Map) || identity.Account != allowedAccount ||
        identity.Arn != allowedPrincipalArn) {
        throw new IllegalStateException('AWS identity does not match the allowed operator')
    }

    failureCode = 'GATEWAY_CONFIGURATION_UNAVAILABLE'
    failureMessage = 'API Gateway limits could not be read; no traffic was sent.'
    def account = new JsonSlurper().parseText(
        runAws(['apigateway', 'get-account', '--output', 'json'])
    )
    def stage = new JsonSlurper().parseText(
        runAws([
            'apigateway', 'get-stage',
            '--rest-api-id', restApiId,
            '--stage-name', stageName,
            '--output', 'json'
        ])
    )

    Number accountRate = account?.throttleSettings?.rateLimit as Number
    Number accountBurst = account?.throttleSettings?.burstLimit as Number
    def globalMethodSettings = stage?.methodSettings?.get('*/*')
    def quotationPostSettings = stage?.methodSettings?.get(
        '~1api~1v1~1cotizaciones/POST'
    )
    Number globalRate = globalMethodSettings?.throttlingRateLimit as Number
    Number globalBurst = globalMethodSettings?.throttlingBurstLimit as Number
    Number methodRate = quotationPostSettings?.throttlingRateLimit as Number
    Number methodBurst = quotationPostSettings?.throttlingBurstLimit as Number

    if (accountRate == null || accountBurst == null ||
        accountRate.doubleValue() <= 0d || accountBurst.doubleValue() <= 0d) {
        throw new IllegalStateException('account API Gateway throttle values are absent or invalid')
    }

    List<Number> applicableRates = [accountRate]
    List<Number> applicableBursts = [accountBurst]
    if (globalRate != null) applicableRates.add(globalRate)
    if (globalBurst != null) applicableBursts.add(globalBurst)
    if (methodRate != null) applicableRates.add(methodRate)
    if (methodBurst != null) applicableBursts.add(methodBurst)
    double effectiveRate = applicableRates.collect { it.doubleValue() }.min()
    double effectiveBurst = applicableBursts.collect { it.doubleValue() }.min()

    double targetRps = targetRpm / 60.0d
    int requiredRateRps = (int) Math.ceil(
        targetRps * (1.0d + rateMarginPercent / 100.0d)
    )
    int requiredBurst = (int) Math.ceil(targetRps * burstSeconds)

    failureCode = 'GATEWAY_CAPACITY_INSUFFICIENT'
    failureMessage = 'API Gateway is not ready for ' + targetRpm + ' RPM: effective limit ' +
        effectiveRate + ' RPS/' + effectiveBurst + ' burst; required at least ' +
        requiredRateRps + ' RPS/' + requiredBurst +
        ' burst. No traffic was sent.'
    if (effectiveRate < requiredRateRps || effectiveBurst < requiredBurst) {
        throw new IllegalStateException('API Gateway throttle is below the capacity-step threshold')
    }

    props.remove('solventa.50k.measured.started.epoch_ms')

    SampleResult.setSuccessful(true)
    SampleResult.setResponseCode('200')
    SampleResult.setResponseMessage('Capacity-step preflight passed')
    SampleResult.setResponseData(
        'Target, identity boundary, endpoint and API Gateway throttles are ready.',
        'UTF-8'
    )
    SampleResult.setIgnore()
} catch (Exception ignored) {
    props.remove('solventa.50k.measured.started.epoch_ms')
    def runtimeCredentials = props.remove('solventa.runtime.aws.credentials')
    if (runtimeCredentials != null) {
        try {
            runtimeCredentials.clear()
        } catch (Exception cleanupIgnored) {
            // Removing the property is the required cleanup boundary.
        }
    }
    SampleResult.setSuccessful(false)
    SampleResult.setResponseCode('PREFLIGHT_' + failureCode)
    SampleResult.setResponseMessage(failureMessage)
    SampleResult.setResponseData(failureMessage, 'UTF-8')
    log.error('Capacity-step preflight stopped before traffic: {}', failureCode)
    ctx.getEngine()?.stopTest(true)
}
