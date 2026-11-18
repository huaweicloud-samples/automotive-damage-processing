# ============================================================================
# 对象存储（OBS）：frontend 桶存匹配图片供 UI 展示，source 桶存灌库源数据
# frontend 桶设为公读以便 UI 直接拼 URL 加载；生产建议改私有 + 临时签名 URL
# ============================================================================

resource "random_id" "suffix" {
  byte_length = 4
}

resource "huaweicloud_obs_bucket" "frontend" {
  bucket        = "${var.project_name}-frontend-${random_id.suffix.hex}"
  acl           = "public-read"
  force_destroy = true

  tags = {
    project = var.project_name
  }
}

resource "huaweicloud_obs_bucket" "source" {
  bucket        = "${var.project_name}-source-${random_id.suffix.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    project = var.project_name
  }
}
