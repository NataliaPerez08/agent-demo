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
  description = "EIP publico del API (via CCE ELB autocreate)"
  value       = "Asignado por CCE ELB autocreate"
}

output "chatbot_eip" {
  description = "EIP publico del Chatbot (via CCE ELB autocreate)"
  value       = "Asignado por CCE ELB autocreate"
}

output "litellm_eip" {
  description = "EIP publico de LiteLLM (via CCE ELB autocreate)"
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
  value       = "ver: kubectl get svc api-elb -n ${var.namespace} -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
}

output "chatbot_endpoint" {
  description = "Endpoint del Chatbot (via ELB)"
  value       = "ver: kubectl get svc chatbot-elb -n ${var.namespace} -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
}

output "litellm_endpoint" {
  description = "Endpoint de LiteLLM (via ELB)"
  value       = "ver: kubectl get svc litellm-elb -n ${var.namespace} -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
}

output "health_check" {
  description = "Health check del API"
  value       = "ver outputs de api_endpoint + /health"
}

output "namespace_k8s" {
  description = "Namespace de Kubernetes"
  value       = var.namespace
}
