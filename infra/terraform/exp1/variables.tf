variable "aws_region" {
  description = "AWS region for experiment 1."
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
  default     = "solventa-exp1"

  validation {
    condition     = can(regex("^solventa-exp1-[a-z0-9-]*$", "${var.name_prefix}-"))
    error_message = "name_prefix must start with solventa-exp1 and use lowercase letters, numbers and hyphens."
  }
}

variable "vpc_cidr" {
  description = "CIDR assigned to the isolated experiment VPC."
  type        = string
  default     = "10.51.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR."
  }
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "Public CIDRs allowed to reach the EKS Kubernetes API. Use the operator's current public IP as /32."
  type        = list(string)

  validation {
    condition = (
      length(var.cluster_endpoint_public_access_cidrs) > 0 &&
      alltrue([for cidr in var.cluster_endpoint_public_access_cidrs : can(cidrhost(cidr, 0))]) &&
      !contains(var.cluster_endpoint_public_access_cidrs, "0.0.0.0/0")
    )
    error_message = "Provide at least one valid restricted CIDR; 0.0.0.0/0 is intentionally rejected."
  }
}

variable "api_allowed_source_cidrs" {
  description = "Public laboratory CIDRs allowed to invoke the regional REST API. The optional Fargate runner NAT EIP is added automatically."
  type        = list(string)

  validation {
    condition = (
      length(var.api_allowed_source_cidrs) > 0 &&
      alltrue([for cidr in var.api_allowed_source_cidrs : can(cidrhost(cidr, 0))]) &&
      !contains(var.api_allowed_source_cidrs, "0.0.0.0/0")
    )
    error_message = "Provide at least one valid restricted CIDR; 0.0.0.0/0 is intentionally rejected."
  }
}

variable "eks_version" {
  description = "Supported EKS Kubernetes minor version."
  type        = string
  default     = "1.36"
}

variable "vpc_cni_addon_version" {
  description = "VPC CNI add-on version verified for the selected EKS version."
  type        = string
  default     = "v1.22.4-eksbuild.3"
}

variable "node_instance_type" {
  description = "Fixed instance type for the experiment node group."
  type        = string
  default     = "c7i.large"

  validation {
    condition     = var.node_instance_type == "c7i.large"
    error_message = "Experiment 1 is intentionally fixed to c7i.large for reproducibility."
  }
}

variable "rds_engine_version" {
  description = "PostgreSQL 15 engine version available in the laboratory account."
  type        = string
  default     = "15.19"
}

variable "redis_engine_version" {
  description = "Redis OSS engine version available in the laboratory account."
  type        = string
  default     = "7.1"
}

variable "evidence_retention_days" {
  description = "Days before JTL and related load-test evidence expires from S3."
  type        = number
  default     = 14

  validation {
    condition     = var.evidence_retention_days >= 1 && var.evidence_retention_days <= 90
    error_message = "evidence_retention_days must be between 1 and 90."
  }
}

variable "enable_ecs_load_runner" {
  description = "Creates the optional Fargate cluster and task definition for remote load generation."
  type        = bool
  default     = false
}

variable "load_runner_image" {
  description = "Immutable ECR image URI for the Fargate load runner; required when enable_ecs_load_runner is true."
  type        = string
  default     = null
  nullable    = true
}

variable "load_runner_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "load_runner_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "load_runner_command" {
  description = "Optional command override for the load-runner image."
  type        = list(string)
  default     = []
}
