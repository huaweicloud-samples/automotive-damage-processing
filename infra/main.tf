# ============================================================================
# Terraform 入口
# 实际资源分别定义在：
#   vpc.tf / css.tf / cce.tf / elb.tf / nat.tf / obs.tf / lts.tf
#   swr.tf / swr_login.tf / iam.tf / outputs.tf / variables.tf / versions.tf
# 本文件仅作为工作空间入口（满足 SKILL.md 约定的 main.tf 必需性）。
# ============================================================================

provider "huaweicloud" {
  region      = var.region
  access_key  = var.access_key
  secret_key  = var.secret_key
  domain_name = var.domain_name
}
