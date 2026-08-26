resource "kubernetes_secret_v1" "app" {
  for_each = local.k8sReady ? { "default" = {} } : {}
  metadata {
    name      = "app-secrets"
    namespace = var.namespace
  }

  data = {
    MAAS_API_KEY           = var.maas_api_key
    LITELLM_MASTER_KEY     = var.litellm_master_key
    LITELLM_BASE_URL       = "http://litellm:4000/v1"
    AGENT_DATABASE_URL     = "postgresql://agent:${local.pg_agent_password}@app-postgres-agent:5432/agent"
    ANALYTICS_DATABASE_URL = "postgresql://analyst_agent:analyst@app-postgres-analytics:5432/analytics"
    REDIS_URL              = "redis://app-redis:6379/0"
    ANALYST_MODEL          = var.analyst_model
    LITELLM_DATABASE_URL   = "postgresql://litellm:${local.litellm_db_password}@litellm-db:5432/litellm"
    LITELLM_REDIS_URL      = "redis://litellm-redis:6379/0"
  }

  depends_on = [kubernetes_manifest.namespace]
}

resource "kubernetes_secret_v1" "pg_agent" {
  for_each = local.k8sReady ? { "default" = {} } : {}
  metadata {
    name      = "app-postgres-agent-credentials"
    namespace = var.namespace
  }

  data = {
    POSTGRES_DB       = "agent"
    POSTGRES_USER     = "agent"
    POSTGRES_PASSWORD = local.pg_agent_password
  }

  depends_on = [kubernetes_manifest.namespace]
}

resource "kubernetes_secret_v1" "pg_analytics" {
  for_each = local.k8sReady ? { "default" = {} } : {}
  metadata {
    name      = "app-postgres-analytics-credentials"
    namespace = var.namespace
  }

  data = {
    POSTGRES_DB       = "analytics"
    POSTGRES_USER     = "analytics_admin"
    POSTGRES_PASSWORD = local.pg_analytics_password
  }

  depends_on = [kubernetes_manifest.namespace]
}

resource "kubernetes_secret_v1" "litellm_db" {
  for_each = local.k8sReady ? { "default" = {} } : {}
  metadata {
    name      = "litellm-db-credentials"
    namespace = var.namespace
  }

  data = {
    POSTGRES_DB       = "litellm"
    POSTGRES_USER     = "litellm"
    POSTGRES_PASSWORD = local.litellm_db_password
  }

  depends_on = [kubernetes_manifest.namespace]
}
