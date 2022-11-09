# AWS Variables
variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "The AWS region to use."
}

variable "aws_availability_zone" {
  type        = string
  default     = "us-east-1a"
  description = "The AWS availability zones to use."
}

variable "image_uri" {
  type        = string
  default     = "gcr.io/censys-io/censys-cloud-connector"
  description = "The URI of the Docker image to use for ECS."
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "The tag of the Docker image to use for ECS."
}

variable "task_cpu" {
  type        = number
  default     = 1024
  description = "The number of CPU units to allocate to the ECS task."
}

variable "task_memory" {
  type        = number
  default     = 2048
  description = "The amount of memory to allocate to the ECS task."
}

variable "logging_level" {
  type        = string
  default     = "INFO"
  description = "The logging level"
}

variable "schedule_expression" {
  # See https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html#eb-rate-expressions
  # Suggested rates: 1, 3, 6, 12, 24
  type        = string
  default     = "rate(4 hours)"
  description = "Cloud Connector scan frequency."
}

variable "role_name" {
  type        = string
  default     = "CensysCloudConnectorRole"
  description = "The cross-account AWS IAM Role name."
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
