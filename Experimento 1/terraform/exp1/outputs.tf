output "aws_account_id" {
  description = "AWS account validated by the provider guardrail."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "Region containing the experiment resources."
  value       = var.aws_region
}

output "cluster_name" {
  description = "EKS cluster name used by aws eks update-kubeconfig."
  value       = aws_eks_cluster.main.name
}

output "api_gateway_rest_api_id" {
  description = "REST API identifier."
  value       = aws_api_gateway_rest_api.api.id
}

output "api_gateway_name" {
  description = "REST API name used as a CloudWatch dimension."
  value       = aws_api_gateway_rest_api.api.name
}

output "api_gateway_stage_name" {
  description = "Deployed REST API stage."
  value       = aws_api_gateway_stage.api.stage_name
}

output "api_gateway_invoke_url" {
  description = "Public base URL used for smoke and load tests."
  value       = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.api.stage_name}"
}

output "api_gateway_cloudwatch_role_arn" {
  description = "Regional API Gateway role used for CloudWatch execution logs."
  value       = aws_iam_role.apigateway_cloudwatch.arn
}

output "api_gateway_log_group_name" {
  description = "CloudWatch access log group for the experiment REST API."
  value       = aws_cloudwatch_log_group.apigateway.name
}

output "internal_nlb_dns_name" {
  description = "Internal NLB DNS name behind the API Gateway VPC Link."
  value       = aws_lb.api.dns_name
}

output "internal_nlb_source_cidrs" {
  description = "Static NLB node addresses allowed by the quotation NetworkPolicy."
  value = [
    for subnet in values(aws_subnet.private) : "${cidrhost(subnet.cidr_block, 10)}/32"
  ]
}

output "ecr_repository_urls" {
  description = "Image destinations keyed by quote, profile and load-runner."
  value       = { for name, repository in aws_ecr_repository.service : name => repository.repository_url }
}

output "evidence_bucket_name" {
  description = "Private bucket for JTL and test evidence."
  value       = aws_s3_bucket.evidence.id
}

output "rds_endpoint" {
  description = "Private PostgreSQL hostname without a port."
  value       = aws_db_instance.postgres.address
}

output "rds_instance_identifier" {
  description = "RDS instance identifier used as a CloudWatch dimension."
  value       = aws_db_instance.postgres.identifier
}

output "rds_port" {
  description = "PostgreSQL listener port."
  value       = aws_db_instance.postgres.port
}

output "rds_database_name" {
  description = "Initial PostgreSQL database."
  value       = aws_db_instance.postgres.db_name
}

output "rds_master_secret_arn" {
  description = "Secrets Manager ARN generated and managed by RDS; it does not expose the password."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}

output "redis_primary_endpoint" {
  description = "Private Redis primary endpoint."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_replication_group_id" {
  description = "Redis replication group identifier."
  value       = aws_elasticache_replication_group.redis.replication_group_id
}

output "redis_member_cluster_ids" {
  description = "Redis member identifiers used as CloudWatch dimensions."
  value       = aws_elasticache_replication_group.redis.member_clusters
}

output "redis_port" {
  description = "Redis TLS listener port."
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_tls_enabled" {
  description = "Signals to deploy tooling that Redis requires TLS."
  value       = aws_elasticache_replication_group.redis.transit_encryption_enabled
}

output "redis_auth_secret_arn" {
  description = "Secrets Manager ARN containing the Redis token; the token is never stored in Terraform state."
  value       = aws_secretsmanager_secret.redis_auth.arn
}

output "private_subnet_ids" {
  description = "Private application subnets used by EKS and the optional load runner."
  value       = values(aws_subnet.private)[*].id
}

output "load_runner_cluster_name" {
  description = "Optional ECS cluster; null when enable_ecs_load_runner is false."
  value       = try(aws_ecs_cluster.load_runner[0].name, null)
}

output "load_runner_task_definition_arn" {
  description = "Optional Fargate task definition; null when disabled."
  value       = try(aws_ecs_task_definition.load_runner[0].arn, null)
}

output "load_runner_security_group_id" {
  description = "Optional outbound-only Fargate security group; null when disabled."
  value       = try(aws_security_group.load_runner[0].id, null)
}
