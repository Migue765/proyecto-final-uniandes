variable "aws_region" {
  description = "AWS region for experiment 2. Must match the region of the reused experiment 1 cluster."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile authenticated with aws login; never an access key."
  type        = string
  default     = "solventa-lab"
}

variable "expected_account_id" {
  description = "Guardrail that prevents applying to a different AWS account."
  type        = string
  default     = "969325258550"

  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "expected_account_id must contain exactly 12 digits."
  }
}

variable "name_prefix" {
  description = "Required prefix for all IAM resources and most experiment resources."
  type        = string
  default     = "solventa-exp2"

  validation {
    condition     = can(regex("^solventa-exp2-[a-z0-9-]*$", "${var.name_prefix}-"))
    error_message = "name_prefix must start with solventa-exp2 and use lowercase letters, numbers and hyphens."
  }
}

variable "exp1_cluster_name" {
  description = "Name of the already-applied experiment 1 EKS cluster reused by experiment 2. Never managed here."
  type        = string
  default     = "solventa-exp1"
}

variable "namespace" {
  description = "Kubernetes namespace where experiment 2 workloads run inside the reused cluster. Created outside Terraform (kubectl/Helm), only referenced here for IRSA trust conditions."
  type        = string
  default     = "solventa-exp2"
}

variable "ingreso_service_account_name" {
  description = "Kubernetes ServiceAccount name the Adaptador de Ingreso deployment will use."
  type        = string
  default     = "ingreso"
}

variable "reclamos_service_account_name" {
  description = "Kubernetes ServiceAccount name the Reclamos (Evaluacion y Liquidacion) deployment will use."
  type        = string
  default     = "reclamos"
}

variable "pagos_service_account_name" {
  description = "Kubernetes ServiceAccount name the Pagos (Ordenes Idempotentes) deployment will use."
  type        = string
  default     = "pagos"
}

variable "max_receive_count" {
  description = "Number of delivery attempts before SQS moves a message from a source queue to its DLQ."
  type        = number
  default     = 5

  validation {
    condition     = var.max_receive_count >= 1 && var.max_receive_count <= 20
    error_message = "max_receive_count must be between 1 and 20."
  }
}

variable "visibility_timeout_seconds" {
  description = "Visibility timeout for both source queues; must exceed the worst-case processing time of one message."
  type        = number
  default     = 30
}

variable "queue_message_retention_seconds" {
  description = "Retention for the source queues (default 4 days)."
  type        = number
  default     = 345600
}

variable "dlq_message_retention_seconds" {
  description = "Retention for both DLQs (default 14 days, the maximum allowed) so failed events stay available for manual analysis."
  type        = number
  default     = 1209600
}
