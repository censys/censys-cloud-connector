# Setup Azure Cloud Connector

There are two options for setup:

1. [Azure CLI](#azure-cli)
2. [Azure Portal](#azure-portal)

## Azure CLI

### Prerequisites

- The [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) must be installed. You must be signed in with `az login` before proceeding.
- This process uses `jq` to parse the JSON output from the Azure CLI. You must have `jq` installed.

### Setup

1. List subscriptions

```sh
az account list --output table
```

2. Create a service principal for the subscriptions you want to connect to

```sh
az ad sp create-for-rbac --name "Censys Cloud Connector" --role Reader --scopes "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxcxxxxxxx" | tee azure-sp.json
```

## Azure Portal

<!-- TODO: Write docs with pictures for Azure -->