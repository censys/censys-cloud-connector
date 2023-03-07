# Google Cloud Scheduled Function

This module allows Terraform to manage
[Google Cloud Scheduled Functions](https://cloud.google.com/functions) for the
Censys Cloud Connector.

## Prerequisites

- Install [Poetry](https://python-poetry.org/docs/).
- Install [Terraform](https://www.terraform.io/downloads).
- Install the [Cloud SDK](https://cloud.google.com/sdk) for your operating
  system.

    If you are running from your local machine, you also need Default
    Application Credentials:

    ```{prompt} bash
    gcloud auth application-default login
    ```

## Setup

1. Ensure you are in the root directory of the project.
2. Source your environment variables.

   ```{prompt} bash
   source .env
   ```

3. Install the dependencies.

   ```{prompt} bash
   poetry install
   ```

4. Ensure your `providers.yml` file contains your cloud provider credentials.

   If you have not already done so, you can create a `providers.yml` file by
   running the following command:

   ```{prompt} bash
   poetry run censys-cc config
   ```

5. Change the working directory to the `google-scheduled-function` directory
   with the following command:

    ```{prompt} bash
    cd ./terraform/google-scheduled-function
    ```

6. Copy `terraform.tfvars.example` to `terraform.tfvars` and update the values
   to match your environment.

   ```{prompt} bash
   cp terraform.tfvars.example terraform.tfvars
   ```

7. Initialize the project with the following command:

   ```{prompt} bash
   terraform init
   ```

8. To see what resources will be created or updated, run the following command:

   ```{prompt} bash
   terraform plan -var-file terraform.tfvars -out=censys-tfplan -input=false
   ```

9. To create or update the resources, run the following command:

   ```{prompt} bash
   terraform apply -input=false censys-tfplan
   ```

## Cleanup

To clean up the resources created by this module, run the following command:

```{prompt} bash
terraform destroy -var-file terraform.tfvars
```

<!-- markdownlint-disable -->
<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| terraform | >= 0.13 |
| google | >= 3.53, < 5.0 |

## Providers

| Name | Version |
|------|---------|
| archive | 2.2.0 |
| external | 2.2.2 |
| google | 4.17.0 |
| local | 2.2.2 |
| null | 3.1.1 |
| random | 3.1.2 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| pubsub\_topic | terraform-google-modules/pubsub/google | ~> 1.0 |

## Resources

| Name | Type |
|------|------|
| [google_cloud_scheduler_job.job](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_scheduler_job) | resource |
| [google_cloudfunctions_function.main](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloudfunctions_function) | resource |
| [google_project_service.gcp_services](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/project_service) | resource |
| [google_secret_manager_secret.censys_api_key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret.providers](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret_iam_member.api_key_member](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_iam_member) | resource |
| [google_secret_manager_secret_iam_member.providers_member](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_iam_member) | resource |
| [google_secret_manager_secret_version.censys_api_key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version) | resource |
| [google_secret_manager_secret_version.providers](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version) | resource |
| [google_secret_manager_secret_version.providers_config](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version) | resource |
| [google_storage_bucket.main](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket_object.main](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_object) | resource |
| [local_file.requirements_txt](https://registry.terraform.io/providers/hashicorp/local/latest/docs/resources/file) | resource |
| [null_resource.copy_build](https://registry.terraform.io/providers/hashicorp/null/latest/docs/resources/resource) | resource |
| [random_id.suffix](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id) | resource |
| [archive_file.main](https://registry.terraform.io/providers/hashicorp/archive/latest/docs/data-sources/file) | data source |
| [external_external.poetry_build](https://registry.terraform.io/providers/hashicorp/external/latest/docs/data-sources/external) | data source |
| [google_project.project](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/project) | data source |
| [google_secret_manager_secret_version.censys_api_key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/secret_manager_secret_version) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket\_force\_destroy | When deleting the GCS bucket containing the cloud function, delete all objects in the bucket first. | `bool` | `true` | no |
| bucket\_labels | A set of key/value label pairs to assign to the bucket. | `map(string)` | `{}` | no |
| bucket\_name | The name to apply to the bucket. Will default to a string of `censys-cloud-connector-bucket-XXXX` with `XXXX` being random characters. | `string` | `""` | no |
| censys\_api\_key | The Censys ASM API key | `string` | n/a | yes |
| create\_bucket | Whether to create a new bucket or use an existing one. If false, `bucket_name` should reference the name of the alternate bucket to use. | `bool` | `true` | no |
| files\_to\_exclude\_in\_source\_dir | Specify files to ignore when reading the source\_dir | `list(string)` | <pre>[<br>  ".gitignore"<br>]</pre> | no |
| function\_available\_memory\_mb | The amount of memory in megabytes allotted for the function to use. | `number` | `256` | no |
| function\_description | The description of the function. | `string` | `"Cloud Function to run the Censys Cloud Connector."` | no |
| function\_labels | A set of key/value label pairs to assign to the function. | `map(string)` | `{}` | no |
| function\_name | The name to apply to the function. Will default to a string of `censys-cloud-connector-function-XXXX` with `XXXX` being random characters. | `string` | `""` | no |
| function\_source\_dir | The directory containing the source code for the function. | `string` | `"function_source"` | no |
| function\_timeout\_s | The amount of time in seconds allotted for the execution of the function. (Can be up to 540 seconds) | `number` | `540` | no |
| gcp\_service\_list | The list of apis necessary for the project | `list(string)` | <pre>[<br>  "cloudbuild.googleapis.com",<br>  "cloudfunctions.googleapis.com",<br>  "cloudresourcemanager.googleapis.com",<br>  "cloudscheduler.googleapis.com",<br>  "pubsub.googleapis.com",<br>  "secretmanager.googleapis.com",<br>  "securitycenter.googleapis.com"<br>]</pre> | no |
| job\_description | Addition text to describe the job | `string` | `"Scheduled time to run the Censys Cloud Connector function"` | no |
| job\_name | The name of the scheduled job to run | `string` | `"censys-cloud-connector-job"` | no |
| job\_schedule | The cron schedule for triggering the cloud function | `string` | `"0 */4 * * *"` | no |
| logging\_level | The logging level | `string` | `"INFO"` | no |
| message\_data | The data to send in the topic message. | `string` | `"c3RhcnQtY2Vuc3lzLWNjLXNjYW4="` | no |
| project\_id | The project ID to host the cloud function in | `string` | n/a | yes |
| providers\_config | The path to the providers config file | `string` | `"../../providers.yml"` | no |
| region | The region the project is in | `string` | `"us-central1"` | no |
| scheduler\_job | An existing Cloud Scheduler job instance | `object({ name = string })` | `null` | no |
| secrets\_dir | The path to the secrets directory | `string` | `"../../secrets"` | no |
| time\_zone | The timezone to use in scheduler | `string` | `"Etc/UTC"` | no |
| topic\_name | Name of pubsub topic connecting the scheduled job and the function | `string` | `"censys-cloud-connector-topic"` | no |
| vpc\_connector | The VPC Network Connector that this cloud function can connect to. It should be set up as fully-qualified URI. The format of this field is projects//locations//connectors/*. | `string` | `null` | no |
| vpc\_connector\_egress\_settings | The egress settings for the connector, controlling what traffic is diverted through it. Allowed values are ALL\_TRAFFIC and PRIVATE\_RANGES\_ONLY. If unset, this field preserves the previously set value. | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| api\_secret\_version | The secret version of the API key |
| bucket\_name | The name of the bucket created |
| function\_name | The name of the function created |
| function\_region | The region the function is in |
| job\_name | The name of the scheduled job to run |
| project\_id | The project ID |
| providers\_secrets\_versions | The secret versions of the providers config |
| topic\_name | The name of the topic created |
<!-- END_TF_DOCS -->
<!-- markdownlint-enable -->
