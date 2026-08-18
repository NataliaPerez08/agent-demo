# ---- Namespace ----
resource "kubernetes_namespace" "agent" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name" = var.namespace
    }
  }

  depends_on = [huaweicloud_cce_node_pool.agent]
}

# ---- Secrets ----

# Secret principal de la app
resource "kubernetes_secret" "app" {
  metadata {
    name      = "app-secrets"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  string_data = {
    MAAS_API_KEY         = var.openai_api_key
    LITELLM_MASTER_KEY     = var.litellm_master_key
    AGENT_DATABASE_URL     = "postgresql://agent:agent@app-postgres-agent:5432/agent"
    ANALYTICS_DATABASE_URL = "postgresql://analyst_agent:analyst@app-postgres-analytics:5432/analytics"
    REDIS_URL              = "redis://app-redis:6379/0"
    ANALYST_MODEL          = var.analyst_model
    LITELLM_DATABASE_URL   = "postgresql://litellm:litellm@litellm-db:5432/litellm"
    LITELLM_REDIS_URL      = "redis://litellm-redis:6379/0"
  }
}

# Credenciales de PostgreSQL agent
resource "kubernetes_secret" "pg_agent" {
  metadata {
    name      = "app-postgres-agent-credentials"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  string_data = {
    POSTGRES_DB       = "agent"
    POSTGRES_USER     = "agent"
    POSTGRES_PASSWORD = "agent"
  }
}

# Credenciales de PostgreSQL analytics
resource "kubernetes_secret" "pg_analytics" {
  metadata {
    name      = "app-postgres-analytics-credentials"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  string_data = {
    POSTGRES_DB       = "analytics"
    POSTGRES_USER     = "analytics_admin"
    POSTGRES_PASSWORD = "analytics_admin"
  }
}

# Credenciales de LiteLLM DB
resource "kubernetes_secret" "litellm_db" {
  metadata {
    name      = "litellm-db-credentials"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  string_data = {
    POSTGRES_DB       = "litellm"
    POSTGRES_USER     = "litellm"
    POSTGRES_PASSWORD = "litellm"
  }
}

# ---- ConfigMap: LiteLLM config ----
resource "kubernetes_config_map" "litellm" {
  metadata {
    name      = "litellm-config"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  data = {
    "config.yaml" = <<-YAML
      model_list:
        - model_name: analyst-fast
          litellm_params:
            model: openai/glm-5.2
            api_base: https://api-ap-southeast-1.modelarts-maas.com/openai/v1
            api_key: os.environ/MAAS_API_KEY

        - model_name: analyst-smart
          litellm_params:
            model: openai/glm-5.2
            api_base: https://api-ap-southeast-1.modelarts-maas.com/openai/v1
            api_key: os.environ/MAAS_API_KEY

        - model_name: analyst-local
          litellm_params:
            model: ollama/qwen2.5:7b
            api_base: http://ollama:11434

        - model_name: analyst-local-fast
          litellm_params:
            model: ollama/qwen2.5:1.5b
            api_base: http://ollama:11434

      litellm_settings:
        drop_params: true

      general_settings:
        master_key: os.environ/LITELLM_MASTER_KEY
    YAML
  }
}

# ---- ConfigMap: agent DB init (audit) ----
resource "kubernetes_config_map" "agent_db_init" {
  metadata {
    name      = "agent-db-init"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  data = {
    "001_audit.sql" = file("${path.module}/../database/agent/ddl/001_audit.sql")
    "002_dashboards.sql" = file("${path.module}/../database/agent/ddl/002_dashboards.sql")
  }
}

# ---- PVCs ----
resource "kubernetes_persistent_volume_claim" "agent_db" {
  metadata {
    name      = "app-agent-db-data"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "csi-disk"
    resources {
      requests = {
        storage = "5Gi"
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "analytics_db" {
  metadata {
    name      = "app-analytics-db-data"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "csi-disk"
    resources {
      requests = {
        storage = "10Gi"
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "litellm_db" {
  metadata {
    name      = "litellm-db-data"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "csi-disk"
    resources {
      requests = {
        storage = "5Gi"
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "ollama_models" {
  metadata {
    name      = "ollama-models"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "csi-disk"
    resources {
      requests = {
        storage = "20Gi"
      }
    }
  }
}
