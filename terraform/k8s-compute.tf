# ---- Ollama (Deployment + Service) ----

resource "kubernetes_deployment" "ollama" {
  metadata {
    name      = "ollama"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "ollama"
      }
    }

    template {
      metadata {
        labels = {
          app = "ollama"
        }
      }

      spec {
        container {
          name  = "ollama"
          image = "ollama/ollama:latest"

          port {
            container_port = 11434
          }

          volume_mount {
            name       = "models"
            mount_path = "/root/.ollama"
          }

          readiness_probe {
            exec {
              command = ["ollama", "list"]
            }
            initial_delay_seconds = 10
            period_seconds        = 5
            failure_threshold     = 30
          }
        }

        volume {
          name = "models"

          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.ollama_models.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "ollama" {
  metadata {
    name      = "ollama"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "ollama"
    }

    port {
      port        = 11434
      target_port = 11434
    }
  }
}

# ---- Ollama Init Job ----

resource "kubernetes_job" "ollama_init" {
  metadata {
    name      = "ollama-init"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    backoff_limit = 3

    template {
      metadata {
        labels = {
          app = "ollama-init"
        }
      }

      spec {
        restart_policy = "Never"

        container {
          name  = "ollama-init"
          image = "ollama/ollama:latest"

          env {
            name  = "OLLAMA_HOST"
            value = "http://ollama:11434"
          }

          command = ["/bin/sh", "-c"]
          args    = [<<-SCRIPT
            echo ">> esperando a que ollama este listo..."
            until ollama list >/dev/null 2>&1; do sleep 2; done
            echo ">> descargando modelos..."
            ollama pull qwen2.5:1.5b
            ollama pull qwen2.5:7b
            if ! ollama list | grep -q 'qwen2.5:1.5b'; then
              echo "!! ERROR: qwen2.5:1.5b no aparece en ollama list"
              exit 1
            fi
            echo ">> modelos listos y verificados"
          SCRIPT
          ]
        }
      }
    }
  }

  depends_on = [kubernetes_deployment.ollama]
}

# ---- LiteLLM (Deployment + Service) ----

resource "kubernetes_deployment" "litellm" {
  metadata {
    name      = "litellm"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "litellm"
      }
    }

    template {
      metadata {
        labels = {
          app = "litellm"
        }
      }

      spec {
        container {
          name  = "litellm"
          image = "ghcr.io/berriai/litellm:main-latest"

          args = ["--config", "/app/config.yaml", "--port", "4000"]

          port {
            container_port = 4000
          }

          env_from {
            secret_ref {
              name = kubernetes_secret.app.metadata[0].name
            }
          }

          volume_mount {
            name       = "config"
            mount_path = "/app/config.yaml"
            sub_path   = "config.yaml"
          }

          readiness_probe {
            http_get {
              path = "/health/liveness"
              port = 4000
            }
            initial_delay_seconds = 10
            period_seconds        = 5
          }
        }

        volume {
          name = "config"

          config_map {
            name = kubernetes_config_map.litellm.metadata[0].name
          }
        }
      }
    }
  }

  depends_on = [kubernetes_job.ollama_init]
}

resource "kubernetes_service" "litellm" {
  metadata {
    name      = "litellm"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "litellm"
    }

    port {
      port        = 4000
      target_port = 4000
    }
  }
}

# ---- API (Deployment + Service) ----

resource "kubernetes_deployment" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = var.api_replicas

    selector {
      match_labels = {
        app = "api"
      }
    }

    template {
      metadata {
        labels = {
          app = "api"
        }
      }

      spec {
        container {
          name  = "api"
          image = "${huaweicloud_swr_repository.api.domain}/${var.swr_org}/${huaweicloud_swr_repository.api.name}:${var.image_tag}"

          port {
            container_port = 8000
          }

          env_from {
            secret_ref {
              name = kubernetes_secret.app.metadata[0].name
            }
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8000
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }
      }
    }
  }

  depends_on = [kubernetes_deployment.litellm]
}

resource "kubernetes_service" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    type = "ClusterIP"

    selector = {
      app = "api"
    }

    port {
      port        = 8000
      target_port = 8000
    }
  }
}

# ---- MCP Glossary (Deployment + Service) ----

resource "kubernetes_deployment" "mcp_glossary" {
  metadata {
    name      = "mcp-glossary"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "mcp-glossary"
      }
    }

    template {
      metadata {
        labels = {
          app = "mcp-glossary"
        }
      }

      spec {
        container {
          name  = "mcp-glossary"
          image = "${huaweicloud_swr_repository.api.domain}/${var.swr_org}/${huaweicloud_swr_repository.api.name}:${var.image_tag}"

          command = ["python", "-m", "mcp_servers.servers.business_glossary"]

          port {
            container_port = 8100
          }

          readiness_probe {
            http_get {
              path = "/mcp"
              port = 8100
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "mcp_glossary" {
  metadata {
    name      = "mcp-glossary"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "mcp-glossary"
    }

    port {
      port        = 8100
      target_port = 8100
    }
  }
}

# ---- MCP Explorer (Deployment + Service) ----

resource "kubernetes_deployment" "mcp_explorer" {
  metadata {
    name      = "mcp-explorer"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "mcp-explorer"
      }
    }

    template {
      metadata {
        labels = {
          app = "mcp-explorer"
        }
      }

      spec {
        container {
          name  = "mcp-explorer"
          image = "${huaweicloud_swr_repository.api.domain}/${var.swr_org}/${huaweicloud_swr_repository.api.name}:${var.image_tag}"

          command = ["python", "-m", "mcp_servers.servers.analytics_explorer"]

          env_from {
            secret_ref {
              name = kubernetes_secret.app.metadata[0].name
            }
          }

          port {
            container_port = 8101
          }

          readiness_probe {
            http_get {
              path = "/mcp"
              port = 8101
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "mcp_explorer" {
  metadata {
    name      = "mcp-explorer"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "mcp-explorer"
    }

    port {
      port        = 8101
      target_port = 8101
    }
  }
}

# ---- Chatbot (Deployment + Service) ----

resource "kubernetes_deployment" "chatbot" {
  metadata {
    name      = "chatbot"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "chatbot"
      }
    }

    template {
      metadata {
        labels = {
          app = "chatbot"
        }
      }

      spec {
        container {
          name  = "chatbot"
          image = "${huaweicloud_swr_repository.chatbot.domain}/${var.swr_org}/${huaweicloud_swr_repository.chatbot.name}:${var.image_tag}"

          port {
            container_port = 8001
          }

          env {
            name  = "AGENT_API_URL"
            value = "http://api:8000"
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8001
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }
      }
    }
  }

  depends_on = [kubernetes_deployment.api]
}

resource "kubernetes_service" "chatbot" {
  metadata {
    name      = "chatbot"
    namespace = kubernetes_namespace.agent.metadata[0].name
  }

  spec {
    selector = {
      app = "chatbot"
    }

    port {
      port        = 8001
      target_port = 8001
    }
  }
}

# ---- API ELB Service (LoadBalancer) ----

resource "kubernetes_service" "api_elb" {
  metadata {
    name      = "api-elb"
    namespace = kubernetes_namespace.agent.metadata[0].name

    annotations = {
      "kubernetes.io/elb.class"          = "union"
      "kubernetes.io/elb.autocreate"     = jsonencode({
        type                = "public"
        name                = "analyst-api-elb"
        bandwidth_name      = "analyst-api-bw"
        bandwidth_chargemode = "bandwidth"
        bandwidth_size      = var.elb_bandwidth
        bandwidth_sharetype = "PER"
        eip_type            = "5_bgp"
      })
      "kubernetes.io/elb.health-check-flag" = "on"
      "kubernetes.io/elb.health-check-option" = jsonencode({
        protocol   = "HTTP"
        port       = 8000
        path       = "/health"
        delay      = "5"
        timeout    = "3"
        max_retries = "3"
      })
    }
  }

  spec {
    type = "LoadBalancer"

    selector = {
      app = "api"
    }

    port {
      port        = 8000
      target_port = 8000
    }
  }

  depends_on = [kubernetes_deployment.api]
}
