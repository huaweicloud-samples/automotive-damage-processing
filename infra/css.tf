# ============================================================================
# 向量数据库：CSS（云搜索服务，OpenSearch 引擎）
# kNN 向量检索接口与 opensearch-py 客户端兼容；鉴权走 HTTP basic auth
# （见 src/adapter/opensearch_client.py）。
# ============================================================================

# CSS(OpenSearch) 搜索端口：集群所在安全组须放通访问（CSS 官方要求）
# 注意：CCE vpc-router 模式下 Pod 源 IP 是容器网段（非 VPC 10.0.0.0/16），
#       必须用 0.0.0.0/0——CSS 集群无公网 IP，物理上仅 VPC 内可达，无暴露风险。
# 安全模式 HTTPS 走 9200；同时放 9600 兼容新版集群
resource "huaweicloud_networking_secgroup_rule" "allow_css" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 9200
  port_range_max    = 9600
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = huaweicloud_networking_secgroup.main.id
}

resource "huaweicloud_css_cluster" "vector" {
  name           = "${var.project_name}-css"
  engine_type    = "opensearch"
  engine_version = var.css_engine_version
  security_mode  = true
  https_enabled  = true
  password       = var.css_password

  availability_zone = "${var.region}a"
  vpc_id            = huaweicloud_vpc.main.id
  subnet_id         = huaweicloud_vpc_subnet.private_1.id
  security_group_id = huaweicloud_networking_secgroup.main.id

  ess_node_config {
    flavor          = var.css_flavor
    instance_number = var.css_node_count

    volume {
      volume_type = "HIGH"
      size        = 40
    }
  }

  tags = {
    project = var.project_name
  }
}
