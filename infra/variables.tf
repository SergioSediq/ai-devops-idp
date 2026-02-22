# ───────────────────────────────────────────────────────────────
# variables.tf — Parameterized infrastructure inputs
# ───────────────────────────────────────────────────────────────

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "idp-platform"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "development"
  validation {
    condition     = contains(["production", "staging", "development", "dev"], var.environment)
    error_message = "Environment must be one of: production, staging, development, dev."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

# ── Networking ────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of AZs to use"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

# ── EKS ───────────────────────────────────────────────────────

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.28"
}

variable "eks_node_instance_types" {
  description = "EC2 instance types for EKS managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "eks_node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 4
}

# ── RDS ───────────────────────────────────────────────────────

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.small"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "14.9"
}

variable "rds_database_name" {
  description = "Default database name"
  type        = string
  default     = "backstage_app"
}

variable "rds_master_username" {
  description = "RDS master username"
  type        = string
  default     = "backstage_admin"
  sensitive   = true
}

variable "rds_master_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

# ── Tags ──────────────────────────────────────────────────────

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    ManagedBy = "terraform"
    Project   = "idp-platform"
  }
}
