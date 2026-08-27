# ---- CCE Cluster ----
resource "huaweicloud_cce_cluster" "agent" {
  name                   = var.cce_cluster_name
  flavor_id              = var.cce_flavor
  cluster_version        = var.cce_cluster_version
  vpc_id                 = huaweicloud_vpc.agent.id
  subnet_id              = huaweicloud_vpc_subnet.agent.id
  container_network_type = "overlay_l2"

  eip = huaweicloud_vpc_eip.cce_master.address

  tags = {
    project = "analyst-agent"
  }

  lifecycle {
    ignore_changes = [agency_name]
  }
}

# ---- Node Pool ----
resource "huaweicloud_cce_node_pool" "agent" {
  cluster_id         = huaweicloud_cce_cluster.agent.id
  name               = "pool-agent"
  flavor_id          = var.node_flavor
  initial_node_count = var.node_count
  os                 = var.node_os
  password           = "Terraform123!"  # cambiar en produccion

  root_volume {
    volumetype = "SSD"
    size       = var.node_disk_size
  }

  data_volumes {
    volumetype = "SSD"
    size       = 100
  }

  tags = {
    project = "analyst-agent"
    pool    = "agent"
  }
}

# ---- EIP para el master del CCE ----
resource "huaweicloud_vpc_eip" "cce_master" {
  name = "eip-cce-master"

  publicip {
    type = "5_bgp"
  }

  bandwidth {
    name        = "bw-cce-master"
    size        = 5
    share_type  = "PER"
    charge_mode = "bandwidth"
  }
}
