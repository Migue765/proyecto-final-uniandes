# Experiment 2 reuses the experiment 1 EKS cluster, VPC, RDS instance and
# EKS OIDC provider. Nothing here creates or modifies experiment 1 resources
# or state; these are read-only lookups by name so this stack stays fully
# independent (its own state file, its own apply/destroy lifecycle).

data "aws_eks_cluster" "exp1" {
  name = var.exp1_cluster_name
}

locals {
  # The OIDC provider ARN is derived as a plain string instead of looked up
  # via the aws_iam_openid_connect_provider data source on purpose: that data
  # source resolves by URL through iam:ListOpenIDConnectProviders, an
  # account-wide list action that cannot be scoped to a single resource. The
  # ARN format is fully deterministic from the account id and issuer host, so
  # building it here needs zero additional IAM permissions beyond the
  # eks:DescribeCluster and sts:GetCallerIdentity reads already covered by
  # PowerUserAccess.
  oidc_issuer_no_scheme = replace(data.aws_eks_cluster.exp1.identity[0].oidc[0].issuer, "https://", "")
  oidc_provider_arn     = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${local.oidc_issuer_no_scheme}"
}
