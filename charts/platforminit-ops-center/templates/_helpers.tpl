{{/*
Expand the name of the chart.
*/}}
{{- define "platforminit-ops-center.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "platforminit-ops-center.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "platforminit-ops-center.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "platforminit-ops-center.labels" -}}
helm.sh/chart: {{ include "platforminit-ops-center.chart" . }}
{{ include "platforminit-ops-center.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "platforminit-ops-center.selectorLabels" -}}
app.kubernetes.io/name: {{ include "platforminit-ops-center.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use for the API component
*/}}
{{- define "platforminit-ops-center.api.serviceAccountName" -}}
{{- if .Values.api.serviceAccount.create }}
{{- default (include "platforminit-ops-center.fullname" .) .Values.api.serviceAccount.name }}
{{- else }}
{{- .Values.api.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use for the UI component
*/}}
{{- define "platforminit-ops-center.ui.serviceAccountName" -}}
{{- if .Values.ui.serviceAccount.create }}
{{- default (printf "%s-ui" (include "platforminit-ops-center.fullname" .)) .Values.ui.serviceAccount.name }}
{{- else }}
{{- .Values.ui.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the appropriate apiVersion for ingress.
*/}}
{{- define "platforminit-ops-center.ingress.apiVersion" -}}
{{- if and (.Capabilities.APIVersions.Has "networking.k8s.io/v1") (semverCompare ">=1.19-0" .Capabilities.KubeVersion.Version) }}
{{- print "networking.k8s.io/v1" }}
{{- else if .Capabilities.APIVersions.Has "networking.k8s.io/v1beta1" }}
{{- print "networking.k8s.io/v1beta1" }}
{{- else }}
{{- print "extensions/v1beta1" }}
{{- end }}
{{- end }}

{{/*
Return if ingress is stable.
*/}}
{{- define "platforminit-ops-center.ingress.isStable" -}}
{{- eq (include "platforminit-ops-center.ingress.apiVersion" .) "networking.k8s.io/v1" }}
{{- end }}
