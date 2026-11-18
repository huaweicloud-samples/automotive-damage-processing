# ============================================================================
# 容器编排：CCE 集群 + 节点池
# 推理 = Deployment + Service（常驻）；灌库 = 一次性 Job
# （清单见 src/containers/*/k8s）。
# ============================================================================

resource "huaweicloud_cce_cluster" "main" {
  name                   = "${var.project_name}-cce"
  cluster_type           = "VirtualMachine"
  flavor_id              = var.cce_cluster_flavor
  vpc_id                 = huaweicloud_vpc.main.id
  subnet_id              = huaweicloud_vpc_subnet.private_1.id
  container_network_type = "vpc-router"
  # 公网访问（API Server 经 EIP 暴露，便于本地 kubectl 管理）
  eip        = huaweicloud_vpc_eip.cce.address
  custom_san = [huaweicloud_vpc_eip.cce.address]
}

resource "huaweicloud_vpc_eip" "cce" {
  publicip {
    type = "5_bgp"
  }
  bandwidth {
    name        = "${var.project_name}-cce-bw"
    size        = 5
    share_type  = "PER"
    charge_mode = "traffic"
  }
}

resource "huaweicloud_cce_node_pool" "main" {
  cluster_id         = huaweicloud_cce_cluster.main.id
  name               = "${var.project_name}-nodepool"
  flavor_id          = var.cce_node_flavor
  initial_node_count = var.cce_node_count
  availability_zone  = "${var.region}a"
  subnet_id          = huaweicloud_vpc_subnet.private_1.id
  os                 = "Huawei Cloud EulerOS 2.0"
  password           = var.node_password
  runtime            = "containerd"

  root_volume {
    size       = 50
    volumetype = "SSD"
  }

  data_volumes {
    size       = 100
    volumetype = "SSD"
  }

  lifecycle {
    # 节点数由集群自动伸缩 / 人工扩缩在运行期维护
    ignore_changes = [initial_node_count]
  }
}
