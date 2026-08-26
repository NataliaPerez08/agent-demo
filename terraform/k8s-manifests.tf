# ---------------------------------------------------------------------------
# Recursos Kubernetes via kubernetes_manifest.
# Fuente unica de verdad: deploy/cce/*.yaml (procesados con templatefile).
# El orden de aplicacion se controla con depends_on entre fases.
# ---------------------------------------------------------------------------

locals {
  # Decodifica un manifiesto multi-doc (separador ---) en una lista de objetos.
  docs_ns = [for d in split("\n---\n", templatefile("${local.manifest_dir}/00-namespace.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]

  docs_litellm_cm       = [for d in split("\n---\n", templatefile("${local.manifest_dir}/02-configmaps.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_pvcs             = [for d in split("\n---\n", templatefile("${local.manifest_dir}/03-pvcs.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_pg_agent         = [for d in split("\n---\n", templatefile("${local.manifest_dir}/10-postgres-agent.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_pg_analytics     = [for d in split("\n---\n", templatefile("${local.manifest_dir}/11-postgres-analytics.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_redis            = [for d in split("\n---\n", templatefile("${local.manifest_dir}/12-redis.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_ollama           = [for d in split("\n---\n", templatefile("${local.manifest_dir}/13-ollama.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_ollama_init      = [for d in split("\n---\n", templatefile("${local.manifest_dir}/14-ollama-init-job.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_litellm_db_redis = [for d in split("\n---\n", templatefile("${local.manifest_dir}/21-litellm-db-redis.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_litellm          = [for d in split("\n---\n", templatefile("${local.manifest_dir}/15-litellm.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_mcp_glossary     = [for d in split("\n---\n", templatefile("${local.manifest_dir}/18-mcp-glossary.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_mcp_explorer     = [for d in split("\n---\n", templatefile("${local.manifest_dir}/19-mcp-explorer.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_api              = [for d in split("\n---\n", templatefile("${local.manifest_dir}/16-api.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_chatbot          = [for d in split("\n---\n", templatefile("${local.manifest_dir}/20-chatbot.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_api_elb          = [for d in split("\n---\n", templatefile("${local.manifest_dir}/17-elb.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_chatbot_elb      = [for d in split("\n---\n", templatefile("${local.manifest_dir}/22-elb-chatbot.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
  docs_litellm_elb      = [for d in split("\n---\n", templatefile("${local.manifest_dir}/23-elb-litellm.yaml", local.tpl_vars)) : yamldecode(d) if trim(d, " \n\t\r") != ""]
}

# ---- Fase 0: Namespace ----

resource "kubernetes_manifest" "namespace" {
  for_each = local.k8sReady ? { "default" = local.docs_ns[0] } : {}
  manifest = each.value
}

# ---- Fase 1: ConfigMaps y PVCs ----

resource "kubernetes_manifest" "litellm_config" {
  for_each = local.k8sReady ? { "default" = local.docs_litellm_cm[0] } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.namespace]
}

resource "kubernetes_manifest" "pvcs" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_pvcs : "03-pvcs/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.namespace]
}

# ---- Fase 2: Bases de datos y cache ----

resource "kubernetes_manifest" "pg_agent" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_pg_agent : "10-postgres-agent/${i}" => doc
  } : {}
  manifest = each.value
  depends_on = [
    kubernetes_manifest.namespace,
    kubernetes_manifest.pvcs,
    kubernetes_secret_v1.pg_agent,
    kubernetes_config_map_v1.agent_db_init,
  ]
}

resource "kubernetes_manifest" "pg_analytics" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_pg_analytics : "11-postgres-analytics/${i}" => doc
  } : {}
  manifest = each.value
  depends_on = [
    kubernetes_manifest.namespace,
    kubernetes_manifest.pvcs,
    kubernetes_secret_v1.pg_analytics,
    kubernetes_config_map_v1.analytics_db_init,
  ]
}

resource "kubernetes_manifest" "redis" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_redis : "12-redis/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.namespace]
}

# ---- Fase 3: Ollama + job init ----

resource "kubernetes_manifest" "ollama" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_ollama : "13-ollama/${i}" => doc
  } : {}
  manifest = each.value
  depends_on = [
    kubernetes_manifest.namespace,
    kubernetes_manifest.pvcs,
  ]
}

resource "kubernetes_manifest" "ollama_init" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_ollama_init : "14-ollama-init/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.ollama]
}

# ---- Fase 4: LiteLLM (DB + cache + servicio) ----

resource "kubernetes_manifest" "litellm_db_redis" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_litellm_db_redis : "21-litellm-db-redis/${i}" => doc
  } : {}
  manifest = each.value
  depends_on = [
    kubernetes_manifest.namespace,
    kubernetes_manifest.pvcs,
    kubernetes_secret_v1.litellm_db,
  ]
}

resource "kubernetes_manifest" "litellm" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_litellm : "15-litellm/${i}" => doc
  } : {}
  manifest = each.value
  depends_on = [
    kubernetes_manifest.namespace,
    kubernetes_manifest.litellm_db_redis,
    kubernetes_manifest.litellm_config,
    kubernetes_secret_v1.app,
  ]
}

# ---- Fase 5: MCP servers ----

resource "kubernetes_manifest" "mcp_glossary" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_mcp_glossary : "18-mcp-glossary/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.namespace]
}

resource "kubernetes_manifest" "mcp_explorer" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_mcp_explorer : "19-mcp-explorer/${i}" => doc
  } : {}
  manifest = each.value
  depends_on = [
    kubernetes_manifest.namespace,
    kubernetes_secret_v1.app,
  ]
}

# ---- Fase 6: API + Chatbot ----

resource "kubernetes_manifest" "api" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_api : "16-api/${i}" => doc
  } : {}
  manifest = each.value
  depends_on = [
    kubernetes_manifest.namespace,
    kubernetes_manifest.pg_agent,
    kubernetes_manifest.pg_analytics,
    kubernetes_manifest.redis,
    kubernetes_manifest.litellm,
    kubernetes_secret_v1.app,
  ]
}

resource "kubernetes_manifest" "chatbot" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_chatbot : "20-chatbot/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.namespace]
}

# ---- Fase 7: ELB services (exposicion publica) ----

resource "kubernetes_manifest" "api_elb" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_api_elb : "17-elb/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.api]
}

resource "kubernetes_manifest" "chatbot_elb" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_chatbot_elb : "22-elb-chatbot/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.chatbot]
}

resource "kubernetes_manifest" "litellm_elb" {
  for_each = local.k8sReady ? {
    for i, doc in local.docs_litellm_elb : "23-elb-litellm/${i}" => doc
  } : {}
  manifest   = each.value
  depends_on = [kubernetes_manifest.litellm]
}
