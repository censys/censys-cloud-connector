# Terraform Deployment Methods

This guide describes the various ways to deploy the Censys Cloud Connector
using Terraform modules.

## Prerequisites

The following prerequisites are required to run any of the Terraform deployment
methods:

- [Terraform](https://www.terraform.io/downloads)
- [A valid `providers.yml`](../README.md#configuration)

## Methods

- [AWS ECS Task](./aws-ecs-task) - Deploy to an ECS cluster scheduled with
  EventBridge.
- [Google Scheduled Function](./google-scheduled-function) - Deploy using
  Google Cloud Functions.
