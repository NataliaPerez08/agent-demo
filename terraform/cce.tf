# ---- CCE Cluster ----
resource "huaweicloud_cce_cluster" "agent" {
  name                   = var.cce_cluster_name
  flavor_id              = var.cce_flavor
  vpc_id                 = huaweicloud_vpc.agent.id
  subnet_id              = huaweicloud_vpc_subnet.agent.id
  container_network_type = "overlay_l2"
  container_cidr         = "172.16.0.0/16"
  service_cidr           = "10.247.0.0/16"
  version                = var.cce_cluster_version

  eip = huaweicloud_eip_address.cce_master.public_ip

  tags = {
    project = "analyst-agent"
  }
}

# ---- Node Pool ----
resource "huaweicloud_cce_node_pool" "agent" {
  cluster_id         = huaweicloud_cce_cluster.agent.id
  name               = "pool-agent"
  flavor             = var.node_flavor
  initial_node_count = var.node_count
  password           = "Terraform123!"  # cambiar en produccion

  scs_enable        = false
  billing_mode      = 0
  docker_lvm_config_enable = false

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
resource "huaweicloud_eip_address" "cce_master" {
  name = "eip-cce-master"
  type = "5_bgp"

  bandwidth {
    name        = "bw-cce-master"
    size        = 5
    sharetype   = "PER"
    charge_mode = "bandwidth"
  }
}
