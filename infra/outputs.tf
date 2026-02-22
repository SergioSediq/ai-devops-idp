# ───────────────────────────────────────────────────────────────
# outputs.tf — Key infrastructure outputs (aligned with main.tf modules)
# ───────────────────────────────────────────────────────────────

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_security_group_id" {
  description = "Security group attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.db.db_instance_endpoint
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.db.db_instance_name
}

output "s3_artifacts_bucket" {
  description = "S3 bucket for build artifacts"
  value       = aws_s3_bucket.idp_artifacts.id
}

output "ai_agent_irsa_role_arn" {
  description = "IAM Role ARN for AI agent service account (IRSA)"
  value       = module.ai_agent_irsa_role.iam_role_arn
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}
