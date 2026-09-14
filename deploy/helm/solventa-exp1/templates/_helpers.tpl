{{- define "solventa-exp1.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "solventa-exp1.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "solventa-exp1.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "solventa-exp1.labels" -}}
app.kubernetes.io/part-of: solventa-exp1
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end }}

{{- define "solventa-exp1.selectorLabels" -}}
app.kubernetes.io/name: {{ include "solventa-exp1.fullname" . }}
{{- end }}

{{- define "solventa-exp1.wiremockUrl" -}}
{{- if .Values.wiremock.baseUrl -}}
{{- .Values.wiremock.baseUrl -}}
{{- else -}}
{{- printf "http://%s-wiremock:%d" (include "solventa-exp1.fullname" .) (int .Values.wiremock.service.port) -}}
{{- end -}}
{{- end }}
