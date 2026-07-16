variable "project_name" {
  type    = string
  default = "aquastat"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "aws_region" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  type = list(string)
}

variable "private_subnet_cidrs" {
  type = list(string)
}

variable "allowed_ingress_cidrs" {
  type    = list(string)
  default = ["10.0.0.0/8"]
}

variable "api_image" {
  type = string
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "api_desired_count" {
  type    = number
  default = 2
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

variable "db_engine_version" {
  type    = string
  default = "15.7"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_max_allocated_storage" {
  type    = number
  default = 100
}

variable "db_backup_retention_days" {
  type    = number
  default = 7
}

variable "db_multi_az" {
  type    = bool
  default = false
}

variable "deletion_protection" {
  type    = bool
  default = false
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "redis_cluster_size" {
  type    = number
  default = 1
}

variable "redis_engine_version" {
  type    = string
  default = "7.1"
}

variable "redis_auth_token" {
  type      = string
  sensitive = true
}

variable "electricity_maps_api_key" {
  type      = string
  sensitive = true
}

variable "api_key_salt" {
  type      = string
  sensitive = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
