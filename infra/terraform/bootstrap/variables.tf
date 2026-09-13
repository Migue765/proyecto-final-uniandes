variable "aws_region" {
  description = "AWS region where the remote-state bucket is created."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile authenticated with aws login."
  type        = string
  default     = "solventa-lab"
}

variable "backend_aws_profile" {
  description = "Credential-process profile used by Terraform's S3 backend."
  type        = string
  default     = "solventa-terraform-backend"
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

variable "project_name" {
  description = "Prefix used for the Terraform state bucket."
  type        = string
  default     = "solventa-exp1"
}
