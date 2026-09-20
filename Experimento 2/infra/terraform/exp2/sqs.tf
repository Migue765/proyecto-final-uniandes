# Two durable FIFO buffers (ASR-EVT-01: "buffer durable con consumidores
# idempotentes y backpressure"), each with its own DLQ for reparable failures.
#
# content_based_deduplication is intentionally FALSE on both source queues.
# The test corpus deliberately sends exact duplicates and late redeliveries of
# the same externalEventId to prove the *application-level* Inbox pattern
# (unique constraint in PostgreSQL) collapses them correctly. If SQS-level
# content-based deduplication were enabled, SQS would silently swallow most of
# those intentional duplicates within its 5-minute dedupe window before Reclamos
# or Pagos ever saw them, defeating the purpose of the experiment. The
# producer must set an explicit MessageDeduplicationId per send attempt (e.g.
# a random UUID, never derived from externalEventId) so every attempt reaches
# the queue and the real idempotency test happens downstream, in the Inbox.
#
# fifo_throughput_limit = "perMessageGroupId" (High Throughput FIFO mode) is
# enabled so the 250,000-request/10-minute target isn't capped by the default
# per-queue FIFO throughput ceiling, as long as the producer spreads events
# across multiple message group ids (partition key = clave de negocio).

resource "aws_sqs_queue" "entrada_parametrica_dlq" {
  name                        = "${var.name_prefix}-entrada-parametrica-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = false
  kms_master_key_id           = "alias/aws/sqs"
  message_retention_seconds   = var.dlq_message_retention_seconds

  tags = {
    Name = "${var.name_prefix}-entrada-parametrica-dlq"
  }
}

resource "aws_sqs_queue" "entrada_parametrica" {
  name                        = "${var.name_prefix}-entrada-parametrica.fifo"
  fifo_queue                  = true
  content_based_deduplication = false
  deduplication_scope         = "messageGroup"
  fifo_throughput_limit       = "perMessageGroupId"
  kms_master_key_id           = "alias/aws/sqs"
  visibility_timeout_seconds  = var.visibility_timeout_seconds
  message_retention_seconds   = var.queue_message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.entrada_parametrica_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = {
    Name = "${var.name_prefix}-entrada-parametrica"
  }
}

resource "aws_sqs_queue" "ordenes_pagos_dlq" {
  name                        = "${var.name_prefix}-ordenes-pagos-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = false
  kms_master_key_id           = "alias/aws/sqs"
  message_retention_seconds   = var.dlq_message_retention_seconds

  tags = {
    Name = "${var.name_prefix}-ordenes-pagos-dlq"
  }
}

resource "aws_sqs_queue" "ordenes_pagos" {
  name                        = "${var.name_prefix}-ordenes-pagos.fifo"
  fifo_queue                  = true
  content_based_deduplication = false
  deduplication_scope         = "messageGroup"
  fifo_throughput_limit       = "perMessageGroupId"
  kms_master_key_id           = "alias/aws/sqs"
  visibility_timeout_seconds  = var.visibility_timeout_seconds
  message_retention_seconds   = var.queue_message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ordenes_pagos_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = {
    Name = "${var.name_prefix}-ordenes-pagos"
  }
}
