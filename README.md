# Cloud Connectors Unified

## Supported Platforms and Services

The following platforms and services are supported and will be used to import
Seeds (IP Addresses, Domains, and Subnets) as well as Cloud Assets
(Object Storage Buckets) into the Censys ASM platform.

### Google Cloud Platform

- [Google Cloud Compute](https://cloud.google.com/products/compute)
  - [Compute Engine](https://cloud.google.com/compute)
- [Google Cloud Containers](https://cloud.google.com/containers)
  - [Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
- [Google Cloud Networking](https://cloud.google.com/products/networking)
  - [Cloud DNS](https://cloud.google.com/dns)
- [Google Cloud Databases](https://cloud.google.com/products/databases)
  - [Cloud SQL](https://cloud.google.com/sql)
- [Google Cloud Storage](https://cloud.google.com/products/storage)
  - [Cloud Storage](https://cloud.google.com/storage)

### Azure Cloud

- [Azure Networking](https://azure.microsoft.com/en-us/product-categories/networking/)
  - [Azure DNS](https://azure.microsoft.com/en-us/services/dns/)
- [Azure Container Services](https://azure.microsoft.com/en-us/product-categories/containers/)
  - [Container Instances](https://azure.microsoft.com/en-us/services/container-instances/)
- [Azure Databases](https://azure.microsoft.com/en-us/product-categories/databases/)
  - [Azure SQL](https://azure.microsoft.com/en-us/products/azure-sql/)
- [Azure Storage](https://azure.microsoft.com/en-us/product-categories/storage/)
  - [Azure Blob Storage](https://azure.microsoft.com/en-us/services/storage/blobs/)

## Getting Started

### Prerequisites

- [Python 3.9+](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/docs/)

### Installation

```sh
# Clone the repository
git clone git@gitlab.com:censys/integrations/cloud-connectors-unified.git
cd cloud-connectors-unified

# Install dependencies
poetry install  # Only core dependencies
poetry install -E azure  # Only Azure dependencies
poetry install -E gcp  # Only GCP dependencies
poetry install -E azure -E gcp  # All dependencies

# Setup your .env file
cp .env.sample .env
```

### Commands

```sh
censys-cc config  # Configure supported providers
censys-cc scan  # Scan for assets
```

## Development

### Useful Commands

```sh
poetry run flake8 .  # Run linter
poetry run black .  # Run formatter
poetry run isort .  # Run import formatter
poetry run mypy .  # Run type checker
pre-commit run --all-files  # Run pre-commit hooks (lint, type check, etc.)
poetry run pytest  # Run tests
poetry run pytest --cov --cov-report html  # Run tests with coverage report
```

### Managing Multiple GCP accounts

When testing the GCP setup cli command, you may need to specify the account
and project to use. Eventually this will be managed by the CLI.

<!-- TODO: This should not be a problem in the future -->

```sh
# Ensure gcloud is authenticated
gcloud auth list
# If you have multiple accounts, you can specify the account to use
gcloud config set account <account>
# Check the current project
gcloud config get-value project
# If you have multiple projects, you can specify the project to use
gcloud config set project <projectId>
```

### VSCode Config

Please note that there is a sample vscode `settings.json` and `extensions.json`
files in the `.vscode` directory.

Features inlcuded in the extensions:

- Use pytest as a test runner
- View `.toml`, `.env` files
- View all todos
- Automatically generate docsstrings
- Spell check

## Known Issues

### Azure Scan Immediately After Creating a Service Principal

In the case where the user has just run the `censys-cc config` command
for Azure and then promptly runs the `censys-cc scan` command, the scan may
fail with a `ClientSecretCredential.get_token failed` exception. This is due
to the fact that Azure is in the process of creating the service principal.
Please wait a few minutes and try again.

Example error message:

```error <!-- markdownlint-disable-next-line MD013 -->
ClientSecretCredential.get_token failed: Authentication failed: AADSTS7000215:Invalid client secret provided. Ensure the secret being sent in the request is the client secret value, not the client secret ID, for a secret added to app 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'.
```
