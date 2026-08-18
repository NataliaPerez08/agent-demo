# ---- EIP para el ELB ----
resource "huaweicloud_eip_address" "api" {
  name = "eip-analyst-api"
  type = "5_bgp"

  bandwidth {
    name        = "bw-analyst-api"
    size        = var.elb_bandwidth
    sharetype   = "PER"
    charge_mode = "bandwidth"
  }
}

# ---- ELB ----
resource "huaweicloud_elb_loadbalancer" "api" {
  name            = "analyst-api-elb"
  vip_subnet_id   = huaweicloud_vpc_subnet.agent.ipv4_subnet_id
  type            = "public"
  ipv4_address    = huaweicloud_eip_address.api.address
  bandwidth_id    = huaweicloud_eip_address.api.id

  tags = {
    project = "analyst-agent"
  }
}

# ---- Listener ----
resource "huaweicloud_elb_listener" "api" {
  name            = "listener-api-8000"
  loadbalancer_id = huaweicloud_elb_loadbalancer.api.id
  protocol        = "HTTP"
  protocol_port   = 8000
  description     = "Listener para Data Analyst Agent API"

  tags = {
    project = "analyst-agent"
  }
}

# ---- Pool ----
resource "huaweicloud_elb_pool" "api" {
  name        = "pool-api"
  protocol    = "HTTP"
  lb_method   = "ROUND_ROBIN"
  listener_id = huaweicloud_elb_listener.api.id

  persistence {
    type = "SOURCE_IP"
  }
}

# ---- Health Monitor ----
resource "huaweicloud_elb_monitor" "api" {
  pool_id  = huaweicloud_elb_pool.api.id
  type     = "HTTP"
  port     = 8000
  url_path = "/health"

  delay          = 5
  timeout        = 3
  max_retries    = 3
}
