# ---- VPC ----
resource "huaweicloud_vpc" "agent" {
  name = "vpc-analyst-agent"
  cidr = var.vpc_cidr
}

# ---- Subnet ----
resource "huaweicloud_vpc_subnet" "agent" {
  name       = "subnet-analyst-agent"
  vpc_id     = huaweicloud_vpc.agent.id
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway

  dns_list = var.dns_nameservers
}

# ---- Security Group ----
resource "huaweicloud_networking_secgroup" "agent" {
  name = "sg-analyst-agent"
}

# Reglas de entrada: permitir todo dentro del VPC (CCEnetworking)
resource "huaweicloud_networking_secgroup_rule" "ingress_vpc" {
  security_group_id = huaweicloud_networking_secgroup.agent.id
  direction         = "ingress"
  ethertype         = "IPv4"
  remote_ip_prefix  = var.vpc_cidr
}

# Regla de salida: permitir todo
resource "huaweicloud_networking_secgroup_rule" "egress_all" {
  security_group_id = huaweicloud_networking_secgroup.agent.id
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = "0.0.0.0/0"
}
