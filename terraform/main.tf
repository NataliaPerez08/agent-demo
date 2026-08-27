provider "huaweicloud" {
  region     = var.region
  access_key = var.access_key
  secret_key = var.secret_key
}

locals {
  _cce      = try(huaweicloud_cce_cluster.agent, null)
  _cce_status = try(huaweicloud_cce_cluster.agent.status, "")
  k8sReady  = local._cce_status == "ACTIVE" || local._cce_status == "Available" || local._cce_status == "Available"
}

# Kubernetes provider: solo se configura si el cluster CCE existe y está ACTIVE.
provider "kubernetes" {
  config_path    = local.k8sReady ? local_file.kubeconfig.filename : ""
  config_context = local.k8sReady ? "externalTLSVerify" : ""
}
