resource "aws_db_subnet_group" "main" {
  name       = "${var.name_prefix}-postgres"
  subnet_ids = values(aws_subnet.data)[*].id

  tags = {
    Name = "${var.name_prefix}-postgres"
  }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.name_prefix}-redis"
  subnet_ids = values(aws_subnet.data)[*].id
}

resource "aws_security_group" "postgres" {
  name        = "${var.name_prefix}-postgres"
  description = "PostgreSQL access only from EKS nodes"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  # Temporary, explicit lab exception for direct DBeaver access from a
  # specific developer IP — see aws_route_table.data's comment for the
  # accompanying network change this depends on. Revert once no longer
  # needed.
  ingress {
    description = "Temporary: direct DBeaver access from a specific developer IP"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["179.1.208.66/32"]
  }

  egress {
    description = "Responses inside the VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.name_prefix}-postgres"
  }
}

resource "aws_security_group" "redis" {
  name        = "${var.name_prefix}-redis"
  description = "Redis access only from EKS nodes"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis TLS from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  egress {
    description = "Responses inside the VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.name_prefix}-redis"
  }
}

resource "aws_db_instance" "postgres" {
  identifier = "${var.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = var.rds_engine_version
  # db.t4g.large would give more max_connections headroom for scaling
  # reclamos/pagos (see PLAN.md/EJECUCION.md capacity projection), but this
  # AWS account is on the free tier, which rejects any instance size beyond
  # db.t4g.micro (FreeTierRestrictionError) — confirmed by attempting it.
  instance_class = "db.t4g.micro"

  allocated_storage     = 20
  max_allocated_storage = 0
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name                     = "solventa"
  username                    = "solventa_admin"
  manage_master_user_password = true
  port                        = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  # Temporary lab exception for direct DBeaver access — see the
  # accompanying comments on aws_route_table.data and the
  # aws_security_group.postgres ingress rule. Revert once no longer needed.
  publicly_accessible = true
  multi_az            = false

  backup_retention_period = 1
  backup_window           = "05:00-05:30"
  maintenance_window      = "sun:06:00-sun:06:30"

  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled    = false
  monitoring_interval             = 0

  deletion_protection        = false
  skip_final_snapshot        = true
  delete_automated_backups   = true
  apply_immediately          = true
  auto_minor_version_upgrade = false

  depends_on = [aws_cloudwatch_log_group.rds]
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.name_prefix}-redis"
  description          = "Solventa experiment 1 cache"

  engine         = "redis"
  engine_version = var.redis_engine_version
  node_type      = "cache.t4g.micro"
  port           = 6379

  num_cache_clusters         = 1
  automatic_failover_enabled = false
  multi_az_enabled           = false

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  transit_encryption_mode    = "required"
  auth_token_wo              = ephemeral.aws_secretsmanager_random_password.redis_auth.random_password
  auth_token_wo_version      = 1

  snapshot_retention_limit = 0
  apply_immediately        = true

  depends_on = [aws_secretsmanager_secret_version.redis_auth]

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }
}
