# ───────────────────────────────────────────────────────────────
# security.tf — Dedicated security groups for EKS ↔ RDS
# Uses outputs from main.tf modules (vpc, eks)
# ───────────────────────────────────────────────────────────────

# Security group for RDS — only allows traffic from EKS nodes
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  description = "Security group for RDS — allows PostgreSQL from EKS only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name        = "${var.project_name}-rds-sg"
    Environment = var.environment
  })

  lifecycle {
    create_before_destroy = true
  }
}
