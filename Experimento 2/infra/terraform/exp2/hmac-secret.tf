# HMAC-SHA256 shared secret used by the Adaptador de Ingreso to sign/verify
# parametric events (see services/ingreso-service/app/security.py). Generated
# with an ephemeral resource, like exp1's redis-auth.tf, so the raw secret
# value never appears in Terraform state or plan output — only its ARN does.

resource "aws_secretsmanager_secret" "hmac_shared" {
  name                    = "${var.name_prefix}/hmac-shared-secret"
  description             = "HMAC-SHA256 shared secret for the Experiment 2 Adaptador de Ingreso"
  recovery_window_in_days = 0
}

ephemeral "aws_secretsmanager_random_password" "hmac_shared" {
  password_length     = 64
  exclude_punctuation = true
  include_space       = false
}

resource "aws_secretsmanager_secret_version" "hmac_shared" {
  secret_id = aws_secretsmanager_secret.hmac_shared.id

  secret_string_wo         = ephemeral.aws_secretsmanager_random_password.hmac_shared.random_password
  secret_string_wo_version = 1
}
