{{/*
Expand the name of the chart.
*/}}
{{- define "ops-bot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ops-bot.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "ops-bot.labels" -}}
helm.sh/chart: {{ include "ops-bot.name" . }}-{{ .Chart.Version }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "ops-bot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ops-bot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}