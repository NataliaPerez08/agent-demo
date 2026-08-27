resource "kubernetes_secret_v1" "app" {
  for_each = { for k in ["default"] : k => {} if local._ready }
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
  for_each = { for k in ["default"] : k => {} if local._ready }
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
  for_each = { for k in ["default"] : k => {} if local._ready }
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
  for_each = { for k in ["default"] : k => {} if local._ready }
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

resource "terraform_data" "swr_pull" {
  for_each = { for k in ["default"] : k => {} if local._ready }

  input = {}

  provisioner "local-exec" {
    environment = {
      KUBECONFIG = local_file.kubeconfig.filename
      ACCESS_KEY = var.access_key
      SECRET_KEY = var.secret_key
      REGION     = var.region
      NAMESPACE  = var.namespace
    }
    command = <<-EOT
      SWR_HOST="swr.$REGION.myhuaweicloud.com"
      LOGIN_KEY=$(printf "$ACCESS_KEY" | openssl dgst -binary -sha256 -hmac "$SECRET_KEY" | od -An -vtx1 | tr -d ' \n')
      AUTH=$(echo -n "$REGION@$ACCESS_KEY:$LOGIN_KEY" | base64 -w0)

      cat <<EOF | kubectl apply -n "$NAMESPACE" -f -
      apiVersion: v1
      kind: Secret
      metadata:
        name: swr-pull-secret
      type: kubernetes.io/dockerconfigjson
      data:
        .dockerconfigjson: $(echo -n "{\"auths\":{\"$SWR_HOST\":{\"username\":\"$REGION@$ACCESS_KEY\",\"password\":\"$LOGIN_KEY\",\"auth\":\"$AUTH\"}}}" | base64 -w0)
      EOF
    EOT
  }

  depends_on = [kubernetes_manifest.namespace]
}
