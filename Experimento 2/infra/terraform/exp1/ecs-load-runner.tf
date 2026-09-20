resource "aws_security_group" "load_runner" {
  count = var.enable_ecs_load_runner ? 1 : 0

  name        = "${var.name_prefix}-load-runner"
  description = "Outbound-only security group for the optional Fargate load runner"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "HTTPS to API Gateway, ECR, CloudWatch and S3 through NAT"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "UDP DNS to the VPC resolver"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "TCP DNS fallback to the VPC resolver"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.name_prefix}-load-runner"
  }
}

resource "aws_ecs_cluster" "load_runner" {
  count = var.enable_ecs_load_runner ? 1 : 0

  name = "${var.name_prefix}-load-runner"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "load_runner" {
  count = var.enable_ecs_load_runner ? 1 : 0

  family                   = "${var.name_prefix}-load-runner"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.load_runner_cpu)
  memory                   = tostring(var.load_runner_memory)
  execution_role_arn       = aws_iam_role.load_runner_execution[0].arn
  task_role_arn            = aws_iam_role.load_runner_task[0].arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  volume {
    name = "results"
  }

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([{
    name                   = "load-runner"
    image                  = local.load_runner_image
    essential              = true
    command                = length(var.load_runner_command) == 0 ? null : var.load_runner_command
    user                   = "10001:10001"
    privileged             = false
    readonlyRootFilesystem = true

    linuxParameters = {
      initProcessEnabled = true
      capabilities = {
        drop = ["ALL"]
      }
    }

    mountPoints = [
      {
        sourceVolume  = "results"
        containerPath = "/work/results"
        readOnly      = false
      },
      {
        sourceVolume  = "tmp"
        containerPath = "/tmp"
        readOnly      = false
      }
    ]

    environment = [
      {
        name  = "TARGET_URL"
        value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.api.stage_name}/api/v1/cotizaciones"
      },
      {
        name  = "ALLOWED_TARGET_HOSTS"
        value = "${aws_api_gateway_rest_api.api.id}.execute-api.${var.aws_region}.amazonaws.com"
      },
      {
        name  = "EVIDENCE_BUCKET"
        value = aws_s3_bucket.evidence.id
      },
      {
        name  = "S3_PREFIX"
        value = "jtl"
      },
      {
        name  = "AWS_REGION"
        value = var.aws_region
      },
      {
        name  = "AUTH_MODE"
        value = "aws_iam"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.load_runner[0].name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "jmeter"
      }
    }
  }])

  lifecycle {
    precondition {
      condition     = try(length(trimspace(var.load_runner_image)) > 0, false)
      error_message = "enable_ecs_load_runner=true requires load_runner_image pinned to an immutable ECR tag or digest."
    }
  }

  depends_on = [aws_iam_role_policy_attachment.load_runner_execution]
}
