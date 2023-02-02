# AWS Provider Setup

```{toctree}
---
maxdepth: 1
caption: AWS
---

stackset
templates
```

## Installation

[Install][aws-cli] the AWS CLI.

## Authentication

[Configure][aws-cli-configure] the AWS CLI.

### Configure Cloud Connector IAM

We recommend {doc}`deploying a StackSet<stackset>`, but
[alterative options](#alternative-aws-configuration-options) are available.

## Configuration

The Censys Cloud Connector {doc}`provider setup CLI <../cli>` will ask a series
of questions that have opt-in defaults.

```{prompt} bash
censys-cc config --provider aws
```

```{admonition} Note
:class: censys
Permissions required during provider setup are described [here](#provider-setup-permissions-overview).
```

### Example AWS Provider Setup: Basic Usage

:::{asciinema} assets/aws-single-account.cast
:poster: "npt:00:16"
:::

## Alternative AWS Configuration Options

Manually create an IAM role and attach the either the
{ref}`Least Privilege<aws/templates:least privilege>` policy or the
{ref}`Recommended<aws/templates:recommended>` set of policies.

## Supported Provider Configurations

The Censys Cloud Connector officially supports the following IAM configurations:

- [IAM User in Parent, Assume Role in Children](#iam-user-in-parent-assume-role-in-children)
- [IAM User in Parent, IAM Users in each children](#iam-user-in-parent-iam-users-in-each-children)
- [ECS Role in Parent, Assume Role in Children](#ecs-role-in-parent-assume-role-in-children)

### IAM User in Parent, Assume Role in Children

This is the recommended configuration if you are running the connector outside
of ECS.

```{literalinclude} ../../tests/data/aws/accounts_parent_key_child_role.yml
---
language: yaml
---
```

### IAM User in Parent, IAM Users in each children

```{literalinclude} ../../tests/data/aws/accounts_key.yml
---
language: yaml
---
```

### ECS Role in Parent, Assume Role in Children

This configuration can be used in conjunction with the
{doc}`AWS ECS <../terraform/aws_ecs_task>` deployment.

```{literalinclude} ../../tests/data/aws/ecs.yml
---
language: yaml
---
```

## Provider Setup Permissions Overview

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

### Find Accounts by StackSet (recommended)

Censys provides a CloudFormation
{ref}`StackSet template <aws/templates:stackset template>`
available to create the `CensysCloudConnectorRole`. It also serves as a way to
list your organization's account numbers with the CloudFormation [Stack Instance][aws-cloudformation-list-stack-instances]
API.

#### Example 1

:::{asciinema} assets/aws-stackset-setup.cast
:poster: "npt:00:46"
:::

### Find Accounts by Organizations

Provider setup will use the Organizations [List Accounts][aws-organizations-list-accounts]
feature to find a list of accounts. You will then have the option to choose which
accounts are saved into `providers.yml`.

#### Example 2

:::{asciinema} assets/aws-orglist-setup.cast
:poster: "npt:01:01"
:::

## Asset Deny List

In certain situations it is desirable not to have assets sent to Censys. This
can be accomplished by utilizing the cloud provider's tagging feature. At this
time, only AWS ENI and EC2 tags are supported.

Usage:

- AWS supports `ignore_tags` at the provider and account levels in
  {doc}`providers.yml <../providers_yml>`.
- Tags named `censys-cloud-connector-ignore` are ignored.

<!-- References -->
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
[aws-cli-configure]: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-prereqs.html
[aws-cloudformation-list-stack-instances]: https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ListStackInstances.html
[aws-organizations-list-accounts]: https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListAccounts.html
