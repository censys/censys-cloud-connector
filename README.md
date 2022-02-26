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
```

### Commands

```sh
censys-cc config  # Configure Cloud Connectors
censys-cc scan  # Scan for assets
```

## Development

```sh
poetry run pytest  # Run tests
poetry run flake8 .  # Run linter
poetry run black .  # Run formatter
poetry run isort .  # Run import formatter
poetry run mypy .  # Run type checker
pre-commit run --all-files  # Run pre-commit hooks (lint, type check, etc.)
```
