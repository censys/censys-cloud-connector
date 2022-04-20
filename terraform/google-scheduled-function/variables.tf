# GCP Variables

variable "region" {
  description = "The region the project is in"
  type        = string
  default     = "us-central1"
}

variable "project_id" {
  description = "The project ID to host the cloud function in"
  type        = string
}

variable "gcp_service_list" {
  description = "The list of apis necessary for the project"
  type        = list(string)
  default = [
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "securitycenter.googleapis.com"
  ]
}


# Scheduler Job Variables

variable "job_name" {
  type        = string
  description = "The name of the scheduled job to run"
  default     = "censys-cloud-connector-job"
}

variable "job_description" {
  type        = string
  description = "Addition text to describe the job"
  default     = "Scheduled time to run the Censys Cloud Connector function"
}

variable "job_schedule" {
  description = "The cron schedule for triggering the cloud function"
  type        = string
  default     = "0 */4 * * *"
}

variable "time_zone" {
  type        = string
  description = "The timezone to use in scheduler"
  default     = "Etc/UTC"
}

variable "scheduler_job" {
  type        = object({ name = string })
  description = "An existing Cloud Scheduler job instance"
  default     = null
}


# Pub/Sub Variables

variable "topic_name" {
  type        = string
  description = "Name of pubsub topic connecting the scheduled job and the function"
  default     = "censys-cloud-connector-topic"
}

variable "message_data" {
  type        = string
  description = "The data to send in the topic message."
  default     = "c3RhcnQtY2Vuc3lzLWNjLXNjYW4="
}

# Bucket Variables

variable "create_bucket" {
  type        = bool
  default     = true
  description = "Whether to create a new bucket or use an existing one. If false, `bucket_name` should reference the name of the alternate bucket to use."
}

variable "bucket_name" {
  type        = string
  default     = ""
  description = "The name to apply to the bucket. Will default to a string of `censys-cloud-connector-bucket-XXXX` with `XXXX` being random characters."
}

variable "bucket_labels" {
  type        = map(string)
  default     = {}
  description = "A set of key/value label pairs to assign to the bucket."
}

variable "bucket_force_destroy" {
  type        = bool
  default     = true
  description = "When deleting the GCS bucket containing the cloud function, delete all objects in the bucket first."
}


# Function Variables

variable "function_name" {
  type        = string
  default     = ""
  description = "The name to apply to the function. Will default to a string of `censys-cloud-connector-function-XXXX` with `XXXX` being random characters."
}

variable "function_description" {
  type        = string
  default     = "Cloud Function to run the Censys Cloud Connector."
  description = "The description of the function."
}

variable "function_labels" {
  type        = map(string)
  default     = {}
  description = "A set of key/value label pairs to assign to the function."
}

variable "function_available_memory_mb" {
  type        = number
  default     = 256
  description = "The amount of memory in megabytes allotted for the function to use."
}

variable "function_timeout_s" {
  type        = number
  default     = 540
  description = "The amount of time in seconds allotted for the execution of the function. (Can be up to 540 seconds)"
}

variable "function_source_dir" {
  type        = string
  default     = "function_source"
  description = "The directory containing the source code for the function."
}

variable "files_to_exclude_in_source_dir" {
  type        = list(string)
  description = "Specify files to ignore when reading the source_dir"
  default     = [".gitignore"]
}

variable "vpc_connector" {
  type        = string
  default     = null
  description = "The VPC Network Connector that this cloud function can connect to. It should be set up as fully-qualified URI. The format of this field is projects//locations//connectors/*."
}

variable "vpc_connector_egress_settings" {
  type        = string
  default     = null
  description = "The egress settings for the connector, controlling what traffic is diverted through it. Allowed values are ALL_TRAFFIC and PRIVATE_RANGES_ONLY. If unset, this field preserves the previously set value."
}


# Environment Variables

variable "logging_level" {
  type        = string
  default     = "INFO"
  description = "The logging level"
}

variable "censys_api_key" {
  type        = string
  sensitive   = true
  description = "The Censys ASM API key"
}

variable "providers_config" {
  type        = string
  default     = "../../providers.yml"
  description = "The path to the providers config file"
}

variable "secrets_dir" {
  type        = string
  default     = "../../secrets"
  description = "The path to the secrets directory"
}
