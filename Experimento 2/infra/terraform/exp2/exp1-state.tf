# Read-only lookup of experiment 1's outputs (RDS endpoint/port/database name
# and its RDS-managed master secret ARN). This never touches exp1's state,
# only reads it, so this stack stays independently apply/destroy-able.

data "terraform_remote_state" "exp1" {
  backend = "s3"

  config = {
    bucket  = "solventa-exp1-tfstate-969325258550-us-east-1"
    key     = "exp1/terraform.tfstate"
    region  = "us-east-1"
    profile = "solventa-terraform-backend"
  }
}
