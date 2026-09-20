data "tls_certificate" "eks_oidc" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc.certificates[0].sha1_fingerprint]
}

data "aws_iam_policy_document" "cluster_autoscaler_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:cluster-autoscaler"]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster_autoscaler" {
  name               = "${var.name_prefix}-cluster-autoscaler"
  assume_role_policy = data.aws_iam_policy_document.cluster_autoscaler_assume.json
}

data "aws_iam_policy_document" "cluster_autoscaler" {
  statement {
    sid = "DescribeAutoscalingForDiscovery"
    actions = [
      "autoscaling:DescribeAutoScalingGroups",
      "autoscaling:DescribeAutoScalingInstances",
      "autoscaling:DescribeLaunchConfigurations",
      "autoscaling:DescribeScalingActivities",
      "ec2:DescribeInstanceTypes",
      "ec2:DescribeLaunchTemplateVersions"
    ]
    resources = ["*"]
  }

  statement {
    sid = "ScaleOnlyThisExperimentNodeGroup"
    actions = [
      "autoscaling:SetDesiredCapacity",
      "autoscaling:TerminateInstanceInAutoScalingGroup",
      "autoscaling:UpdateAutoScalingGroup"
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "autoscaling:ResourceTag/k8s.io/cluster-autoscaler/${var.name_prefix}"
      values   = ["owned"]
    }
  }
}

resource "aws_iam_role_policy" "cluster_autoscaler" {
  name   = "${var.name_prefix}-cluster-autoscaler"
  role   = aws_iam_role.cluster_autoscaler.id
  policy = data.aws_iam_policy_document.cluster_autoscaler.json
}
