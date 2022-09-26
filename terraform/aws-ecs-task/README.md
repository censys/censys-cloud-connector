# AWS Elastic Container Service (ECS) Task

This module allows Terraform to manage
[AWS ECS Service](https://aws.amazon.com/ecs/) for the Censys Cloud Connector.

## Prerequisites

- Install [Poetry](https://python-poetry.org/docs/).
- Install [Terraform](https://www.terraform.io/downloads).
- Install [AWS CLI](https://aws.amazon.com/cli/).

## Login Instructions

Use the [AWS CLI][aws-cli] tool to configure a
[named profile][aws-cli-named-profile]. You can set the profile to use with the
variable `aws_profile`. This can be defined using a Terraform
[variable definition file][terraform-var-def-file].

## Setup

1. Ensure you are in the root directory of the project.
2. Source your environment variables.

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

   ```sh
   cp terraform.tfvars.example terraform.tfvars
   ```

7. Initialize the project with the following command:

   ```sh
   terraform init
   ```

8. To see what resources will be created or updated, run the following command:

   ```sh
   terraform plan -var-file terraform.tfvars
   ```

9. To create or update the resources, run the following command:

   ```sh
   terraform apply -var-file terraform.tfvars
   ```

## Cleanup

To clean up the resources created by this module, run the following command:

```sh
terraform destroy -var-file terraform.tfvars
```

<!-- markdownlint-disable -->
<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| terraform | >= 0.13 |
| aws | ~> 3.0 |

## Providers

| Name | Version |
|------|---------|
| aws | 3.75.2 |
| random | 3.3.2 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| ecs | terraform-aws-modules/ecs/aws | ~> 3.0 |
| eventbridge | terraform-aws-modules/eventbridge/aws | n/a |
| vpc | terraform-aws-modules/vpc/aws | n/a |

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
| aws\_availability\_zone | The AWS availability zones to use. | `string` | `"us-east-1a"` | no |
| aws\_profile | The AWS profile to use. | `string` | `"default"` | no |
| aws\_region | The AWS region to use. | `string` | `"us-east-1"` | no |
| censys\_api\_key | The Censys ASM API key | `string` | n/a | yes |
| image\_tag | The tag of the Docker image to use for ECS. | `string` | `"latest"` | no |
| image\_uri | The URI of the Docker image to use for ECS. | `string` | `"gcr.io/censys-io/censys-cloud-connector"` | no |
| logging\_level | The logging level | `string` | `"INFO"` | no |
| providers\_config | The path to the providers config file | `string` | `"../../providers.yml"` | no |
| role\_name | The cross-account AWS IAM Role name. | `string` | `"CensysCloudConnectorRole"` | no |
| schedule\_expression | Cloud Connector scan frequency. | `string` | `"rate(4 hours)"` | no |
| secrets\_dir | The path to the secrets directory | `string` | `"../../secrets"` | no |
| task\_cpu | The number of CPU units to allocate to the ECS task. | `number` | `1024` | no |
| task\_memory | The amount of memory to allocate to the ECS task. | `number` | `2048` | no |

## Outputs

| Name | Description |
|------|-------------|
| eventbridge\_bus\_arn | The EventBridge Bus ARN |
| eventbridge\_rule\_arns | The EventBridge Rule ARNs |
| eventbridge\_rule\_ids | The EventBridge Rule IDs |
<!-- END_TF_DOCS -->
<!-- markdownlint-enable -->

<!-- References -->
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html
[aws-cli-named-profile]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html
[terraform-var-def-file]: https://www.terraform.io/language/values/variables#variable-definitions-tfvars-files
