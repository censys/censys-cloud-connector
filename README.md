# Censys Unified Cloud Connector

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
interface. After you have configured the connector, you can deploy it to your
environment. In the following sections, we will provide a brief overview of
how to deploy the connector to your environment.

## Deployment Methods

- [Local Deployment](#local-deployment)
- [Docker Standalone](#docker-standalone)
- [Docker Compose](#docker-compose)
- [Kubernetes](#kubernetes)
- [Helm](#helm)
<!-- Coming Soon
- [Terraform](#terraform)
- [Ansible](#ansible) -->

### Local Installation

#### Prerequisites

- [Python 3.9+](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/docs/)

#### Installation

```sh
# Clone the repository
git clone git@gitlab.com:censys/integrations/cloud-connectors-unified.git
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
censys-cc config  # Configure supported providers
censys-cc scan  # Scan for assets
```

- The `censys-cc config` command will guide you through the configuration of
  supported cloud providers. This command will assist you in generating a
  `providers.yml` file. This file can contain multiple provider configurations.
- The `censys-cc scan` command runs the connector.

#### Environment Variables

The following environment variables are available for use in the connector:

- `CENSYS_API_KEY` - Your Censys ASM API key found in the
  [ASM Integrations Page](https://app.censys.io/integrations).
- `PROVIDERS_CONFIG_FILE` - The path to the `providers.yml` file.
- `LOGGING_LEVEL` - The logging level. Valid values are `DEBUG`, `INFO`,
  `WARN`, `ERROR`, and `CRITICAL`.
- `DRY_RUN` - If set to `true`, the connector will not write any data to the
- ASM platform. This is useful for testing.

### Docker Standalone

This method assumes you have Docker installed and running on your server.

1. Pull the Docker image

```sh
docker pull gcr.io/censys-io/cloud-connector:latest
```

- If your environment does not allow you to pull the Docker image, you can
  build it from the Dockerfile using the following command. You can then
  push the image to a Docker registry.

  ```sh
  docker build -t gcr.io/censys-io/cloud-connector:latest .
  ```

2. Configure the Docker image <!-- markdownlint-disable -->

- If you have not already done so, create the providers.yml file

  > This is due to the way docker handles volumes.

  ```sh
  touch providers.yml
  ```

```sh
docker run --rm -it \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -e "PROVIDERS_CONFIG_FILE=/app/config/providers.yml" \
  -v $(pwd)/providers.yml:/app/config/providers.yml \
  -v $(pwd)/secrets:/app/secrets \
  gcr.io/censys-io/cloud-connector:latest \
  config
```

3. Run the Docker container <!-- markdownlint-disable -->

The following command will run the Docker container. You can specify the
environment variables you want to pass to the container using the `-e` flag.
The container also requires the `providers.yml` file. The `-v` flag will
mount the `providers.yml` file as a volume. If your `providers.yml` references
additional secret files, you can mount it as a volume as well. We also include
the `--rm` flag to ensure the container is removed after it has finished.

```sh
# Mount the providers.yml file as a volume
docker run --rm \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -v $(pwd)/providers.yml:/app/providers.yml \
  gcr.io/censys-io/cloud-connector:latest

# Mount the providers.yml and secrets files as volumes
docker run --rm \
  -e "CENSYS_API_KEY=$CENSYS_API_KEY" \
  -v $(pwd)/providers.yml:/app/providers.yml \
  -v $(pwd)/secrets:/app/secrets \
  gcr.io/censys-io/cloud-connector:latest
```

It is important to note that the container runs once by default.

<!-- TODO: Add cron instructions -->

### Docker Compose

This method assumes you have Docker and Docker Compose installed and running on
your server.

<!-- TODO: Add steps -->

### Kubernetes

<!-- TODO: Add steps -->

### Helm

This method assumes you have Helm installed locally.

<!-- TODO: Add steps -->

## Development

```sh
poetry run flake8 .  # Run linter
poetry run black .  # Run formatter
poetry run isort .  # Run import formatter
poetry run mypy -p censys.cloud_connectors  # Run type checker
pre-commit run --all-files  # Run pre-commit hooks (lint, type check, etc.)
poetry run pytest  # Run tests
poetry run pytest --cov --cov-report html  # Run tests with coverage report
```

## Committing

This repository currently uses the `rebase` workflow for Merge Requests. This means
that merge messages are _not_ created when requests are merged.

Every commit in the merge request **must** be treated as a stand-alone, autonomous
change. If this is not the case, consider using the squash feature before
merging.

### Commit Messages

Search is now using
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
to structure its commit messages, in the event we want to automatically
generate changelogs in the future.

Commit messages should always be written as if to complete the follow sentence:

> If applied, this commit will... < Insert Commit Message Here >

#### Type

- `fix`: A bug fix.
- `feat`: A new feature or component.
- `improve`: A code code that is neither a new feature nor a bug fix but improves
  functionality.
- `refactor`: A code change that is niether a new feature nor
  a bug fix but does not change the current functionality of the code.
- `chore`: A repeatable action such as static code generation.
- `docs`: Changes to documentation.
- `style`: Changes that do not change the meaning of the code such as black or isort.
- `test`: Changes to tests.

> type: \<commit message>

Finally, there is a `build` type which has its own set of scopes. See below.

#### Scope

The scope should be the name of an area of Search. While this is certainly not
an exhaustive list, please consider using an existing scope before adding a
new one.

Scopes are not required, but they help keep commits succinct and autonomous.

- `cc`: Changes to the Cloud Connectors.
  - `cc-azure`: Changes to the Azure Cloud Connectors.
  - `cc-gcp`: Changes to the GCP Cloud Connectors.
- `cli`: Changes to the CLI.
  - `cli-setup`: Changes to the CLI setup.
  - `cli-scan`: Changes to the CLI scan.
- `docs`: Changes to the documentation.

> type(scope): \<commit message>

#### Build Type and Scopes

The `build` type is used to represent changes to the build system or repository itself.
The following scopes are recommended for use with the build commit type:

- `ci`
- `chart`
- `container`
- `deps`

### VSCode Config

Please note that there is a sample vscode `settings.json` and `extensions.json`
files in the `.vscode` directory.

Features inlcuded in the extensions:

- Use pytest as a test runner
- `.toml`, `.yaml`, `.env` file extension support
- View all todos
- Automatically generate docsstrings
- Spell check
- Docker and Kubernetes support

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
[pyenv](https://github.com/pyenv/pyenv) is used.
Once installed, Poetry will make a virtualenv using the
correct version of Python automatically.

### Rebasing merge conflicts when there was a new package added to poetry

Incase of `poetry.lock` merge conflicts

1. Accept all incoming changes (to maintain toml validity)

2. Rewrite the lockfile from `pyproject.toml`

```sh
poetry lock --no-update
```
