# ============================================================================
# 日志（LTS 云日志服务）
# 建日志组/流；CCE 侧配置日志策略将容器日志接入 LTS（见 deployment-guide.md）。
# ============================================================================

resource "huaweicloud_lts_group" "main" {
  group_name  = "${var.project_name}-lts"
  ttl_in_days = 7
}

resource "huaweicloud_lts_stream" "main" {
  group_id    = huaweicloud_lts_group.main.id
  stream_name = "${var.project_name}-app"
  ttl_in_days = 7
}
