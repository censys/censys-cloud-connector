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
```

## Picking a Deployment Method

The Censys Unified Cloud Connector can be deployed in a variety of ways. The
following table provides a high-level overview of the different deployment
methods available.

<!-- markdownlint-disable MD013 MD033 -->
| Deployment Method | Description | Pros | Cons |
|-------------------|-------------|------|------|
| {doc}`Docker <docker>` | Run the connector in a Docker container. | - Easily deployable on any server with Docker installed. | - Requires Docker to be installed on the server. <br> - Requires the `providers.yml` file and the `secrets` directory to be mounted as volumes. |
| {doc}`Kubernetes <kubernetes>` | Run the connector in a Kubernetes cluster. | - Leverage the power of Kubernetes CronJobs. <br> - Can be deployed to a variety of cloud providers. | - Requires a Kubernetes cluster to be deployed. |
| {doc}`AWS ECS Task <terraform/aws_ecs_task>` | Run the connector in an AWS ECS Task. | - Easy to deploy and maintain. <br> - Leverage the power of AWS ECS. <br> - Can be deployed to AWS. | - Requires an AWS account. <br> - Requires the `providers.yml` file and the `secrets` directory to be stored in AWS Secrets Manager. |
| {doc}`Google Scheduled Function <terraform/google_scheduled_function>` | Run the connector in a Google Scheduled Function. | - Easy to deploy and maintain. <br> - Leverage the power of Google Cloud Functions. <br> - Can be deployed to Google Cloud. | - Requires a Google Cloud account. <br> - Requires the `providers.yml` file and the `secrets` directory to be stored in Google Secret Manager. |
<!-- TODO: Finish pros and cons -->
<!-- markdownlint-enable MD013 MD033 -->
