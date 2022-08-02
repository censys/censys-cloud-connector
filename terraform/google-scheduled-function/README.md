# Google Cloud Scheduled Function

This module allows Terraform to manage
[Google Cloud Scheduled Functions](https://cloud.google.com/functions) for the
Censys Cloud Connector.

## Prerequisites

- Install [Poetry](https://python-poetry.org/docs/).

- Install the [Cloud SDK](https://cloud.google.com/sdk) for your operating
  system.

    If you are running from your local machine, you also need Default
    Application Credentials:

    ```sh
    gcloud auth application-default login
    ```

- Install [Terraform](https://www.terraform.io/downloads).

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

5. Change the working directory to the `google-scheduled-function` directory
   with the following command:

    ```sh
    cd ./terraform/google-scheduled-function
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
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 3.53, < 5.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_archive"></a> [archive](#provider\_archive) | 2.2.0 |
| <a name="provider_external"></a> [external](#provider\_external) | 2.2.2 |
| <a name="provider_google"></a> [google](#provider\_google) | 4.17.0 |
| <a name="provider_local"></a> [local](#provider\_local) | 2.2.2 |
| <a name="provider_null"></a> [null](#provider\_null) | 3.1.1 |
| <a name="provider_random"></a> [random](#provider\_random) | 3.1.2 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_pubsub_topic"></a> [pubsub\_topic](#module\_pubsub\_topic) | terraform-google-modules/pubsub/google | ~> 1.0 |

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
| <a name="input_bucket_force_destroy"></a> [bucket\_force\_destroy](#input\_bucket\_force\_destroy) | When deleting the GCS bucket containing the cloud function, delete all objects in the bucket first. | `bool` | `true` | no |
| <a name="input_bucket_labels"></a> [bucket\_labels](#input\_bucket\_labels) | A set of key/value label pairs to assign to the bucket. | `map(string)` | `{}` | no |
| <a name="input_bucket_name"></a> [bucket\_name](#input\_bucket\_name) | The name to apply to the bucket. Will default to a string of `censys-cloud-connector-bucket-XXXX` with `XXXX` being random characters. | `string` | `""` | no |
| <a name="input_censys_api_key"></a> [censys\_api\_key](#input\_censys\_api\_key) | The Censys ASM API key | `string` | n/a | yes |
| <a name="input_create_bucket"></a> [create\_bucket](#input\_create\_bucket) | Whether to create a new bucket or use an existing one. If false, `bucket_name` should reference the name of the alternate bucket to use. | `bool` | `true` | no |
| <a name="input_files_to_exclude_in_source_dir"></a> [files\_to\_exclude\_in\_source\_dir](#input\_files\_to\_exclude\_in\_source\_dir) | Specify files to ignore when reading the source\_dir | `list(string)` | <pre>[<br>  ".gitignore"<br>]</pre> | no |
| <a name="input_function_available_memory_mb"></a> [function\_available\_memory\_mb](#input\_function\_available\_memory\_mb) | The amount of memory in megabytes allotted for the function to use. | `number` | `256` | no |
| <a name="input_function_description"></a> [function\_description](#input\_function\_description) | The description of the function. | `string` | `"Cloud Function to run the Censys Cloud Connector."` | no |
| <a name="input_function_labels"></a> [function\_labels](#input\_function\_labels) | A set of key/value label pairs to assign to the function. | `map(string)` | `{}` | no |
| <a name="input_function_name"></a> [function\_name](#input\_function\_name) | The name to apply to the function. Will default to a string of `censys-cloud-connector-function-XXXX` with `XXXX` being random characters. | `string` | `""` | no |
| <a name="input_function_source_dir"></a> [function\_source\_dir](#input\_function\_source\_dir) | The directory containing the source code for the function. | `string` | `"function_source"` | no |
| <a name="input_function_timeout_s"></a> [function\_timeout\_s](#input\_function\_timeout\_s) | The amount of time in seconds allotted for the execution of the function. (Can be up to 540 seconds) | `number` | `540` | no |
| <a name="input_gcp_service_list"></a> [gcp\_service\_list](#input\_gcp\_service\_list) | The list of apis necessary for the project | `list(string)` | <pre>[<br>  "cloudbuild.googleapis.com",<br>  "cloudfunctions.googleapis.com",<br>  "cloudresourcemanager.googleapis.com",<br>  "cloudscheduler.googleapis.com",<br>  "pubsub.googleapis.com",<br>  "secretmanager.googleapis.com",<br>  "securitycenter.googleapis.com"<br>]</pre> | no |
| <a name="input_job_description"></a> [job\_description](#input\_job\_description) | Addition text to describe the job | `string` | `"Scheduled time to run the Censys Cloud Connector function"` | no |
| <a name="input_job_name"></a> [job\_name](#input\_job\_name) | The name of the scheduled job to run | `string` | `"censys-cloud-connector-job"` | no |
| <a name="input_job_schedule"></a> [job\_schedule](#input\_job\_schedule) | The cron schedule for triggering the cloud function | `string` | `"0 */4 * * *"` | no |
| <a name="input_logging_level"></a> [logging\_level](#input\_logging\_level) | The logging level | `string` | `"INFO"` | no |
| <a name="input_message_data"></a> [message\_data](#input\_message\_data) | The data to send in the topic message. | `string` | `"c3RhcnQtY2Vuc3lzLWNjLXNjYW4="` | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The project ID to host the cloud function in | `string` | n/a | yes |
| <a name="input_providers_config"></a> [providers\_config](#input\_providers\_config) | The path to the providers config file | `string` | `"../../providers.yml"` | no |
| <a name="input_region"></a> [region](#input\_region) | The region the project is in | `string` | `"us-central1"` | no |
| <a name="input_scheduler_job"></a> [scheduler\_job](#input\_scheduler\_job) | An existing Cloud Scheduler job instance | `object({ name = string })` | `null` | no |
| <a name="input_secrets_dir"></a> [secrets\_dir](#input\_secrets\_dir) | The path to the secrets directory | `string` | `"../../secrets"` | no |
| <a name="input_time_zone"></a> [time\_zone](#input\_time\_zone) | The timezone to use in scheduler | `string` | `"Etc/UTC"` | no |
| <a name="input_topic_name"></a> [topic\_name](#input\_topic\_name) | Name of pubsub topic connecting the scheduled job and the function | `string` | `"censys-cloud-connector-topic"` | no |
| <a name="input_vpc_connector"></a> [vpc\_connector](#input\_vpc\_connector) | The VPC Network Connector that this cloud function can connect to. It should be set up as fully-qualified URI. The format of this field is projects//locations//connectors/*. | `string` | `null` | no |
| <a name="input_vpc_connector_egress_settings"></a> [vpc\_connector\_egress\_settings](#input\_vpc\_connector\_egress\_settings) | The egress settings for the connector, controlling what traffic is diverted through it. Allowed values are ALL\_TRAFFIC and PRIVATE\_RANGES\_ONLY. If unset, this field preserves the previously set value. | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_api_secret_version"></a> [api\_secret\_version](#output\_api\_secret\_version) | The secret version of the API key |
| <a name="output_bucket_name"></a> [bucket\_name](#output\_bucket\_name) | The name of the bucket created |
| <a name="output_function_name"></a> [function\_name](#output\_function\_name) | The name of the function created |
| <a name="output_function_region"></a> [function\_region](#output\_function\_region) | The region the function is in |
| <a name="output_job_name"></a> [job\_name](#output\_job\_name) | The name of the scheduled job to run |
| <a name="output_project_id"></a> [project\_id](#output\_project\_id) | The project ID |
| <a name="output_providers_secrets_versions"></a> [providers\_secrets\_versions](#output\_providers\_secrets\_versions) | The secret versions of the providers config |
| <a name="output_topic_name"></a> [topic\_name](#output\_topic\_name) | The name of the topic created |
<!-- END_TF_DOCS -->
<!-- markdownlint-enable -->
