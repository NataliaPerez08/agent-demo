terraform {
  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.60"
    }
  }
}
provider "huaweicloud" {
  region = "la-north-2"
}
data "huaweicloud_cce_clusters" "all" {}
output "clusters" {
  value = [for c in data.huaweicloud_cce_clusters.all.clusters : {
    id     = c.id
    name   = c.name
    status = c.status
  }]
}
