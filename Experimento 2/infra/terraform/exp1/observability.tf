resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.name_prefix}/cluster"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "apigateway" {
  name              = "/aws/apigateway/${var.name_prefix}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "rds" {
  name              = "/aws/rds/instance/${var.name_prefix}-postgres/postgresql"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/${var.name_prefix}/slow-log"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "redis_engine" {
  name              = "/aws/elasticache/${var.name_prefix}/engine-log"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "load_runner" {
  count = var.enable_ecs_load_runner ? 1 : 0

  name              = "/aws/ecs/${var.name_prefix}/load-runner"
  retention_in_days = 7
}
