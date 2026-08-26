resource "random_password" "node_pool" {
  length  = 16
  special = true
}

locals {
  node_pool_password = coalesce(var.node_pool_password, random_password.node_pool.result)

  pg_agent_password     = coalesce(var.pg_agent_password, "agent")
  pg_analytics_password = coalesce(var.pg_analytics_password, "analytics_admin")
  litellm_db_password   = coalesce(var.litellm_db_password, "litellm")

  swr_host = "swr.${var.region}.myhuaweicloud.com"

  manifest_dir = "${path.module}/../deploy/cce"

  postgres_image = coalesce(var.postgres_image, "${local.swr_host}/${var.swr_org}/postgres:16")
  redis_image    = coalesce(var.redis_image, "${local.swr_host}/${var.swr_org}/redis:7")
  ollama_image   = coalesce(var.ollama_image, "${local.swr_host}/${var.swr_org}/ollama:latest")
  litellm_image  = coalesce(var.litellm_image, "${local.swr_host}/${var.swr_org}/litellm:latest")

  tpl_vars = {
    namespace      = var.namespace
    api_image      = "${local.swr_host}/${var.swr_org}/analyst-api:${var.image_tag}"
    chatbot_image  = "${local.swr_host}/${var.swr_org}/analyst-chatbot:${var.image_tag}"
    postgres_image = local.postgres_image
    redis_image    = local.redis_image
    ollama_image   = local.ollama_image
    litellm_image  = local.litellm_image
    api_replicas   = var.api_replicas
  }
}
