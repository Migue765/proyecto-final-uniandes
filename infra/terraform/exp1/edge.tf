resource "aws_security_group" "nlb" {
  name        = "${var.name_prefix}-nlb"
  description = "Internal NLB reachable only through API Gateway PrivateLink"
  vpc_id      = aws_vpc.main.id

  egress {
    description     = "NodePort on EKS nodes"
    from_port       = 30080
    to_port         = 30080
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  tags = {
    Name = "${var.name_prefix}-nlb"
  }
}

resource "aws_vpc_security_group_ingress_rule" "eks_nodeport_from_nlb" {
  security_group_id            = aws_security_group.eks_nodes.id
  referenced_security_group_id = aws_security_group.nlb.id
  description                  = "NLB health checks and requests to the fixed NodePort"
  from_port                    = 30080
  to_port                      = 30080
  ip_protocol                  = "tcp"
}

resource "aws_lb" "api" {
  name               = "${var.name_prefix}-nlb"
  internal           = true
  load_balancer_type = "network"
  security_groups    = [aws_security_group.nlb.id]

  dynamic "subnet_mapping" {
    for_each = aws_subnet.private

    content {
      subnet_id            = subnet_mapping.value.id
      private_ipv4_address = cidrhost(subnet_mapping.value.cidr_block, 10)
    }
  }

  enable_cross_zone_load_balancing                             = true
  enable_deletion_protection                                   = false
  enforce_security_group_inbound_rules_on_private_link_traffic = "off"

  tags = {
    Name = "${var.name_prefix}-nlb"
  }
}

resource "aws_lb_target_group" "api" {
  name        = "${var.name_prefix}-api"
  port        = 30080
  protocol    = "TCP"
  target_type = "instance"
  vpc_id      = aws_vpc.main.id

  deregistration_delay = 15
  preserve_client_ip   = false

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 10
    matcher             = "200-399"
    path                = "/health/ready"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 6
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_autoscaling_attachment" "eks_nodes" {
  autoscaling_group_name = aws_eks_node_group.fixed.resources[0].autoscaling_groups[0].name
  lb_target_group_arn    = aws_lb_target_group.api.arn
}

resource "aws_api_gateway_vpc_link" "api" {
  name        = "${var.name_prefix}-nlb"
  description = "Private integration to the Solventa experiment NLB"
  target_arns = [aws_lb.api.arn]

  depends_on = [aws_lb_listener.api]
}

data "aws_iam_policy_document" "api_gateway_resource" {
  statement {
    sid     = "DenyUnexpectedPrincipals"
    effect  = "Deny"
    actions = ["execute-api:Invoke"]
    resources = [
      "${aws_api_gateway_rest_api.api.execution_arn}/*"
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "ArnNotEquals"
      variable = "aws:PrincipalArn"
      values = distinct(concat(
        ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/solventa-terraform-operator"],
        var.enable_ecs_load_runner ? [aws_iam_role.load_runner_task[0].arn] : []
      ))
    }
  }

  statement {
    sid     = "DenyOutsideLaboratorySources"
    effect  = "Deny"
    actions = ["execute-api:Invoke"]
    resources = [
      "${aws_api_gateway_rest_api.api.execution_arn}/*"
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "NotIpAddress"
      variable = "aws:SourceIp"
      values = distinct(concat(
        var.api_allowed_source_cidrs,
        ["${aws_eip.nat.public_ip}/32"]
      ))
    }
  }

  statement {
    sid     = "AllowOnlyLaboratorySources"
    effect  = "Allow"
    actions = ["execute-api:Invoke"]
    resources = [
      "${aws_api_gateway_rest_api.api.execution_arn}/*"
    ]

    principals {
      type = "AWS"
      identifiers = distinct(concat(
        ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/solventa-terraform-operator"],
        var.enable_ecs_load_runner ? [aws_iam_role.load_runner_task[0].arn] : []
      ))
    }

    condition {
      test     = "IpAddress"
      variable = "aws:SourceIp"
      values = distinct(concat(
        var.api_allowed_source_cidrs,
        ["${aws_eip.nat.public_ip}/32"]
      ))
    }
  }
}

resource "aws_api_gateway_rest_api" "api" {
  name                 = "${var.name_prefix}-api"
  description          = "Regional REST API for Solventa experiment 1"
  security_policy      = "SecurityPolicy_TLS13_1_3_2025_09"
  endpoint_access_mode = "STRICT"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_rest_api_policy" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  policy      = data.aws_iam_policy_document.api_gateway_resource.json
}

resource "aws_api_gateway_resource" "api_path" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "api"
}

resource "aws_api_gateway_resource" "v1_path" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.api_path.id
  path_part   = "v1"
}

resource "aws_api_gateway_resource" "quotations" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1_path.id
  path_part   = "cotizaciones"
}

resource "aws_api_gateway_method" "create_quotation" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.quotations.id
  http_method   = "POST"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "create_quotation" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.quotations.id
  http_method             = aws_api_gateway_method.create_quotation.http_method
  integration_http_method = "POST"
  type                    = "HTTP_PROXY"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.api.id
  uri                     = "http://${aws_lb.api.dns_name}/api/v1/cotizaciones"
}

resource "aws_api_gateway_account" "current" {
  cloudwatch_role_arn = aws_iam_role.apigateway_cloudwatch.arn

  depends_on = [aws_iam_role_policy_attachment.apigateway_cloudwatch]
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.api_path.id,
      aws_api_gateway_resource.v1_path.id,
      aws_api_gateway_resource.quotations.id,
      aws_api_gateway_method.create_quotation.id,
      aws_api_gateway_integration.create_quotation.id,
      sha1(data.aws_iam_policy_document.api_gateway_resource.json)
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_api_gateway_rest_api_policy.api]
}

resource "aws_api_gateway_stage" "api" {
  deployment_id = aws_api_gateway_deployment.api.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "lab"

  xray_tracing_enabled = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.apigateway.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      resourcePath     = "$context.resourcePath"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
      xrayTraceId      = "$context.xrayTraceId"
    })
  }

  depends_on = [aws_api_gateway_account.current]
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = aws_api_gateway_stage.api.stage_name
  method_path = "*/*"

  settings {
    logging_level          = "INFO"
    metrics_enabled        = true
    data_trace_enabled     = false
    throttling_burst_limit = 40
    throttling_rate_limit  = 20
  }
}
