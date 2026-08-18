# ---- PostgreSQL Agent (StatefulSet + Service) ----

resource "kubernetes_stateful_set" "pg_agent" {
  metadata {
    name      = "app-postgres-agent"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    service_name = "app-postgres-agent"
    replicas     = 1

    selector {
      match_labels = {
        app = "app-postgres-agent"
      }
    }

    template {
      metadata {
        labels = {
          app = "app-postgres-agent"
        }
      }

      spec {
        container {
          name  = "postgres"
          image = "postgres:16"

          port {
            container_port = 5432
          }

          env_from {
            secret_ref {
              name = kubernetes_secret.pg_agent.metadata[0].name
            }
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }

          volume_mount {
            name       = "init-sql"
            mount_path = "/docker-entrypoint-initdb.d"
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "agent", "-d", "agent"]
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }

        volume {
          name = "data"

          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.agent_db.metadata[0].name
          }
        }

        volume {
          name = "init-sql"

          config_map {
            name = kubernetes_config_map.agent_db_init.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "pg_agent" {
  metadata {
    name      = "app-postgres-agent"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "app-postgres-agent"
    }

    port {
      port        = 5432
      target_port = 5432
    }
  }
}

# ---- PostgreSQL Analytics (StatefulSet + Service) ----

resource "kubernetes_stateful_set" "pg_analytics" {
  metadata {
    name      = "app-postgres-analytics"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    service_name = "app-postgres-analytics"
    replicas     = 1

    selector {
      match_labels = {
        app = "app-postgres-analytics"
      }
    }

    template {
      metadata {
        labels = {
          app = "app-postgres-analytics"
        }
      }

      spec {
        container {
          name  = "postgres"
          image = "postgres:16"

          port {
            container_port = 5432
          }

          env_from {
            secret_ref {
              name = kubernetes_secret.pg_analytics.metadata[0].name
            }
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "analytics_admin", "-d", "analytics"]
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }

        volume {
          name = "data"

          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.analytics_db.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "pg_analytics" {
  metadata {
    name      = "app-postgres-analytics"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "app-postgres-analytics"
    }

    port {
      port        = 5432
      target_port = 5432
    }
  }
}

# ---- Redis (Deployment + Service) ----

resource "kubernetes_deployment" "redis" {
  metadata {
    name      = "app-redis"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "app-redis"
      }
    }

    template {
      metadata {
        labels = {
          app = "app-redis"
        }
      }

      spec {
        container {
          name  = "redis"
          image = "redis:7"

          port {
            container_port = 6379
          }

          readiness_probe {
            exec {
              command = ["redis-cli", "ping"]
            }
            initial_delay_seconds = 3
            period_seconds        = 5
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "redis" {
  metadata {
    name      = "app-redis"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "app-redis"
    }

    port {
      port        = 6379
      target_port = 6379
    }
  }
}

# ---- LiteLLM DB (StatefulSet + Service) ----

resource "kubernetes_stateful_set" "litellm_db" {
  metadata {
    name      = "litellm-db"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    service_name = "litellm-db"
    replicas     = 1

    selector {
      match_labels = {
        app = "litellm-db"
      }
    }

    template {
      metadata {
        labels = {
          app = "litellm-db"
        }
      }

      spec {
        container {
          name  = "postgres"
          image = "postgres:16"

          port {
            container_port = 5432
          }

          env_from {
            secret_ref {
              name = kubernetes_secret.litellm_db.metadata[0].name
            }
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "litellm", "-d", "litellm"]
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }

        volume {
          name = "data"

          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.litellm_db.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "litellm_db" {
  metadata {
    name      = "litellm-db"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "litellm-db"
    }

    port {
      port        = 5432
      target_port = 5432
    }
  }
}

# ---- LiteLLM Redis (Deployment + Service) ----

resource "kubernetes_deployment" "litellm_redis" {
  metadata {
    name      = "litellm-redis"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "litellm-redis"
      }
    }

    template {
      metadata {
        labels = {
          app = "litellm-redis"
        }
      }

      spec {
        container {
          name  = "redis"
          image = "redis:7"

          port {
            container_port = 6379
          }

          readiness_probe {
            exec {
              command = ["redis-cli", "ping"]
            }
            initial_delay_seconds = 3
            period_seconds        = 5
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "litellm_redis" {
  metadata {
    name      = "litellm-redis"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "litellm-redis"
    }

    port {
      port        = 6379
      target_port = 6379
    }
  }
}
