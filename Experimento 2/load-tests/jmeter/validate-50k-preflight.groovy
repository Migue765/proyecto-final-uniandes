import groovy.json.JsonSlurper

import java.nio.charset.StandardCharsets
import java.util.Arrays
import java.util.concurrent.TimeUnit

String failureCode = 'CONFIGURATION_INVALID'
String failureMessage = 'The 50k JMeter configuration is invalid.'

try {
    String confirmation = props.getProperty('confirm_high_load', '')
    int targetRpm = Integer.parseInt(props.getProperty('target_rpm', '0'))
    int threads = Integer.parseInt(props.getProperty('gui_threads', '0'))
    int measuredSeconds = Integer.parseInt(props.getProperty('measured_seconds', '0'))
    int measuredThreadSeconds = Integer.parseInt(props.getProperty('measured_thread_seconds', '0'))
    int baselineSeconds = Integer.parseInt(props.getProperty('baseline_seconds', '0'))
    int threadStartSeconds = Integer.parseInt(props.getProperty('gui_ramp_seconds', '0'))
    int totalDurationSeconds = Integer.parseInt(props.getProperty('gui_duration_seconds', '0'))
    int connectTimeoutMs = Integer.parseInt(props.getProperty('connect_timeout_ms', '0'))
    int responseTimeoutMs = Integer.parseInt(props.getProperty('response_timeout_ms', '0'))
    String targetUrl = props.getProperty('target_url', '')
    String restApiId = props.getProperty('rest_api_id', '')
    String stageName = props.getProperty('api_stage', '')
    String awsCliPath = props.getProperty('aws_cli_path', '')
    String awsProfile = props.getProperty('aws_profile', '')
    String awsRegion = props.getProperty('aws_region', '')
    int minimumRateRps = Integer.parseInt(props.getProperty('minimum_gateway_rate_rps', '1000'))
    int minimumBurst = Integer.parseInt(props.getProperty('minimum_gateway_burst', '2000'))

    if (confirmation != 'SOLVENTA_EXP1_50K') {
        throw new IllegalArgumentException('explicit high-load confirmation is missing')
    }
    if (!(targetRpm in [50000, 50506])) {
        throw new IllegalArgumentException('target_rpm must be 50000 or 50506')
    }
    if (threads < 527 || threads > 1000) {
        throw new IllegalArgumentException('gui_threads must be between 527 and 1000')
    }
    if (measuredSeconds != 600) {
        throw new IllegalArgumentException('measured_seconds must be exactly 600')
    }
    if (baselineSeconds != 60 || threadStartSeconds != 5 ||
        measuredThreadSeconds != measuredSeconds + threadStartSeconds ||
        totalDurationSeconds != baselineSeconds + measuredThreadSeconds) {
        throw new IllegalArgumentException('the effective test timeline must be 60 + 5 + 600 seconds')
    }
    if (connectTimeoutMs != 2000 || responseTimeoutMs != 5000) {
        throw new IllegalArgumentException('HTTP timeouts must remain fixed at 2000/5000 ms')
    }
    if (!(restApiId ==~ /^[a-z0-9]{10}$/) || stageName != 'lab') {
        throw new IllegalArgumentException('API Gateway identifier or stage is invalid')
    }
    if (!(awsProfile ==~ /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/) ||
        !(awsRegion ==~ /^[a-z0-9-]{3,32}$/)) {
        throw new IllegalArgumentException('AWS profile or region is invalid')
    }
    if (minimumRateRps < 1000 || minimumRateRps > 10000 ||
        minimumBurst < 1000 || minimumBurst > 10000) {
        throw new IllegalArgumentException('gateway safety thresholds are invalid')
    }

    URI target = new URI(targetUrl)
    String expectedHost = restApiId + '.execute-api.' + awsRegion + '.amazonaws.com'
    String expectedPath = '/' + stageName + '/api/v1/cotizaciones'
    if (target.scheme != 'https' || target.host != expectedHost || target.port != -1 ||
        target.rawPath != expectedPath || target.rawQuery != null || target.rawFragment != null) {
        throw new IllegalArgumentException('target_url is not the expected Solventa API Gateway endpoint')
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
            if (process.exitValue() != 0 || stdoutBytes.length == 0 || stdoutBytes.length > 65536) {
                throw new IllegalStateException('AWS CLI command failed')
            }
            new String(stdoutBytes, StandardCharsets.UTF_8)
        } finally {
            Arrays.fill(stdoutBytes, (byte) 0)
            Arrays.fill(stderrBytes, (byte) 0)
        }
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
    def quotationPostSettings = stage?.methodSettings?.get('~1api~1v1~1cotizaciones/POST')
    Number globalRate = globalMethodSettings?.throttlingRateLimit as Number
    Number globalBurst = globalMethodSettings?.throttlingBurstLimit as Number
    Number methodRate = quotationPostSettings?.throttlingRateLimit as Number
    Number methodBurst = quotationPostSettings?.throttlingBurstLimit as Number

    if (accountRate == null || accountBurst == null) {
        throw new IllegalStateException('account API Gateway throttle values are absent')
    }

    List<Number> applicableRates = [accountRate]
    List<Number> applicableBursts = [accountBurst]
    if (globalRate != null) applicableRates.add(globalRate)
    if (globalBurst != null) applicableBursts.add(globalBurst)
    if (methodRate != null) applicableRates.add(methodRate)
    if (methodBurst != null) applicableBursts.add(methodBurst)
    double effectiveRate = applicableRates.collect { it.doubleValue() }.min()
    double effectiveBurst = applicableBursts.collect { it.doubleValue() }.min()

    failureCode = 'GATEWAY_CAPACITY_INSUFFICIENT'
    failureMessage = 'API Gateway is not ready for 50k: effective limit ' + effectiveRate +
        ' RPS/' + effectiveBurst + ' burst; required at least ' + minimumRateRps + ' RPS/' + minimumBurst +
        ' burst. No traffic was sent.'
    if (effectiveRate < minimumRateRps || effectiveBurst < minimumBurst) {
        throw new IllegalStateException('API Gateway throttle is below the 50k safety threshold')
    }

    props.remove('solventa.50k.measured.started.epoch_ms')

    SampleResult.setSuccessful(true)
    SampleResult.setResponseCode('200')
    SampleResult.setResponseMessage('50k preflight passed')
    SampleResult.setResponseData(
        'Target, duration, identity boundary and API Gateway throttles are ready.',
        'UTF-8'
    )
    SampleResult.setIgnore()
} catch (Exception ignored) {
    SampleResult.setSuccessful(false)
    SampleResult.setResponseCode('PREFLIGHT_' + failureCode)
    SampleResult.setResponseMessage(failureMessage)
    SampleResult.setResponseData(failureMessage, 'UTF-8')
    log.error('50k preflight stopped before traffic: {}', failureCode)
    ctx.getEngine()?.stopTest(true)
}
