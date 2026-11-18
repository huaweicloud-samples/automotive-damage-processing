# ============================================================================
# 网络底座：VPC / 子网 / 安全组
# 公网入口经 EIP（绑定 ELB）提供；私网子网访问 SWR/MaaS/CSS/OBS 等
# 同 region 云服务走华为云内网服务网络（100.125.x.x），无需公网 NAT。
# ============================================================================

resource "huaweicloud_vpc" "main" {
  name                  = "${var.project_name}-vpc"
  cidr                  = "10.0.0.0/16"
  enterprise_project_id = null
}

# 公网子网（承载 ELB）
resource "huaweicloud_vpc_subnet" "public_1" {
  name       = "${var.project_name}-public-1"
  vpc_id     = huaweicloud_vpc.main.id
  cidr       = "10.0.0.0/24"
  gateway_ip = "10.0.0.1"
}

resource "huaweicloud_vpc_subnet" "public_2" {
  name       = "${var.project_name}-public-2"
  vpc_id     = huaweicloud_vpc.main.id
  cidr       = "10.0.1.0/24"
  gateway_ip = "10.0.1.1"
}

# 私网子网（承载 CCE 节点 / Pod / CSS；经内网服务网络访问同 region 云服务）
resource "huaweicloud_vpc_subnet" "private_1" {
  name       = "${var.project_name}-private-1"
  vpc_id     = huaweicloud_vpc.main.id
  cidr       = "10.0.2.0/24"
  gateway_ip = "10.0.2.1"
}

resource "huaweicloud_vpc_subnet" "private_2" {
  name       = "${var.project_name}-private-2"
  vpc_id     = huaweicloud_vpc.main.id
  cidr       = "10.0.3.0/24"
  gateway_ip = "10.0.3.1"
}

# 安全组（出方向默认放通，不重复声明 egress 规则）
resource "huaweicloud_networking_secgroup" "main" {
  name        = "${var.project_name}-sg"
  description = "auto-damage security group"
}

resource "huaweicloud_networking_secgroup_rule" "allow_http" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = var.allowed_ingress_cidr
  security_group_id = huaweicloud_networking_secgroup.main.id
}

resource "huaweicloud_networking_secgroup_rule" "allow_https" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = var.allowed_ingress_cidr
  security_group_id = huaweicloud_networking_secgroup.main.id
}

# Streamlit 推理 UI 容器端口
resource "huaweicloud_networking_secgroup_rule" "allow_app" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 8501
  port_range_max    = 8501
  remote_ip_prefix  = var.allowed_ingress_cidr
  security_group_id = huaweicloud_networking_secgroup.main.id
}
# 说明：私网子网不部署公网 NAT——CCE 节点拉取 SWR 镜像、Pod 访问 MaaS/CSS/OBS
# 均通过华为云同 region 内网服务网络（100.125.x.x）完成，无需公网出口。
# 若后续需要公网出网（如访问第三方 API），再补 NAT 网关即可。
