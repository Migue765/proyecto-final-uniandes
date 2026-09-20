provider "aws" {
  region              = var.aws_region
  profile             = var.aws_profile
  allowed_account_ids = [var.expected_account_id]

  default_tags {
    tags = local.common_tags
  }
}

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  availability_zones = slice(sort(data.aws_availability_zones.available.names), 0, 2)

  common_tags = {
    Project     = "solventa"
    Experiment  = "1"
    Environment = "lab"
    ManagedBy   = "terraform"
    Teardown    = "required-after-test"
  }

  repository_names  = toset(["quote", "profile", "load-runner"])
  load_runner_image = var.load_runner_image
}
