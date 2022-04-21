# Censys Unified Cloud Connector

[![Apache License](https://img.shields.io/badge/license-Apache%202.0-orange.svg?style=flat-square)](./LICENSE)

The Censys Unified Cloud Connector is a standalone connector that gathers
assets from various cloud providers and stores them in Censys ASM. This
Connector offers users the ability to supercharge our ASM Platform with total
cloud visibility. This connector currently supports the following cloud
providers: Azure and GCP. Support for AWS and other cloud providers will be
added in the future.

## Supported Platforms and Services

The following platforms and services are supported and will be used to import
Seeds (IP Addresses, Domain Names, CIDRs, and ASNs) as well as Cloud Assets
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

It is important to note that this connector is a Python package. This allows
you to run the connector from the command line as well as enables you to run
the connector in as many different environments as you wish. We have provided
a variety of deployment types and configuration options. We recommend that you
install the package locally to take advantage of the configuration command line
interface (`censys-cc config`). After you have configured the connector, you
can deploy it to your environment. In the following sections, we will provide
a brief overview of how to deploy the connector to your environment.

## Deployment Methods

- [Local Deployment](#local-deployment)
- [Terraform](#terraform)
- [Docker Standalone](#docker-standalone)
- [Docker Compose](#docker-compose)
- [Kubernetes](#kubernetes)

---

### Local Installation

#### Prerequisites

- [Python 3.9+][python-install]
- [Poetry][poetry-install]

#### Installation

```sh
# Clone the repository
git clone https://github.com/censys/censys-cloud-connector.git
cd cloud-connectors-unified

# Ensure you have poetry installed
pip install --upgrade poetry

# Install dependencies
poetry install -E azure -E gcp  # All dependencies (This is recommended)
poetry install -E azure  # Only Azure dependencies
poetry install -E gcp  # Only GCP dependencies
poetry install  # Only core dependencies
```

#### Configuration

To configure the connector, you can use the command line interface. The base
command is `censys-cc`. The following commands are available:

```sh
poetry run censys-cc config  # Configure supported providers
poetry run censys-cc scan    # Scan for assets
```

- The `censys-cc config` command will guide you through the configuration of
  supported cloud providers. This command will assist you in generating a
  `providers.yml` file. This file can contain multiple provider configurations.
- The `censys-cc scan` command runs the connector.

> You will need to have generated your `providers.yml` file using the
> `censys-cc config` commmand before you can run the connector.

#### providers.yml

The `providers.yml` file contains the configuration for all cloud providers.
The file is a YAML file and is structured as follows:

```yaml
- provider: azure
  tenant_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  client_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  client_secret: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  subscription_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  # The subscription_id field takes one or more subscription IDs.
  # subscription_id:
  #   - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  #   - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  # The ignore field takes a list of Azure resource types to ignore during scanning.
  # ignore:
  #   - Microsoft.Network/publicIPAddresses
  #   - Microsoft.ContainerInstance/containerGroups
  #   - Microsoft.Sql/servers
  #   - Microsoft.Network/dnszones
  #   - Microsoft.Storage/storageAccounts
- provider: gcp
  organization_id: xxxxxxxx-xxxx-xxxx
  service_account_json_file: service_account.json
  service_account_email: censys-cloud-connector@project-id.iam.gserviceaccount.com
  # The ignore field takes a list of GCP resource types to ignore during scanning.
  # ignore:
  #   - google.compute.Address
  #   - google.container.Cluster
  #   - google.cloud.sql.Instance
  #   - google.cloud.dns.ManagedZone
  #   - google.cloud.storage.Bucket
```

#### Environment Variables

The following environment variables are available for use in the connector:

- `CENSYS_API_KEY` - Your Censys ASM API key found in the
  [ASM Integrations Page][censys-asm-integrations]. (**Required**)
- `PROVIDERS_CONFIG_FILE` - The path to the `providers.yml` file.
- `SECRETS_DIR` - The path to the directory containing the secrets.
- `LOGGING_LEVEL` - The logging level. Valid values are `DEBUG`, `INFO`,
  `WARN`, `ERROR`, and `CRITICAL`.
- `DRY_RUN` - If set to `true`, the connector will not write any data to the
  ASM platform. This is useful for testing.

---

### [Terraform](./terraform/README.md)

We offer several Terraform deployment options for you to choose from. These
options deploy the connector to the serverless environment in your provider's
cloud.

#### [Option 1: Deploy to GCP](./terraform/google-scheduled-function/README.md)

This option deploys the connector to GCP as a Google Cloud Function.

#### Option 2: Deploy to Azure [](./terraform/azure-scheduled-function/README.md)

> Coming Soon!

This option deploys the connector to Azure as a Azure Function.

---

### [Docker Standalone](./Dockerfile)

This method assumes you have Docker installed and running on your server.

1. Pull the Docker image

```sh
docker pull ghcr.io/censys/censys-cloud-connector:latest
```

- If your environment does not allow you to pull the Docker image, you can
  build it from the Dockerfile using the following command. You can then
  push the image to a Docker registry.

  ```sh
  docker build -t ghcr.io/censys/censys-cloud-connector:latest .
  ```

2. Run the Docker container <!-- markdownlint-disable -->

The following command will run the Docker container. You can specify the
environment variables you want to pass to the container using the `-e` flag.
The container also requires the `providers.yml` file. The `-v` flag will
mount the `providers.yml` file as a volume. If your `providers.yml` references
additional secret files, you can mount it as a volume as well. We also include
the `--rm` flag to ensure the container is removed after it has finished.

```sh
# Mount the providers.yml and secrets files as volumes
docker run --rm \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -v $(pwd)/providers.yml:/app/providers.yml \
  -v $(pwd)/secrets:/app/secrets \
  ghcr.io/censys/censys-cloud-connector:latest

# Alternatively if you do not need the secrets volume
docker run --rm \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -v $(pwd)/providers.yml:/app/providers.yml \
  ghcr.io/censys/censys-cloud-connector:latest
```

> It is important to note that the container runs once by default.

<!-- TODO: Add cron instructions -->

---

### [Docker Compose](./docker-compose.yml)

This method assumes you have Docker and Docker Compose installed and running on
your server.

1. Run the Docker Compose file

```sh
docker-compose up -d
```

---

### [Kubernetes](./kubernetes/censys-cloud-connectors/README.md)

This method assumes you have Kubernetes installed and running on your server.

<!-- TODO: Add steps -->

---

## Known Issues

### Azure Scan Immediately After Creating a Service Principal

<!-- TODO: Remove once this feature has been added to the setup cli -->

In the case where the user has just run the `censys-cc config` command
for Azure and then promptly runs the `censys-cc scan` command, the scan may
fail with a `ClientSecretCredential.get_token failed` exception. This is due
to the fact that Azure is in the process of creating the service principal.
Please wait a few minutes and try again.

Example error message:

```error <!-- markdownlint-disable-next-line MD013 -->
ClientSecretCredential.get_token failed: Authentication failed: AADSTS7000215:Invalid client secret provided. Ensure the secret being sent in the request is the client secret value, not the client secret ID, for a secret added to app 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'.
```

## FAQs

### My Python Version is Not Compatible

It is highly recommended that a Python version shim like
[pyenv][pyenv-install] is used.
Once installed, Poetry will make a virtualenv using the
correct version of Python automatically.

<!-- References -->

[python-install]: https://www.python.org/downloads/
[poetry-install]: https://python-poetry.org/docs/
[pyenv-install]: https://github.com/pyenv/pyenv#installation
[censys-asm-integrations]: https://app.censys.io/integrations
