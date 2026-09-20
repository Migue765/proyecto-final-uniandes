# ECR repositories for experiment 2's three application images, mirroring
# infra/terraform/exp1/registry-storage.tf's conventions exactly.

locals {
  repository_names = toset(["ingreso", "reclamos", "pagos"])
}

resource "aws_ecr_repository" "service" {
  for_each = local.repository_names

  name                 = "${var.name_prefix}-${each.value}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "service" {
  for_each = aws_ecr_repository.service

  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain only the 10 newest images in this laboratory repository"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}
