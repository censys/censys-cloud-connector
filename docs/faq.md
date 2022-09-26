# FAQ

## My Python Version is Not Compatible

It is highly recommended that a Python version shim like
[pyenv][pyenv-install] is used.
Once installed, Poetry will make a virtualenv using the
correct version of Python automatically.

## AWS Policy Actions

The following permissions are required to scan:

- `route53:ListHostedZones`
- `elasticloadbalancing:DescribeLoadBalancers`
- `route53domains:ListDomains`
- `ec2:DescribeNetworkInterfaces`
- `rds:DescribeDBInstances`
- `route53:ListResourceRecordSets`
- `ecs:ListContainerInstances`
- `apigateway:GET`
- `s3:GetBucketLocation`
- `s3:ListBucket`
- `s3:ListAllMyBuckets`
- `ecs:ListClusters`

## Azure Roles

Ensure the account's Access control (IAM) role has the following permission to
create a service principal with a Reader role:

- `Microsoft.Authorization/roleAssignments/write` over scope `/subscriptions/uuid`

The following permissions will be used with this service principal:

- `Microsoft.ContainerInstance/containerGroups/read`
- `Microsoft.Network/dnszones/read`
- `Microsoft.Network/publicIPAddresses/read`
- `Microsoft.Sql/servers/read`
- `Microsoft.Storage/storageAccounts/read`

If you see the following error message, check that you are logged into an
account with the correct permissions:

<!-- markdownlint-disable MD013 -->
```{code-block}
The client 'user@example.com' with object id 'uuid' does not have authorization to perform action 'Microsoft.Authorization/roleAssignments/write' over scope '/subscriptions/uuid' or the scope is invalid. If access was recently granted, please refresh your credentials.
```
<!-- markdownlint-enable MD013 -->

## GCP Service Account Keys

If you encounter the following error while configuring your GCP Cloud Connector,
a likely cause is that your service account has reached its maximum quota of keys.

<!-- markdownlint-disable MD013 -->
```{code-block}
Failed to enable service account. ERROR: (gcloud.iam.service-accounts.keys.create) FAILED_PRECONDITION: Precondition check failed.
```
<!-- markdownlint-enable MD013 -->

Go to <https://console.cloud.google.com/iam-admin/serviceaccounts> to manage
your service account keys.

<!-- References -->
[pyenv-install]: https://github.com/pyenv/pyenv#installation
