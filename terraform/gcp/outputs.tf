output "network_name" {
  value = google_compute_network.this.name
}

output "private_subnet_name" {
  value = google_compute_subnetwork.private.name
}

output "cloud_sql_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "redis_host" {
  value = google_redis_instance.cache.host
}

output "cloud_run_service_name" {
  value = google_cloud_run_v2_service.api.name
}
