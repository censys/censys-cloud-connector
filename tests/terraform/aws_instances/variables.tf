variable "num_buckets" {
  type    = number
  default = 5
  description = "The number of s3 buckets to create"
}

variable "num_instances" {
  type    = number
  default = 5
  description = "The number of ec2 instances to create"
}

variable "num_db_instances" {
  type    = number
  default = 5
  description = "The number of rds instances to create"
}

variable "num_elb_instances" {
  type    = number
  default = 5
  description = "The number of elb instances to create"
}

variable "num_dns_zones" {
  type    = number
  default = 5
  description = "The number of route53 dns zones to create"
}
