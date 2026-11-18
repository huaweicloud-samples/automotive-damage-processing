# ============================================================================
# IAM 委托（Agency）
# 单一 Agency 授予 CCE 节点 / 工作负载访问 OBS / SWR / ModelArts / VPC 的权限。
# 容器内模型调用主要使用 Secret 中的凭据；此 Agency 用于节点拉取 SWR 镜像等资源访问。
# ============================================================================

resource "huaweicloud_identity_agency" "workload" {
  name                  = "${var.project_name}-agency"
  duration              = "FOREVER"
  delegated_domain_name = var.domain_name

  project_role {
    project = var.region
    roles = [
      "OBS OperateAccess",
      "SWR FullAccess",
      "ModelArts FullAccess",
      "VPC FullAccess",
    ]
  }
}
