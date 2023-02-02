# Deployment Methods

```{toctree}
---
maxdepth: 1
caption: Available Deployment Methods
---

terraform/aws_ecs_task
terraform/google_scheduled_function
docker
kubernetes
local
```

## Picking a Deployment Method

After successfully completing {doc}`Provider Setup <providers_yml>`, choose
a deployment method to run the cloud connector on a schedule.

The Censys Unified Cloud Connector can be deployed in a variety of ways. The
following table provides a high-level overview of the different deployment
methods available.

<!-- markdownlint-disable MD013 MD033 -->
| Deployment Method | Description | Pros | Cons |
|-------------------|-------------|------|------|
| {doc}`AWS ECS Task <terraform/aws_ecs_task>` | Run the connector in an AWS ECS Task. | - Easy to deploy and maintain. <br> - Leverage the power of AWS ECS. <br> - Can be deployed to AWS. | - Requires an AWS account. <br> - Requires the `providers.yml` file and the `secrets` directory to be stored in AWS Secrets Manager. |
| {doc}`Google Scheduled Function <terraform/google_scheduled_function>` | Run the connector in a Google Scheduled Function. | - Easy to deploy and maintain. <br> - Leverage the power of Google Cloud Functions. <br> - Can be deployed to Google Cloud. | - Requires a Google Cloud account. <br> - Requires the `providers.yml` file and the `secrets` directory to be stored in Google Secret Manager. |
| {doc}`Docker <docker>` | Run the connector in a Docker container. | - Easily deployable on any server with Docker installed. | - Requires Docker to be installed on the server. <br> - Requires the `providers.yml` file and the `secrets` directory to be mounted as volumes. |
| {doc}`Kubernetes <kubernetes>` | Run the connector in a Kubernetes cluster. | - Leverage the power of Kubernetes CronJobs. <br> - Can be deployed to a variety of cloud providers. | - Requires a Kubernetes cluster to be deployed. |
| {doc}`Local Deployment <local>` | Run the connector in a local environment. | - Good for testing. <br> - Doesn't require external infrastructure. | - Not scalable. <br> - Doesn't make use of IaaS best practices. |
<!-- TODO: Finish pros and cons -->
<!-- markdownlint-enable MD013 MD033 -->

## Confirm Results

Visit the [Seed Data Page][seed-data] and the
[Storage Buckets Page][storage-bucket] to confirm that you're seeing seeds and
storage buckets from your cloud provider(s).

<!-- References -->
[seed-data]: https://app.censys.io/seeds
[storage-bucket]: https://app.censys.io/storage-bucket
