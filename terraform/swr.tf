# ---- SWR Organization ----
resource "huaweicloud_swr_organization" "agent" {
  name = var.swr_org
}

# ---- Repositorios de imagenes ----
resource "huaweicloud_swr_repository" "api" {
  organization = huaweicloud_swr_organization.agent.name
  name         = "analyst-api"
  category     = "app_image"
  is_public    = false
}

resource "huaweicloud_swr_repository" "chatbot" {
  organization = huaweicloud_swr_organization.agent.name
  name         = "analyst-chatbot"
  category     = "app_image"
  is_public    = false
}
