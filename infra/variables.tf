variable "region" {
  description = "华为云区域"
  type        = string
  default     = "cn-north-4"
}

variable "project_name" {
  description = "资源命名前缀"
  type        = string
  default     = "auto-damage"
}

# 账号域名（Agency 委托归属域），需替换为实际域名
variable "domain_name" {
  description = "华为云账号域名，用于 Agency 委托（delegated_domain_name）"
  type        = string
  default     = "your-huaweicloud-domain"
}

variable "css_password" {
  description = "CSS(OpenSearch) 集群 admin 密码（basic auth）"
  type        = string
  sensitive   = true
}

variable "node_password" {
  description = "CCE 节点 root 密码（也可改用 key_pair）"
  type        = string
  sensitive   = true
}

# SWR 组织/项目名（镜像仓库路径的一部分）
variable "swr_project" {
  description = "SWR 组织名（镜像仓库路径 <swr_host>/<swr_project>/damage-repo）"
  type        = string
  default     = "your-project"
}

# ----------------------------------------------------------------------------
# 计费相关规格：全部显式声明，不使用数据源下标
# ----------------------------------------------------------------------------

# 独享型 ELB 的 L7 规格（cn-north-4 实测 UUID，最小档 s1.small；其他 region 部署前实查）
variable "elb_l7_flavor_id" {
  description = "独享型 ELB 的 L7 规格 ID（显式写死，cn-north-4 实测最小档）"
  type        = string
  default     = "66da67e5-e36b-4c9a-8c06-197ae9e92988"
}

variable "cce_cluster_flavor" {
  description = "CCE 集群规格（单控制节点最小档）"
  type        = string
  default     = "cce.s1.small"
}

variable "cce_node_flavor" {
  description = "CCE 节点 ECS 规格"
  type        = string
  default     = "s6.large.2"
}

variable "cce_node_count" {
  description = "CCE 节点台数"
  type        = number
  default     = 1
}

variable "css_flavor" {
  description = "CSS 集群节点规格"
  type        = string
  default     = "ess.spec-4u8g"
}

variable "css_node_count" {
  description = "CSS 集群节点台数"
  type        = number
  default     = 1
}

variable "css_engine_version" {
  description = "CSS OpenSearch 引擎版本（cn-north-4 商用版 2.19.0，2026-08 实测）"
  type        = string
  default     = "2.19.0"
}

# 入站放通范围：调试期建议收窄到运维者出口 IP，勿长期保留 0.0.0.0/0
variable "allowed_ingress_cidr" {
  description = "允许访问推理 UI 的来源 CIDR"
  type        = string
  default     = "0.0.0.0/0"
}
