# Azure Provider Setup

## Installation

Install the [Azure CLI][azure-cli].

## Authentication

Log in to Azure's CLI tool using the following command: [`az login`][azure-cli-login].

## Configuration

Use our {doc}`../cli` to step through the configuration process:

```{prompt} bash
censys-cc config --provider azure
```

```{admonition} Note
:class: censys
Running the provider setup will overwrite any existing Service Principals with
the name `Censys Cloud Connector`.
```

### Roles and Permissions

Azure uses [role-based access control][azure-rbac]. Ensure that your account's
role has the following permission to create a service principal with a
Reader role:

- `Microsoft.Authorization/roleAssignments/write` over scope `/subscriptions/uuid`

The following permissions will be used by this service principal:

- [`Microsoft.ContainerInstance/containerGroups/read`][container-groups]
- [`Microsoft.Network/dnszones/read`][dns-zones]
- [`Microsoft.Network/publicIPAddresses/read`][public-ip]
- [`Microsoft.Sql/servers/read`][sql-servers]
- [`Microsoft.Storage/storageAccounts/read`][storage-accounts]

### Example

:::{asciinema} assets/azure-setup.cast
:poster: "npt:00:13"
:::

<!-- References -->
[azure-cli]: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
[azure-cli-login]: https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli
[azure-rbac]: https://learn.microsoft.com/en-us/azure/role-based-access-control/check-access
[container-groups]: https://learn.microsoft.com/en-us/azure/templates/microsoft.containerinstance/containergroups?pivots=deployment-language-terraform
[dns-zones]: https://learn.microsoft.com/en-us/azure/templates/microsoft.network/dnszones?pivots=deployment-language-terraform
[public-ip]: https://learn.microsoft.com/en-us/azure/templates/microsoft.network/publicipaddresses?pivots=deployment-language-terraform
[sql-servers]: https://learn.microsoft.com/en-us/azure/templates/microsoft.sql/servers?pivots=deployment-language-terraform
[storage-accounts]: https://learn.microsoft.com/en-us/azure/templates/microsoft.storage/storageaccounts?pivots=deployment-language-terraform
