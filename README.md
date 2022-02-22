# Cloud Connectors Unified

## Getting Started

### Prerequisites

- [Python 3.9+](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/docs/)

### Installation

```sh
poetry install  # Only core dependencies
poetry install -E azure  # Only Azure dependencies
poetry install -E gcp  # Only GCP dependencies
poetry install -E azure -E gcp  # All dependencies
```

## Commands

```sh
censys-cc config  # Configure Cloud Connectors
censys-cc scan  # Scan for assets
```
