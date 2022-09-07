# AWS Elastic Container Service (ECS) Task

This module allows Terraform to manage
[AWS ECS Service](https://aws.amazon.com/ecs/) for the Censys Cloud Connector.

## Prerequisites

- Install [Poetry](https://python-poetry.org/docs/).
- Install [Terraform](https://www.terraform.io/downloads).
- Install [AWS CLI](https://aws.amazon.com/cli/).
<!-- TODO: Add login instructions -->

## Setup

1. Ensure you are in the root directory of the project.
2. Source your environment variables as set in the main [README](../../README.md#environment-variables)

   ```sh
   source .env
   ```

3. Run `poetry install -E aws -E azure -E gcp` to install the dependencies.
4. Ensure your `providers.yml` file contains your cloud provider credentials.

   If you have not already done so, you can create a `providers.yml` file by
   running the following command:

   ```sh
   poetry run censys-cc config
   ```

5. Change the working directory to the `aws-ecs-task` directory
   with the following command:

    ```sh
    cd ./terraform/aws-ecs-task
    ```

6. Copy `terraform.tfvars.example` to `terraform.tfvars` and update the values
   to match your environment.
7. Run `terraform init` to initialize the project.
8. Run `terraform plan -var-file terraform.tfvars` to see what resources will
   be created.
9. Run `terraform apply -var-file terraform.tfvars` to create the resources.

## Cleanup

Run `terraform destroy -var-file terraform.tfvars` to destroy the resources.

<!-- markdownlint-disable -->
<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 0.13 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 3.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 3.75.2 |
| <a name="provider_random"></a> [random](#provider\_random) | 3.3.2 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_ecs"></a> [ecs](#module\_ecs) | terraform-aws-modules/ecs/aws | ~> 3.0 |
| <a name="module_eventbridge"></a> [eventbridge](#module\_eventbridge) | terraform-aws-modules/eventbridge/aws | n/a |
| <a name="module_vpc"></a> [vpc](#module\_vpc) | terraform-aws-modules/vpc/aws | n/a |

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.cloud_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_ecs_task_definition.cloud_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_task_definition) | resource |
| [aws_iam_policy.cross_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy.get_secret](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_role.cc_task_exec_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role.cc_task_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_secretsmanager_secret.censys_api_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret) | resource |
| [aws_secretsmanager_secret.providers](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret) | resource |
| [aws_secretsmanager_secret_version.censys_api_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_version) | resource |
| [aws_secretsmanager_secret_version.providers](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_version) | resource |
| [random_pet.censys](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/pet) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_aws_availability_zone"></a> [aws\_availability\_zone](#input\_aws\_availability\_zone) | The AWS availability zones to use. | `string` | `"us-east-1a"` | no |
| <a name="input_aws_profile"></a> [aws\_profile](#input\_aws\_profile) | The AWS profile to use. | `string` | `"default"` | no |
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | The AWS region to use. | `string` | `"us-east-1"` | no |
| <a name="input_censys_api_key"></a> [censys\_api\_key](#input\_censys\_api\_key) | The Censys ASM API key | `string` | n/a | yes |
| <a name="input_image_tag"></a> [image\_tag](#input\_image\_tag) | The tag of the Docker image to use for ECS. | `string` | `"latest"` | no |
| <a name="input_image_uri"></a> [image\_uri](#input\_image\_uri) | The URI of the Docker image to use for ECS. | `string` | `"gcr.io/censys-io/censys-cloud-connector"` | no |
| <a name="input_logging_level"></a> [logging\_level](#input\_logging\_level) | The logging level | `string` | `"INFO"` | no |
| <a name="input_providers_config"></a> [providers\_config](#input\_providers\_config) | The path to the providers config file | `string` | `"../../providers.yml"` | no |
| <a name="input_role_name"></a> [role\_name](#input\_role\_name) | The cross-account AWS IAM Role name. | `string` | `"CensysCloudConnectorRole"` | no |
| <a name="input_schedule_expression"></a> [schedule\_expression](#input\_schedule\_expression) | Cloud Connector scan frequency. | `string` | `"rate(4 hours)"` | no |
| <a name="input_secrets_dir"></a> [secrets\_dir](#input\_secrets\_dir) | The path to the secrets directory | `string` | `"../../secrets"` | no |
| <a name="input_task_cpu"></a> [task\_cpu](#input\_task\_cpu) | The number of CPU units to allocate to the ECS task. | `number` | `1024` | no |
| <a name="input_task_memory"></a> [task\_memory](#input\_task\_memory) | The amount of memory to allocate to the ECS task. | `number` | `2048` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_eventbridge_bus_arn"></a> [eventbridge\_bus\_arn](#output\_eventbridge\_bus\_arn) | The EventBridge Bus ARN |
| <a name="output_eventbridge_rule_arns"></a> [eventbridge\_rule\_arns](#output\_eventbridge\_rule\_arns) | The EventBridge Rule ARNs |
| <a name="output_eventbridge_rule_ids"></a> [eventbridge\_rule\_ids](#output\_eventbridge\_rule\_ids) | The EventBridge Rule IDs |
<!-- END_TF_DOCS -->
<!-- markdownlint-enable -->
