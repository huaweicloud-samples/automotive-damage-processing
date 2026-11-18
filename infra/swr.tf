# ============================================================================
# 镜像仓库：SWR 组织 + 仓库（inference / ingestion 镜像）
# 构建脚本见 src/containers/*/build_and_push.sh
# ============================================================================

resource "huaweicloud_swr_organization" "main" {
  name = "${var.project_name}-swr"
}

resource "huaweicloud_swr_repository" "main" {
  organization = huaweicloud_swr_organization.main.name
  name         = "damage-repo"
  description  = "automotive damage processing: inference + ingestion"
}
