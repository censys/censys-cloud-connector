# Censys Unified Cloud Connector

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/censys/censys-cloud-connector)][github]
[![PyPI - License](https://img.shields.io/pypi/l/censys-cloud-connectors)][license]
[![AWS Supported](https://img.shields.io/badge/-Supported-orange?logo=amazonaws)](#amazon-web-services)
[![Azure Supported](https://img.shields.io/badge/-Supported-green?logo=microsoftazure)](#azure-cloud)
[![GCP Supported](https://img.shields.io/badge/-Supported-blue?logo=googlecloud&logoColor=white)](#google-cloud-platform)

The Censys Unified Cloud Connector is a standalone connector that gathers
assets from various cloud providers and stores them in Censys ASM. This
Connector offers users the ability to supercharge our ASM Platform with total
cloud visibility. This connector currently supports the following cloud
providers: AWS, Azure, and GCP.

## Supported Platforms and Services

The following platforms and services are supported and will be used to import
Seeds (IP Addresses, Domain Names, CIDRs, and ASNs) as well as Cloud Assets
(Object Storage Buckets) into the Censys ASM platform.

### Amazon Web Services

- [Compute](https://aws.amazon.com/products/compute/)
  - [Elastic Container Service (ECS)](https://aws.amazon.com/ecs/)
  - [Elastic Compute Cloud (EC2)](https://aws.amazon.com/ec2/)
- [Database](https://aws.amazon.com/products/databases/)
  - [Relational Database Service (RDS)](https://aws.amazon.com/rds/)
- [Network & Content Delivery](https://aws.amazon.com/products/networking)
  - [API Gateway](https://aws.amazon.com/api-gateway)
  - [Elastic Load Balancing (ELB)](https://aws.amazon.com/elasticloadbalancing/)
  - [Route53](https://aws.amazon.com/route53/)
- [Cloud Storage](https://aws.amazon.com/products/storage/)
  - [Simple Storage Service (S3)](https://aws.amazon.com/s3/features/)

### Azure Cloud

- [Azure Networking](https://azure.microsoft.com/en-us/product-categories/networking/)
  - [Azure DNS](https://azure.microsoft.com/en-us/services/dns/)
- [Azure Container Services](https://azure.microsoft.com/en-us/product-categories/containers/)
  - [Container Instances](https://azure.microsoft.com/en-us/services/container-instances/)
- [Azure Databases](https://azure.microsoft.com/en-us/product-categories/databases/)
  - [Azure SQL](https://azure.microsoft.com/en-us/products/azure-sql/)
- [Azure Storage](https://azure.microsoft.com/en-us/product-categories/storage/)
  - [Azure Blob Storage](https://azure.microsoft.com/en-us/services/storage/blobs/)

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
cd censys-cloud-connector

# Ensure you have poetry installed
pip install --upgrade poetry

# Recommended installation
poetry install -E aws -E azure -E gcp  # All dependencies (This is recommended)

# Other installations
# poetry install -E aws # Only AWS dependencies
# poetry install -E azure  # Only Azure dependencies
# poetry install -E gcp  # Only GCP dependencies

# Copy .env file
cp .env.sample .env
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

`.env.sample` is a sample file that contains the above environment variables.
Please use this file as a template to create your own `.env` file.

#### Configuration

To configure the connector, you can use the command line interface. The base
command is `censys-cc`. The configuration command is:

```sh
poetry run censys-cc config  # Configure supported providers
```

The `censys-cc config` command will guide you through the configuration of
supported cloud providers. This command will assist you in generating a
`providers.yml` file. This file can contain multiple provider configurations.
You can optionally specify a provider in the command line with the flag
`--provider`.

> Before configuring the connector, make sure you are logged in to your cloud
> provider's CLI tool. See our [supported providers](#supported-providers)
> below for more information.

**You have successfully configured your cloud connector if your
[providers.yml](./providers.yml) file is populated with your credentials.**

#### Supported Providers

Log in to your cloud provider's CLI tool using the following commands:

- [AWS CLI][aws-cli]: `aws configure` or `aws configure sso`

- [Azure CLI][azure-cli]: `az login`

- [Google's gcloud CLI][gcloud-cli]: `gcloud auth login`

#### providers.yml

The `providers.yml` file contains the configuration for all cloud providers.
The file is a YAML file and is structured as follows:

> You will need to have generated your `providers.yml` file using the
> `censys-cc config` command before you can run the connector.

```yaml
- provider: aws
  account_number: xxxxxxxxxxxx
  access_key: xxxxxxxxxxxxxxxxxxxx
  secret_key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  regions:
    - xxxxxxxxx
  # The ignore field takes a list of AWS resource types to ignore during scanning.
  # ignore:
  #   - AWS::ApiGateway
  #   - AWS::ECS
  #   - AWS::ElasticLoadBalancing
  #   - AWS::NetworkInterface
  #   - AWS::RDS
  #   - AWS::Route53
  #   - AWS::S3
  # It is also possible to define roles to assume for multiple accounts.
  # accounts:
  # - account_number: xxxxxxxxxxxx
  #   access_key: xxxxxxxxxxxxxxxxxxxx
  #   secret_key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  #   role_name: xxxxxxxxxxxxxxxxxxxx
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

---

### Local Deployment

To run the connector, you can use the command line interface.

```sh
poetry run censys-cc scan  # Scan cloud assets
```

The `censys-cc scan` command runs the connector.

#### Default settings

- The connector will scan for assets from all providers in
[`providers.yml`](./providers.yml).
- The connector will run once.

#### Additional options

- You can specify one or more providers in the command line with the flag
`--provider`. The connector will only scan for assets from the specified
providers.

- You can set a scheduled interval for the connector to run on with the flag
`--daemon`. This option takes in a time interval in hours. If you do not
specify an interval, the default will be set to 1 hour.

  ```sh
  censys-cc scan --daemon       # Run every 1 hour
  censys-cc scan --daemon 1.5   # Run every 1.5 hours
  ```

---

### [Terraform](./terraform/README.md)

We offer several Terraform deployment options for you to choose from. These
options deploy the connector to the serverless environment in your provider's
cloud.

#### [Option 1: Deploy to GCP](./terraform/google-scheduled-function/README.md)

This option deploys the connector to GCP as a Google Cloud Function.

#### [Option 2: Deploy to Azure](./terraform/azure-scheduled-function/README.md)

> Coming Soon!

#### [Option 3: Deploy to AWS](./terraform/aws-scheduled-function/README.md)

> Coming Soon!

This option deploys the connector to Azure as a Azure Function.

---

### [Docker Standalone](./Dockerfile)

This method assumes you have Docker installed and running on your server.

1. Pull the Docker image <!-- markdownlint-disable -->

```sh
docker pull gcr.io/censys-io/censys-cloud-connector:latest
```

- If your environment does not allow you to pull the Docker image, you can
  build it from the Dockerfile using the following command. You can then
  push the image to a Docker registry.

  ```sh
  docker build -t gcr.io/censys-io/censys-cloud-connector:latest .
  ```

2. Run the Docker container <!-- markdownlint-disable -->

The following command will run the Docker container. You can specify the
environment variables you want to pass to the container using the `-e` flag.
The container also requires the `providers.yml` file. The `-v` flag will
mount the `providers.yml` file as a volume. If your `providers.yml` references
additional secret files, you can mount it as a volume as well. The `-d` flag
is used to run the container in the background. We also include the `--rm`
flag to ensure the container is removed after it has finished.

```sh
# Ensure you have sourced your environmental variables
source .env

# Mount the providers.yml and secrets files as volumes
docker run -d --rm \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -v $(pwd)/providers.yml:/app/providers.yml \
  -v $(pwd)/secrets:/app/secrets \
  gcr.io/censys-io/censys-cloud-connector:latest \
  scan --daemon 4

# Alternatively if you do not need the secrets volume
docker run -d --rm \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -v $(pwd)/providers.yml:/app/providers.yml \
  gcr.io/censys-io/censys-cloud-connector:latest \
  scan --daemon 4

# Additionally if you only need to scan once
docker run --rm \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -v $(pwd)/providers.yml:/app/providers.yml \
  -v $(pwd)/secrets:/app/secrets \
  gcr.io/censys-io/censys-cloud-connector:latest
```

> More information about the `--daemon` flag is found
> [here](#additional-options).

---

### [Docker Compose](./docker-compose.yml)

This method assumes you have Docker and Docker Compose installed and running on
your server.

1. Run the Docker Compose file

```sh
docker-compose up -d
```

2. [Optional] Run your connector on a scheduled interval

Uncomment the line `# command: scan --daemon 4` in
[docker-compose.yml](./docker-compose.yml).

Details about the `--daemon` option can be found [here](#additional-options).

---

### [Kubernetes](./kubernetes/censys-cloud-connectors/README.md)

This method assumes you have Kubernetes installed and running on your server.

<!-- TODO: Add steps -->

---

### Confirm Results

Visit the [Seed Data Page][seed-data] and the [Storage Buckets Page][storage-bucket] to confirm that you're seeing seeds and storage buckets from your cloud provider(s).

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

### AWS Policy Actions

The following permissions are required to scan:

- `route53:ListHostedZones`,
- `elasticloadbalancing:DescribeLoadBalancers`,
- `route53domains:ListDomains`,
- `ec2:DescribeNetworkInterfaces`,
- `rds:DescribeDBInstances`,
- `route53:ListResourceRecordSets`,
- `ecs:ListContainerInstances`,
- `apigateway:GET`,
- `s3:GetBucketLocation`,
- `s3:ListBucket`,
- `s3:ListAllMyBuckets`,
- `ecs:ListClusters`

### Azure Roles

Ensure the account's Access control (IAM) role has the following permission to create a service principal with a Reader role:

- `Microsoft.Authorization/roleAssignments/write` over scope `/subscriptions/uuid`

The following permissions will be used with this service principal:

- `Microsoft.ContainerInstance/containerGroups/read`
- `Microsoft.Network/dnszones/read`
- `Microsoft.Network/publicIPAddresses/read`
- `Microsoft.Sql/servers/read`
- `Microsoft.Storage/storageAccounts/read`

If you see the following error message, check that you are logged into an account with the correct permissions:

```error
The client 'user@example.com' with object id 'uuid' does not have authorization to perform action 'Microsoft.Authorization/roleAssignments/write' over scope '/subscriptions/uuid' or the scope is invalid. If access was recently granted, please refresh your credentials.
```

### GCP Service Account Keys

If you encounter the following error while configuring your GCP Cloud Connector, a likely cause is that your service account has reached its maximum quota of keys.

```error
Failed to enable service account. ERROR: (gcloud.iam.service-accounts.keys.create) FAILED_PRECONDITION: Precondition check failed.
```

Go to <https://console.cloud.google.com/iam-admin/serviceaccounts> to manage your service account keys.

## Developer Documentation

All contributions (no matter how small) are always welcome. See
[Contributing to the Cloud Connector](https://github.com/censys/censys-cloud-connector/tree/main/.github/CONTRIBUTING.md) to change or
test the code or for information on the CI/CD pipeline.

## License

This software is licensed under [Apache License, Version 2.0][license].

- Copyright (C) 2022 Censys, Inc.

<!-- References -->

[license]: http://www.apache.org/licenses/LICENSE-2.0
[github]: https://github.com/censys/censys-cloud-connector
[python-install]: https://www.python.org/downloads/
[poetry-install]: https://python-poetry.org/docs/
[pyenv-install]: https://github.com/pyenv/pyenv#installation
[censys-asm-integrations]: https://app.censys.io/integrations
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
[azure-cli]: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
[gcloud-cli]: https://cloud.google.com/sdk/docs/install
[seed-data]: https://app.censys.io/seeds
[storage-bucket]: https://app.censys.io/storage-bucket
