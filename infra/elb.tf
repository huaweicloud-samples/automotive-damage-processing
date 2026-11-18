# ============================================================================
# 弹性负载均衡（独享型 ELB）：公网入口 HTTP:80 -> 推理 UI 8501
# ELB 绑定 EIP 对外提供访问；监听器与后端池由 CCE Service 注解自动创建
# （见 src/containers/inference/k8s/service.yaml）。
# ============================================================================

resource "huaweicloud_vpc_eip" "elb" {
  publicip {
    type = "5_bgp"
  }
  bandwidth {
    name        = "${var.project_name}-elb-bw"
    size        = 5
    share_type  = "PER"
    charge_mode = "traffic"
  }
}

resource "huaweicloud_elb_loadbalancer" "main" {
  name              = "${var.project_name}-elb"
  vpc_id            = huaweicloud_vpc.main.id
  ipv4_subnet_id    = huaweicloud_vpc_subnet.public_1.ipv4_subnet_id
  availability_zone = ["${var.region}a"]
  l7_flavor_id      = var.elb_l7_flavor_id
  ipv4_eip_id       = huaweicloud_vpc_eip.elb.id

  lifecycle {
    # 后端池由 CCE Service 控制器在运行期维护，交出所有权避免 apply 回滚
    ignore_changes = [cross_vpc_backend]
  }
}
