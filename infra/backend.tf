# ───────────────────────────────────────────────────────────────
# backend.tf — Remote state with S3 + DynamoDB locking
# ───────────────────────────────────────────────────────────────

terraform {
  backend "s3" {
    bucket         = "idp-platform-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "idp-platform-terraform-locks"
  }
}
