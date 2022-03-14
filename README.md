# Cloud Connectors Unified

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue?logo=python)](https://www.python.org/downloads/)

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

```sh
poetry run flake8 .  # Run linter
poetry run black .  # Run formatter
poetry run isort .  # Run import formatter
poetry run mypy .  # Run type checker
pre-commit run --all-files  # Run pre-commit hooks (lint, type check, etc.)
```

### Testing

```sh
# Run tests
poetry run pytest
# With coverage report
poetry run pytest --cov-report html
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


### GCP Config

<!-- TODO: if this is your first time using Censys cloud connectors, follow these directions. Otherwise, skip to... -->

Initial gcloud authentication:
[Install the gcloud SDK] (https://cloud.google.com/sdk/docs/downloads-interactive)
<!-- Is this necessary? -->
<!-- - Install kubectl
    ```sh
    gcloud components install kubectl
    ``` -->

Authenticate your gcloud client
To activate your user via browser-based SSO, run
```sh
$ gcloud auth login

You are now logged in as [your@email.com].
Your current project is [PROJECT-ID].  You can change this setting by running:
  $ gcloud config set project PROJECT_ID
```
Set your _PROJECT-ID_ to your preferred project.


```sh
$ censys-cc config
? Select a provider: Gcp
? Select a method to configure your credentials: Generate with CLI
i Before you begin you\'ll need to have identified the following:
  - The Google Cloud organization administrator account which will execute scripts that configure
the Censys Cloud Connector.
  - The project that will be used to run the Censys Cloud Connector. Please note that the cloud
connector will be scoped to the organization.
? Do you want to get the project and organization IDs from the CLI? Yes

```