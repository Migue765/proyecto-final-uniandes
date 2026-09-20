# KEDA's aws-sqs-queue scaler needs an AWS identity to call
# sqs:GetQueueAttributes. Two options exist: identityOwner=workload (the
# scaled Deployment's own IRSA role, solventa-exp2-workload) or
# identityOwner=keda (the KEDA operator's own IRSA role). We use the latter:
# in this KEDA version, identityOwner=workload has the operator perform a
# plain sts:AssumeRole (not AssumeRoleWithWebIdentity) into the target role
# using its own current identity — which, since the KEDA operator has no
# dedicated IRSA role, falls back to the shared EKS node instance role
# (solventa-exp1-eks-nodes). Trusting that shared node role on
# solventa-exp2-workload would let any pod on those nodes assume it, not
# just KEDA. A dedicated, narrowly-scoped operator role avoids that
# widening entirely and needs no change to solventa-exp2-workload's trust
# policy.

data "aws_iam_policy_document" "keda_operator_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer_no_scheme}:sub"
      values   = ["system:serviceaccount:keda:keda-operator"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer_no_scheme}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "keda_operator" {
  name               = "${var.name_prefix}-keda-operator"
  assume_role_policy = data.aws_iam_policy_document.keda_operator_assume.json
}

data "aws_iam_policy_document" "keda_operator" {
  statement {
    sid     = "ReadOnlyExperiment2QueueAttributes"
    actions = ["sqs:GetQueueAttributes"]
    resources = [
      aws_sqs_queue.entrada_parametrica.arn,
      aws_sqs_queue.ordenes_pagos.arn,
    ]
  }
}

resource "aws_iam_role_policy" "keda_operator" {
  name   = "${var.name_prefix}-keda-operator"
  role   = aws_iam_role.keda_operator.id
  policy = data.aws_iam_policy_document.keda_operator.json
}
