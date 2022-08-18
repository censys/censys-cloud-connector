# https://github.com/terraform-aws-modules/terraform-aws-eventbridge/blob/master/examples/with-ecs-scheduling/outputs.tf
output "eventbridge_bus_arn" {
  description = "The EventBridge Bus ARN"
  value       = module.eventbridge.eventbridge_bus_arn
}

output "eventbridge_rule_ids" {
  description = "The EventBridge Rule IDs"
  value       = module.eventbridge.eventbridge_rule_ids
}

output "eventbridge_rule_arns" {
  description = "The EventBridge Rule ARNs"
  value       = module.eventbridge.eventbridge_rule_arns
}
