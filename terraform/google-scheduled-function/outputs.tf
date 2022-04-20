output "project_id" {
  value       = data.google_project.project.project_id
  description = "The project ID"
}

output "function_region" {
  value       = var.region
  description = "The region the function is in"
}

output "function_name" {
  value       = google_cloudfunctions_function.main.name
  description = "The name of the function created"
}

output "bucket_name" {
  value       = var.create_bucket ? google_storage_bucket.main[0].name : var.bucket_name
  description = "The name of the bucket created"
}

output "job_name" {
  value       = var.job_name
  description = "The name of the scheduled job to run"
}

output "topic_name" {
  value       = module.pubsub_topic.topic
  description = "The name of the topic created"
}

output "api_secret_version" {
  value       = data.google_secret_manager_secret_version.censys_api_key.version
  description = "The secret version of the API key"
  sensitive   = true
}

output "providers_secrets_versions" {
  value       = local.providers_versions_map
  description = "The secret versions of the providers config"
  sensitive   = true
}
