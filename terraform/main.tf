provider "huaweicloud" {
  region     = var.region
  access_key = var.access_key
  secret_key = var.secret_key
}

# Kubernetes provider apunta al endpoint del cluster CCE.
# El token se obtiene del cluster CCE despues de crearlo.
provider "kubernetes" {
  host  = huaweicloud_cce_cluster.agent.endpoint
  token = huaweicloud_cce_cluster.agent.kube_config_raw
  insecure = true
}
