resource "huaweicloud_swr_temporary_login_command" "local" {
  enhanced = true
}

output "swr_login" {
  value = huaweicloud_swr_temporary_login_command.local.x_swr_docker_login
}
