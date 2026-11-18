# ============================================================================
# NAT 网关：私网子网出公网（MaaS / ModelArts 的 api.modelarts-maas.com 为公网端点，
# CSS/OBS 走同 region 内网服务网络，不走 NAT）
# ⚠️ 用户要求：本 NAT 部署后【保留不销毁】（可复用），destroy 时须排除。
# 模式：标准 NAT 网关（spec=1）。
# ============================================================================

resource "huaweicloud_vpc_eip" "nat" {
  publicip {
    type = "5_bgp"
  }
  bandwidth {
    name        = "${var.project_name}-nat-bw"
    size        = 5
    share_type  = "PER"
    charge_mode = "traffic"
  }
}

resource "huaweicloud_nat_gateway" "main" {
  name        = "${var.project_name}-nat"
  spec        = "1"
  vpc_id      = huaweicloud_vpc.main.id
  subnet_id   = huaweicloud_vpc_subnet.public_1.id
  description = "private subnet egress for MaaS public API"
}

resource "huaweicloud_nat_snat_rule" "private_1" {
  nat_gateway_id = huaweicloud_nat_gateway.main.id
  subnet_id      = huaweicloud_vpc_subnet.private_1.id
  floating_ip_id = huaweicloud_vpc_eip.nat.id
  description    = "SNAT private_1"
}

resource "huaweicloud_nat_snat_rule" "private_2" {
  nat_gateway_id = huaweicloud_nat_gateway.main.id
  subnet_id      = huaweicloud_vpc_subnet.private_2.id
  floating_ip_id = huaweicloud_vpc_eip.nat.id
  description    = "SNAT private_2"
}
