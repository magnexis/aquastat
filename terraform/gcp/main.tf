terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

resource "google_compute_network" "this" {
  name                    = "${local.name_prefix}-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "private" {
  name          = "${local.name_prefix}-private"
  ip_cidr_range = var.private_subnet_cidr
  region        = var.region
  network       = google_compute_network.this.id

  private_ip_google_access = true
}

resource "google_compute_global_address" "private_service_range" {
  name          = "${local.name_prefix}-psa"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.this.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.this.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_range.name]
}

resource "google_project_service" "required" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "servicenetworking.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com"
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "api" {
  account_id   = substr("${var.project_name}${var.environment}api", 0, 28)
  display_name = "AquaStat API"
}

resource "google_secret_manager_secret" "electricity_maps_api_key" {
  secret_id = "${local.name_prefix}-electricity-maps"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "electricity_maps_api_key" {
  secret      = google_secret_manager_secret.electricity_maps_api_key.id
  secret_data = var.electricity_maps_api_key
}

resource "google_secret_manager_secret_iam_member" "api_secret_access" {
  secret_id = google_secret_manager_secret.electricity_maps_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_vpc_access_connector" "run" {
  name          = "${local.name_prefix}-connector"
  region        = var.region
  network       = google_compute_network.this.name
  ip_cidr_range = var.vpc_connector_cidr
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.name_prefix}-postgres"
  region           = var.region
  database_version = var.db_version

  depends_on = [
    google_project_service.required,
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier              = var.db_tier
    availability_type = var.db_availability_type
    disk_type         = "PD_SSD"
    disk_size         = var.db_disk_size_gb
    activation_policy = "ALWAYS"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.this.id
    }
  }

  deletion_protection = var.deletion_protection
}

resource "google_sql_database" "aquastat" {
  name     = var.db_name
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "aquastat" {
  name     = var.db_username
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

resource "google_redis_instance" "cache" {
  name               = "${local.name_prefix}-redis"
  tier               = var.redis_tier
  memory_size_gb     = var.redis_memory_size_gb
  region             = var.region
  authorized_network = google_compute_network.this.id
  redis_version      = "REDIS_7_0"
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service" "api" {
  name     = "${local.name_prefix}-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.api.email
    timeout         = "${var.request_timeout_seconds}s"

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.api_image

      resources {
        limits = {
          cpu    = tostring(var.cpu_limit)
          memory = var.memory_limit
        }
      }

      env {
        name  = "AQUASTAT_DATABASE_URL"
        value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@/${var.db_name}?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"
      }

      env {
        name  = "AQUASTAT_REDIS_URL"
        value = "redis://${google_redis_instance.cache.host}:6379/0"
      }

      env {
        name  = "AQUASTAT_REDIS_ENABLED"
        value = "true"
      }

      env {
        name = "AQUASTAT_ELECTRICITY_MAPS_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.electricity_maps_api_key.secret_id
            version = "latest"
          }
        }
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.run.id
      egress    = "ALL_TRAFFIC"
    }
  }

  depends_on = [
    google_project_service.required,
    google_sql_database.aquastat,
    google_sql_user.aquastat
  ]
}
