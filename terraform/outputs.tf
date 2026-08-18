# ---- Outputs ----

output "cce_cluster_id" {
  description = "ID del cluster CCE"
  value       = huaweicloud_cce_cluster.agent.id
}

output "cce_master_eip" {
  description = "EIP del master del CCE"
  value       = huaweicloud_eip_address.cce_master.public_ip
}

output "api_eip" {
  description = "EIP publico del API (via ELB)"
  value       = huaweicloud_eip_address.api.address
}

output "swr_api_repository" {
  description = "Repositorio SWR de la imagen API"
  value       = "${huaweicloud_swr_repository.api.domain}/${var.swr_org}/${huaweicloud_swr_repository.api.name}"
}

output "swr_chatbot_repository" {
  description = "Repositorio SWR de la imagen chatbot"
  value       = "${huaweicloud_swr_repository.chatbot.domain}/${var.swr_org}/${huaweicloud_swr_repository.chatbot.name}"
}

output "namespace" {
  description = "Namespace de Kubernetes"
  value       = kubernetes_namespace.agent.metadata[0].name
}

output "api_endpoint" {
  description = "Endpoint del API (via ELB)"
  value       = "http://${huaweicloud_eip_address.api.address}:8000"
}

output "health_check" {
  description = "Health check del API"
  value       = "curl http://${huaweicloud_eip_address.api.address}:8000/health"
}
