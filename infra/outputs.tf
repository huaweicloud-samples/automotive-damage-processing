# ============================================================================
# 输出（供部署脚本 / k8s 清单填充）
# ============================================================================

output "obs_frontend_bucket" {
  description = "前端展示桶（图片公读）"
  value       = huaweicloud_obs_bucket.frontend.bucket
}

output "obs_source_bucket" {
  description = "灌库源桶"
  value       = huaweicloud_obs_bucket.source.bucket
}

output "css_os_host" {
  description = "CSS OpenSearch 公网访问主机名（端口 443，basic auth）"
  value       = "${huaweicloud_css_cluster.vector.id}.${var.region}.css.myhuaweicloud.com"
}

output "elb_id" {
  description = "独享型 ELB ID，填入 inference k8s Service 注解 kubernetes.io/elb.id"
  value       = huaweicloud_elb_loadbalancer.main.id
}

output "elb_eip" {
  description = "推理 UI 公网访问地址（HTTP:80）"
  value       = huaweicloud_vpc_eip.elb.address
}

output "cce_kubeconfig" {
  description = "CCE 集群 kubeconfig（敏感）"
  value       = huaweicloud_cce_cluster.main.kube_config_raw
  sensitive   = true
}

output "agency_name" {
  description = "工作负载 Agency 名称"
  value       = huaweicloud_identity_agency.workload.name
}
