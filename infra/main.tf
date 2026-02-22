provider "aws" {
  region = var.aws_region
}

locals {
  cluster_name = "${var.project_name}-eks"
}

################################################################################
# VPC
################################################################################
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  tags = merge(var.common_tags, {
    Environment                                   = var.environment
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  })
}

################################################################################
# EKS Cluster
################################################################################
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.15.3"

  cluster_name    = local.cluster_name
  cluster_version = var.eks_cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    main = {
      min_size     = var.eks_node_min_size
      max_size     = var.eks_node_max_size
      desired_size = var.eks_node_desired_size

      instance_types = var.eks_node_instance_types
      capacity_type  = "ON_DEMAND"
    }
  }

  # Allow IRSA
  enable_irsa = true

  tags = merge(var.common_tags, {
    Environment = var.environment
  })
}

################################################################################
# RDS Postgres (Backstage Backend)
################################################################################
module "db" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.0.0"

  identifier = "${var.project_name}-db"

  engine               = "postgres"
  engine_version       = var.rds_engine_version
  family               = "postgres14"
  major_engine_version = "14"
  instance_class       = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = 100

  db_name  = var.rds_database_name
  username = var.rds_master_username
  password = var.rds_master_password
  port     = 5432

  subnet_ids             = module.vpc.private_subnets
  vpc_security_group_ids = [aws_security_group.rds.id]

  skip_final_snapshot = true
  deletion_protection = false # For demo
}

################################################################################
# S3 Bucket (Terraform State & Logs)
################################################################################
resource "aws_s3_bucket" "idp_artifacts" {
  bucket = "${var.project_name}-artifacts-${random_id.suffix.hex}"

  tags = merge(var.common_tags, {
    Name        = "${var.project_name} Artifacts"
    Environment = var.environment
  })
}

resource "random_id" "suffix" {
  byte_length = 4
}

################################################################################
# IRSA: IAM Role for Service Accounts (AI Agent -> CloudWatch)
################################################################################
module "ai_agent_irsa_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 6.4"

  role_name = "ai-agent-cloudwatch-reader"

  role_policy_arns = {
    CloudWatchReadOnly = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["idp-platform:ai-agent"]
    }
  }
}

################################################################################
# Outputs
################################################################################
output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "db_endpoint" {
  value = module.db.db_instance_endpoint
}

output "ai_agent_role_arn" {
  value = module.ai_agent_irsa_role.iam_role_arn
}
