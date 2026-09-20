output "state_bucket_name" {
  description = "Bucket to copy into exp1/backend.hcl."
  value       = aws_s3_bucket.terraform_state.id
}

output "backend_config" {
  description = "Non-secret backend values used by the exp1 root module."
  value = {
    bucket              = aws_s3_bucket.terraform_state.id
    key                 = "exp1/terraform.tfstate"
    region              = var.aws_region
    profile             = var.backend_aws_profile
    use_lockfile        = true
    encrypt             = true
    allowed_account_ids = [var.expected_account_id]
  }
}
