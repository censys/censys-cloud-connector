# AWS Provider Setup

```{toctree}
---
maxdepth: 1
caption: AWS
---

stackset
templates
```

## Prerequisites

- [Install][aws-cli] the AWS CLI
- [Configure][aws-cli-configure] the AWS CLI
- [Configure](#configure-cloud-connector-iam) Cloud Connector IAM
- Optional: [Define][aws-cli-profile] a named profile

Note: AWS CLI supports [Single Sign-On][aws-cli-sso] via IAM Identity Center.
You can use the `aws sso login` command to authenticate before running
provider setup.

## Overview

The Censys Cloud Connector provider setup will ask a series of questions that
have opt-in defaults.

- Select a credential profile allows you to choose which
  [named profile][aws-cli-profile] to use during provider setup.
  - You can optionally save the profile's credentials to `providers.yml`
- Define a role name to use STS [Assume Role][aws-sts-assume-role]. This enables
  running the connector without defining an access or secret key.
  - When using a role, AWS recommends using a [Session Role Name][aws-boto3-sts].
    Typically, you pass the name or identifier that is associated with the user
    who is using your application. That way, the temporary security credentials
    that your application will use are associated with that user.
- If your organization has multiple accounts, provider setup will give an option
  to find and load these accounts into `providers.yml`.  The find accounts
  feature has two ways to look up accounts:
  - Find accounts with a CloudFormation StackSet Instance
  - Find accounts using Organization List Accounts

## Permissions Overview

The permissions used are dependant on options chosen during setup.

<!-- markdownlint-disable MD013 -->
| Service | Action  | Reason |
| :--- | :--- | :--- |
| STS | `GetCallerIdentity` | Used to find the primary account number |
| Organizations | `ListAccounts` | Allows finding accounts within an organization |
| CloudFormation | `ListStackInstances` | Allows finding accounts using a specific StackSet instance |
<!-- markdownlint-enable MD013 -->

## Find Accounts Feature

Add assets from all of your AWS accounts for the most up-to-date view of your
cloud attack surface.

### Find Accounts by Organizations

Provider setup will use the Organizations [List Accounts][aws-organizations-list-accounts]
feature to find a list of accounts. You will then have the option to choose which
accounts are saved into `providers.yml`.

### Find Accounts by StackSet

Censys provides a CloudFormation
{ref}`StackSet template <aws/templates:stackset template>`
available to create the `CensysCloudConnectorRole`. It also serves as a way to
list your organization's account numbers with the CloudFormation [Stack Instance][aws-cloudformation-list-stack-instances]
API.

### Account Specific Roles

If you are utilizing multiple accounts in `providers.yml`, it's possible to
configure roles that are unique to each account.

```yaml
- provider: aws
  account_number: 111 # <- primary account
  role_name: SharedRole
  accounts:
  - account_number: 222
  - account_number: 333
    role_name: Role333
  - account_number: 444
    role_name: Role444
```

In this example, account 222 will inherit the role `SharedRole`. Account 333
will overwrite the parent role with `Role333`.

## Configure Cloud Connector IAM

The Censys Cloud Connector has a set of
{ref}`minimum required permissions <aws/templates:least privilege policy>`.
These permissions can be applied through standard IAM configuration. As a security
best-practice, the connector also supports creation of [temporary credentials][aws-sts-creds]
via Secure Token Service (STS).

Censys also maintains a CloudFormation
{ref}`StackSet template <aws/templates:stackset template>`
that will deploy a `CensysCloudConnectorRole` role to all of your AWS accounts.
The StackSet can also be used to list all of your accounts.

### StackSet Deployment

See {doc}`StackSet Deployment <stackset>` for a walk-through of how to install
the Censys Cloud Connector StackSet in your account.

## Asset Deny List

In certain situations it is desirable not to have assets sent to Censys. This
can be accomplished by utilizing the cloud provider's tagging feature. At this
time, only AWS ENI and EC2 tags are supported.

Usage:

- AWS supports `ignore_tags` at the provider and account levels in
  {doc}`providers.yml <../providers_yml>`.
- Tags named `censys-cloud-connector-ignore` are ignored.

<!-- References -->
[aws-boto3-sts]: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
[aws-cli-configure]: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-prereqs.html
[aws-cli-profile]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html
[aws-cli-sso]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html
[aws-cloudformation-list-stack-instances]: https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ListStackInstances.html
[aws-organizations-list-accounts]: https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListAccounts.html
[aws-sts-assume-role]: https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html
[aws-sts-creds]: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html
