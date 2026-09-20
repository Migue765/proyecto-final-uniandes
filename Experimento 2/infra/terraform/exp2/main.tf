provider "aws" {
  region              = var.aws_region
  profile             = var.aws_profile
  allowed_account_ids = [var.expected_account_id]

  default_tags {
    tags = local.common_tags
  }
}

data "aws_caller_identity" "current" {}

locals {
  common_tags = {
    Project     = "solventa"
    Experiment  = "2"
    Environment = "lab"
    ManagedBy   = "terraform"
    Teardown    = "required-after-test"
  }
}
