variable "project_name" {
  type    = string
  default = "aquastat"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "private_subnet_cidr" {
  type    = string
  default = "10.52.0.0/24"
}

variable "vpc_connector_cidr" {
  type    = string
  default = "10.8.0.0/28"
}

variable "api_image" {
  type = string
}

variable "db_name" {
  type    = string
  default = "aquastat"
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_version" {
  type    = string
  default = "POSTGRES_15"
}

variable "db_tier" {
  type    = string
  default = "db-custom-1-3840"
}

variable "db_disk_size_gb" {
  type    = number
  default = 20
}

variable "db_availability_type" {
  type    = string
  default = "ZONAL"
}

variable "redis_tier" {
  type    = string
  default = "STANDARD_HA"
}

variable "redis_memory_size_gb" {
  type    = number
  default = 1
}

variable "electricity_maps_api_key" {
  type      = string
  sensitive = true
}

variable "min_instances" {
  type    = number
  default = 1
}

variable "max_instances" {
  type    = number
  default = 5
}

variable "cpu_limit" {
  type    = number
  default = 1
}

variable "memory_limit" {
  type    = string
  default = "1Gi"
}

variable "request_timeout_seconds" {
  type    = number
  default = 60
}

variable "deletion_protection" {
  type    = bool
  default = false
}
