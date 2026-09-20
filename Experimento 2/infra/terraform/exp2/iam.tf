# Single shared IRSA role for all of experiment 2's workloads (Adaptador de
# Ingreso, Reclamos, Pagos). This is a deliberate simplification from one role
# per service: this is a disposable lab environment (not production), so the
# extra blast-radius separation between the three services wasn't judged
# worth the added complexity. The role's permissions are still scoped to the
# four exp2 queues by ARN (never sqs:* on Resource "*") so it can't touch any
# other queue in the account.

data "aws_iam_policy_document" "workload_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer_no_scheme}:sub"
      values = [
        "system:serviceaccount:${var.namespace}:${var.ingreso_service_account_name}",
        "system:serviceaccount:${var.namespace}:${var.reclamos_service_account_name}",
        "system:serviceaccount:${var.namespace}:${var.pagos_service_account_name}",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer_no_scheme}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "workload" {
  name               = "${var.name_prefix}-workload"
  assume_role_policy = data.aws_iam_policy_document.workload_assume.json
}

data "aws_iam_policy_document" "workload" {
  statement {
    sid = "ReadWriteOnlyExperiment2Queues"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [
      aws_sqs_queue.entrada_parametrica.arn,
      aws_sqs_queue.ordenes_pagos.arn,
    ]
  }

  statement {
    sid = "InspectOnlyBothDlqsNonDestructive"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
    ]
    resources = [
      aws_sqs_queue.entrada_parametrica_dlq.arn,
      aws_sqs_queue.ordenes_pagos_dlq.arn,
    ]
  }

  statement {
    sid       = "ReadOnlyHmacSharedSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.hmac_shared.arn]
  }

  statement {
    # Deliberate simplification (explicit lab decision, not the default
    # recommendation): reuses the shared workload role instead of a
    # dedicated bootstrap-only role, so any of ingreso/reclamos/pagos can
    # read exp1's RDS master secret. Reclamos and Pagos connect to their own
    # new "reclamos"/"pagos" databases as the same solventa_admin user exp1
    # already uses for its own "solventa" database, on the same instance.
    sid       = "ReadOnlyExp1RdsMasterSecretForAppAndBootstrap"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [data.terraform_remote_state.exp1.outputs.rds_master_secret_arn]
  }
}

resource "aws_iam_role_policy" "workload" {
  name   = "${var.name_prefix}-workload"
  role   = aws_iam_role.workload.id
  policy = data.aws_iam_policy_document.workload.json
}
