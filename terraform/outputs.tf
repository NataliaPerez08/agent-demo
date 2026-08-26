# ---- Outputs ----

output "cce_cluster_id" {
  description = "ID del cluster CCE"
  value       = huaweicloud_cce_cluster.agent.id
}

output "cce_master_eip" {
  description = "EIP del master del CCE"
  value       = huaweicloud_vpc_eip.cce_master.address
}

output "api_eip" {
  description = "EIP publico del API (via ELB)"
  value       = huaweicloud_vpc_eip.api.address
}

output "chatbot_eip" {
  description = "EIP publico del Chatbot (via ELB)"
  value       = "Asignado por CCE ELB autocreate"
}

output "litellm_eip" {
  description = "EIP publico de LiteLLM (via ELB)"
  value       = "Asignado por CCE ELB autocreate"
}

output "swr_api_repository" {
  description = "Repositorio SWR de la imagen API"
  value       = "${var.swr_org}/analyst-api"
}

output "swr_chatbot_repository" {
  description = "Repositorio SWR de la imagen chatbot"
  value       = "${var.swr_org}/analyst-chatbot"
}

output "namespace" {
  description = "Namespace de Kubernetes"
  value       = var.namespace
}

output "api_endpoint" {
  description = "Endpoint del API (via ELB)"
  value       = "http://${huaweicloud_vpc_eip.api.address}:8000"
}

output "chatbot_endpoint" {
  description = "Endpoint del Chatbot (via ELB)"
  value       = "http://<chatbot-elb-ip>:8001 (ver kubectl get svc chatbot-elb)"
}

output "litellm_endpoint" {
  description = "Endpoint de LiteLLM (via ELB)"
  value       = "http://<litellm-elb-ip>:4000 (ver kubectl get svc litellm-elb)"
}

output "health_check" {
  description = "Health check del API"
  value       = "curl http://${huaweicloud_vpc_eip.api.address}:8000/health"
}
