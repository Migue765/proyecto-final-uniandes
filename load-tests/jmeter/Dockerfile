# syntax=docker/dockerfile:1.7
ARG AWS_CLI_VERSION=2.36.44
FROM public.ecr.aws/aws-cli/aws-cli:${AWS_CLI_VERSION}@sha256:e8467f2c319f9bc9a1471808a69949a76915e9c95eaf4a09ece9f9e85fd32747 AS awscli

FROM eclipse-temurin:17-jre-jammy@sha256:ec72ba5962b45ae4e7f96bfb5ebf6eeb34a488b967f937c8e14f0aaec688954f

ARG JMETER_VERSION=5.6.3
ARG JMETER_SHA512=5978a1a35edb5a7d428e270564ff49d2b1b257a65e17a759d259a9283fc17093e522fe46f474a043864aea6910683486340706d745fcdf3db1505fd71e689083

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl jq tar \
    && curl --fail --silent --show-error --location \
      "https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz" \
      --output "/tmp/apache-jmeter-${JMETER_VERSION}.tgz" \
    && printf '%s  %s\n' "${JMETER_SHA512}" "/tmp/apache-jmeter-${JMETER_VERSION}.tgz" | sha512sum --check --strict - \
    && tar -xzf "/tmp/apache-jmeter-${JMETER_VERSION}.tgz" -C /opt \
    && mv "/opt/apache-jmeter-${JMETER_VERSION}" /opt/jmeter \
    && rm "/tmp/apache-jmeter-${JMETER_VERSION}.tgz" \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 loadtest \
    && useradd --uid 10001 --gid loadtest --create-home --shell /usr/sbin/nologin loadtest

ARG SOURCE_REVISION=unknown

COPY --from=awscli /usr/local/aws-cli /usr/local/aws-cli
RUN ln -s /usr/local/aws-cli/v2/current/bin/aws /usr/local/bin/aws

ENV PATH="/opt/jmeter/bin:${PATH}" \
    JVM_ARGS="-Xms256m -Xmx512m -Djava.awt.headless=true -Djava.util.prefs.userRoot=/tmp/jmeter-prefs" \
    RUNNER_SOURCE_REVISION="${SOURCE_REVISION}"

LABEL org.opencontainers.image.revision="${SOURCE_REVISION}"

WORKDIR /work
COPY experiment-1.jmx request-fragment.jmx user.properties run.sh sigv4.groovy /work/
RUN chmod 0555 /work/run.sh \
    && mkdir -p /work/results \
    && chown -R loadtest:loadtest /work

USER 10001:10001
VOLUME ["/work/results"]
ENTRYPOINT ["/work/run.sh"]
