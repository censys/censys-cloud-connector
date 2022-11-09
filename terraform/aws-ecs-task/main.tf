resource "random_pet" "censys" {
  # see: https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/pet
  length = 2
  prefix = "CensysCloudConnector"
}

locals {
  project_id = random_pet.censys.id
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      "product" = "CensysCloudConnector"
    }
  }
}

module "vpc" {
  source                  = "terraform-aws-modules/vpc/aws"
  name                    = "CensysCC_VPC"
  cidr                    = "10.0.0.0/16"
  azs                     = [var.aws_availability_zone]
  private_subnets         = ["10.0.141.0/24"]
  public_subnets          = ["10.0.142.0/24"]
  enable_nat_gateway      = true
  single_nat_gateway      = false
  one_nat_gateway_per_az  = false
  map_public_ip_on_launch = false

  default_security_group_egress = [{
    # deny incoming *
    # allow outbound 443
    from_port   = "443"
    to_port     = "443"
    protocol    = "tcp"
    cidr_blocks = "0.0.0.0/0"
  }]
}

module "eventbridge" {
  source = "terraform-aws-modules/eventbridge/aws"

  # Schedules can only be created on default bus
  create_bus = false

  create_role       = true
  role_name         = "ecs-eventbridge"
  attach_ecs_policy = true
  ecs_target_arns   = [aws_ecs_task_definition.cloud_connector.arn]

  # Fire every five minutes
  rules = {
    cloud_connector = {
      description         = "Cloud Connector scan schedule."
      enabled             = true
      schedule_expression = var.schedule_expression
    }
  }

  # Send to a fargate ECS cluster
  targets = {
    cloud_connector = [
      {
        name            = "cloud_connector"
        arn             = module.ecs.ecs_cluster_arn
        attach_role_arn = true

        ecs_target = {
          launch_type         = "FARGATE"
          task_count          = 1
          task_definition_arn = aws_ecs_task_definition.cloud_connector.arn

          network_configuration = {
            assign_public_ip = true
            subnets          = module.vpc.private_subnets
            security_groups  = [module.vpc.default_security_group_id]
          }
        }
      }
    ]
  }
}

module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "~> 3.0"

  name               = local.project_id
  container_insights = true
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}


resource "aws_cloudwatch_log_group" "cloud_connector" {
  name = local.project_id
}

locals {
  providers_files = merge({
    for file_name in fileset(var.secrets_dir, "*.json") : "secrets/${file_name}" => file("${var.secrets_dir}/${file_name}")
  }, { "providers.yml" = file(var.providers_config) })
}

resource "aws_secretsmanager_secret" "censys_api_key" {
  name = "${local.project_id}-CCASMAPIKey"
}

resource "aws_secretsmanager_secret_version" "censys_api_key" {
  secret_id     = aws_secretsmanager_secret.censys_api_key.id
  secret_string = var.censys_api_key
}

resource "aws_secretsmanager_secret" "providers" {
  name = "${local.project_id}-CCProviders"
}

resource "aws_secretsmanager_secret_version" "providers" {
  secret_id     = aws_secretsmanager_secret.providers.id
  secret_string = jsonencode(local.providers_files)
}

resource "aws_iam_policy" "get_secret" {
  name        = "${local.project_id}-GetSecret"
  description = "Allows reading Census Cloud Connector configuration secrets"
  policy = templatefile("${path.module}/templates/get_secret_policy.json.tpl", {
    providers_arn      = aws_secretsmanager_secret_version.providers.arn,
    censys_api_key_arn = aws_secretsmanager_secret_version.censys_api_key.arn
  })
}

resource "aws_iam_policy" "cross_account" {
  name        = "${local.project_id}-CrossAccount"
  description = "Allows organization and accounts to be accessed from the ECS task"

  policy = templatefile("${path.module}/templates/cross_account_policy.json.tpl", {
    role_name = var.role_name
  })
}

resource "aws_iam_role" "cc_task_exec_role" {
  # see: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html
  name        = "${local.project_id}-TaskExecRole"
  description = "Cloud Connector task execution role"

  assume_role_policy = templatefile("${path.module}/templates/task_exec_policy.json.tpl", {})

  managed_policy_arns = [
    aws_iam_policy.get_secret.arn,
    "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  ]
}

resource "aws_iam_role" "cc_task_role" {
  name               = "${local.project_id}-TaskRole"
  description        = "Cloud Connector task role"
  assume_role_policy = templatefile("${path.module}/templates/task_role_policy.json.tpl", {})

  managed_policy_arns = [
    aws_iam_policy.cross_account.arn,
  ]
}

resource "aws_ecs_task_definition" "cloud_connector" {
  family                   = local.project_id
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.cc_task_exec_role.arn
  task_role_arn            = aws_iam_role.cc_task_role.arn
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory

  container_definitions = templatefile("${path.module}/templates/container_def.json.tpl", {
    image                         = "${var.image_uri}:${var.image_tag}"
    logging_level                 = var.logging_level
    awslogs_group                 = aws_cloudwatch_log_group.cloud_connector.name
    awslogs_region                = var.aws_region
    censys_asm_api_key_secret_arn = aws_secretsmanager_secret_version.censys_api_key.arn
    providers_secret_arn          = aws_secretsmanager_secret_version.providers.arn
  })
}
