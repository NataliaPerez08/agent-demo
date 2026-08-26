provider "huaweicloud" {
  region     = var.region
  access_key = var.access_key
  secret_key = var.secret_key
}

locals {
  _cce = try(huaweicloud_cce_cluster.agent, null)
  k8sReady = local._cce != null && try(local._cce.status, "") == "ACTIVE"
}

# Kubernetes provider: solo se configura si el cluster CCE existe y está ACTIVE.
provider "kubernetes" {
  host  = local.k8sReady ? local._cce.endpoint : ""
  token = local.k8sReady ? local._cce.kube_config_raw : ""
  insecure = local.k8sReady
}
