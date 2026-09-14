resource "aws_secretsmanager_secret" "redis_auth" {
  name                    = "${var.name_prefix}/redis-auth"
  description             = "Authentication token for the Solventa experiment Redis cache"
  recovery_window_in_days = 0
}

ephemeral "aws_secretsmanager_random_password" "redis_auth" {
  password_length     = 32
  exclude_punctuation = true
  include_space       = false
}

resource "aws_secretsmanager_secret_version" "redis_auth" {
  secret_id = aws_secretsmanager_secret.redis_auth.id

  secret_string_wo = jsonencode({
    username   = "default"
    auth_token = ephemeral.aws_secretsmanager_random_password.redis_auth.random_password
  })
  secret_string_wo_version = 1
}
