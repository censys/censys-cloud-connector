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
