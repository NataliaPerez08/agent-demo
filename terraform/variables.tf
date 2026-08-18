# ---- Huawei Cloud ----
variable "region" {
  description = "Region de Huawei Cloud"
  type        = string
  default     = "cn-north-4"
}

variable "access_key" {
  description = "Access Key de Huawei Cloud (IAM)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secret Key de Huawei Cloud (IAM)"
  type        = string
  sensitive   = true
}

# ---- SWR ----
variable "swr_org" {
  description = "Organizacion (namespace) en SWR"
  type        = string
  default     = "mi-org"
}

variable "image_tag" {
  description = "Tag de las imagenes"
  type        = string
  default     = "latest"
}

# ---- CCE ----
variable "cce_cluster_name" {
  description = "Nombre del cluster CCE"
  type        = string
  default     = "analyst-agent"
}

variable "cce_cluster_version" {
  description = "Version de Kubernetes"
  type        = string
  default     = "v1.28"
}

variable "cce_flavor" {
  description = "Flavor del cluster CCE (ej: s6.large.2, s6.xlarge.2)"
  type        = string
  default     = "s6.large.2"
}

variable "node_flavor" {
  description = "Flavor de los nodos del cluster"
  type        = string
  default     = "s6.large.2"
}

variable "node_count" {
  description = "Numero de nodos en el node pool"
  type        = number
  default     = 2
}

variable "node_disk_size" {
  description = "Tamano del disco del nodo (GB)"
  type        = number
  default     = 50
}

# ---- Networking ----
variable "vpc_cidr" {
  description = "CIDR del VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR del subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "subnet_gateway" {
  description = "Gateway del subnet"
  type        = string
  default     = "10.0.1.1"
}

variable "dns_nameservers" {
  description = "DNS servers del subnet"
  type        = list(string)
  default     = ["8.8.8.8", "8.8.4.4"]
}

# ---- ELB ----
variable "elb_bandwidth" {
  description = "Ancho de banda del EIP (Mbps)"
  type        = number
  default     = 5
}

# ---- Kubernetes namespace ----
variable "namespace" {
  description = "Namespace de Kubernetes"
  type        = string
  default     = "data-analyst-agent"
}

# ---- App ----
variable "analyst_model" {
  description = "Alias del modelo LLM"
  type        = string
  default     = "analyst-local-fast"
}

variable "openai_api_key" {
  description = "API key de OpenAI (vacia si usa Ollama local)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "litellm_master_key" {
  description = "Master key de LiteLLM"
  type        = string
  default     = "sk-local-secret"
  sensitive   = true
}

variable "api_replicas" {
  description = "Numero de replicas del API"
  type        = number
  default     = 2
}
