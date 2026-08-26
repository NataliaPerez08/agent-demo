# ---- EIP para el ELB ----
resource "huaweicloud_vpc_eip" "api" {
  name = "eip-analyst-api"

  publicip {
    type = "5_bgp"
  }

  bandwidth {
    name        = "bw-analyst-api"
    size        = var.elb_bandwidth
    share_type  = "PER"
    charge_mode = "bandwidth"
  }
}

# ---- ELB ----
resource "huaweicloud_elb_loadbalancer" "api" {
  name              = "analyst-api-elb"
  availability_zone = ["la-north-2a"]

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
  pool_id        = huaweicloud_elb_pool.api.id
  protocol       = "HTTP"
  port           = 8000
  url_path       = "/health"

  interval       = 5
  timeout        = 3
  max_retries    = 3
}
