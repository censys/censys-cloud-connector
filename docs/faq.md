# FAQ

## General

### My Python Version is Not Compatible

It is highly recommended that a Python version shim like
[pyenv][pyenv-install] is used.
Once installed, Poetry will make a virtualenv using the
correct version of Python automatically.

## AWS

### AWS Policy Actions

The following permissions are required to scan:

```{literalinclude} ../templates/aws/iam_least_privilege_policy.json
---
language: json
---
```

### Can I use a Session Role Name?

Yes, this can be set during the provider setup and will be defined in `providers.yml`.

### Do you support Named Profiles?

[Yes][aws-cli-profile].

### Can I use SSO?

AWS CLI supports [Single Sign-On][aws-cli-sso] via IAM Identity Center.
You can use the `aws sso login` command to authenticate before running
provider setup.

## Azure

### Azure Roles

Read about Azure roles and permissions
{ref}`here <azure/provider_setup:roles and permissions>`.

If you see the following error message, check that you are logged into an
account with the correct permissions:

<!-- markdownlint-disable MD013 -->
```{code-block}
The client 'user@example.com' with object id 'uuid' does not have authorization to perform action 'Microsoft.Authorization/roleAssignments/write' over scope '/subscriptions/uuid' or the scope is invalid. If access was recently granted, please refresh your credentials.
```
<!-- markdownlint-enable MD013 -->

### Why does the Cloud Connector say that my Azure subscription does not exist?

There are two cases where the Cloud Connector might report that your Azure
subscription does not exist.

#### Case 1: Your providers.yaml file includes a non-existent subscription ID

If you encounter this error:

<!-- markdownlint-disable MD013 -->
```{code-block}
Failed to get Azure <RESOURCE_TYPE>: (SubscriptionNotFound) The subscription <SUBSCRIPTION_ID> could not be found.
```
<!-- markdownlint-enable MD013 -->

Check to see if this subscription ID exists within the Azure tenant you've
defined in your providers.yaml file.

#### Case 2: Your Azure Subscription is empty or has unregistered resource providers

If you encounter an error like this:

<!-- markdownlint-disable MD013 -->
```{code-block}
Error scanning Microsoft.Network/dnszones: (BadRequest) The specified subscription <SUBSCRIPTION_ID> does not exist
```
<!-- markdownlint-enable MD013 -->

Check in your Azure portal if this subscription is empty. Azure reports this
error if the "Resource Provider" we are trying to access is not registered
for this subscription and there are no resources of this type in this
subscription. You can check this by going to the subscription in question in
your Azure portal, and clicking on "Resource Providers" in the left-hand menu.
If the resource provider you are trying to access is not listed, you will need
to register it.

For example, the error shown above is for the `Microsoft.Network/dnszones`
resource provider. To register this resource provider, you would click on
"Microsoft.Network" in the list of resource providers, and then click the
"Register" button at the top of the page.

This is a non-fatal error, so it will not prevent the Cloud Connector from
scanning the rest of the resource types in this subscription, or the rest of
the subscriptions in your providers.yaml file.

## GCP

### GCP Service Account Keys

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
[aws-cli-profile]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html
[aws-cli-sso]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html
