output "aws_account_id" {
  description = "AWS account validated by the provider guardrail."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "Region containing the experiment 2 resources."
  value       = var.aws_region
}

output "namespace" {
  description = "Kubernetes namespace expected by the IRSA trust policies (created outside Terraform)."
  value       = var.namespace
}

output "entrada_parametrica_queue_url" {
  description = "URL of the entrada-parametrica FIFO queue."
  value       = aws_sqs_queue.entrada_parametrica.url
}

output "entrada_parametrica_queue_arn" {
  description = "ARN of the entrada-parametrica FIFO queue."
  value       = aws_sqs_queue.entrada_parametrica.arn
}

output "entrada_parametrica_dlq_url" {
  description = "URL of the entrada-parametrica DLQ."
  value       = aws_sqs_queue.entrada_parametrica_dlq.url
}

output "entrada_parametrica_dlq_arn" {
  description = "ARN of the entrada-parametrica DLQ."
  value       = aws_sqs_queue.entrada_parametrica_dlq.arn
}

output "ordenes_pagos_queue_url" {
  description = "URL of the ordenes-pagos FIFO queue."
  value       = aws_sqs_queue.ordenes_pagos.url
}

output "ordenes_pagos_queue_arn" {
  description = "ARN of the ordenes-pagos FIFO queue."
  value       = aws_sqs_queue.ordenes_pagos.arn
}

output "ordenes_pagos_dlq_url" {
  description = "URL of the ordenes-pagos DLQ."
  value       = aws_sqs_queue.ordenes_pagos_dlq.url
}

output "ordenes_pagos_dlq_arn" {
  description = "ARN of the ordenes-pagos DLQ."
  value       = aws_sqs_queue.ordenes_pagos_dlq.arn
}

output "workload_role_arn" {
  description = "Shared IRSA role ARN used by the Adaptador de Ingreso, Reclamos and Pagos service accounts."
  value       = aws_iam_role.workload.arn
}

output "keda_operator_role_arn" {
  description = "IRSA role ARN for the KEDA operator's own ServiceAccount (system:serviceaccount:keda:keda-operator)."
  value       = aws_iam_role.keda_operator.arn
}

output "hmac_shared_secret_arn" {
  description = "Secrets Manager ARN of the HMAC shared secret; never exposes its value."
  value       = aws_secretsmanager_secret.hmac_shared.arn
}

output "ecr_repository_urls" {
  description = "Image destinations keyed by ingreso, reclamos and pagos."
  value       = { for name, repository in aws_ecr_repository.service : name => repository.repository_url }
}

output "rds_endpoint" {
  description = "Private PostgreSQL hostname reused from experiment 1 (read-only passthrough)."
  value       = data.terraform_remote_state.exp1.outputs.rds_endpoint
}

output "rds_port" {
  description = "PostgreSQL listener port reused from experiment 1 (read-only passthrough)."
  value       = data.terraform_remote_state.exp1.outputs.rds_port
}

output "rds_master_secret_arn" {
  description = "Secrets Manager ARN of experiment 1's RDS master secret (read-only passthrough); never exposes its value."
  value       = data.terraform_remote_state.exp1.outputs.rds_master_secret_arn
}
