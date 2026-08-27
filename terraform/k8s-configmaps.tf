resource "kubernetes_config_map_v1" "agent_db_init" {
  for_each = { for k in ["default"] : k => {} if local._ready }
  metadata {
    name      = "agent-db-init"
    namespace = var.namespace
  }

  data = {
    "001_audit.sql"      = file("${path.module}/../database/agent/ddl/001_audit.sql")
    "002_dashboards.sql" = file("${path.module}/../database/agent/ddl/002_dashboards.sql")
  }

  depends_on = [kubernetes_manifest.namespace]
}

resource "kubernetes_config_map_v1" "analytics_db_init" {
  for_each = { for k in ["default"] : k => {} if local._ready }
  metadata {
    name      = "analytics-db-init"
    namespace = var.namespace
  }

  data = {
    "001_schema.sql"     = file("${path.module}/../database/analytics/ddl/001_schema.sql")
    "002_indexes.sql"    = file("${path.module}/../database/analytics/ddl/002_indexes.sql")
    "003_views.sql"      = file("${path.module}/../database/analytics/ddl/003_views.sql")
    "004_agent_role.sql" = file("${path.module}/../database/analytics/ddl/004_agent_role.sql")
    "005_seed.sql"       = file("${path.module}/../database/analytics/dml/001_seed.sql")
  }

  depends_on = [kubernetes_manifest.namespace]
}
