# AWS Provider Setup

## Prerequisites

- Install the [AWS CLI][aws-cli]
- [Configure][aws-cli-configure] the CLI
- Define a named [profile][aws-cli-profile]

Note: AWS CLI supports [Single Sign-On][aws-cli-sso] via IAM Identity Center.
You can use the `aws sso login` command to authenticate before running
provider setup.

## Permissions Overview

The permissions used are dependant on which setup options you use.

<!-- markdownlint-disable MD013 -->
| Service | Action  | Reason |
| :--- | :--- | :--- |
| STS | `GetCallerIdentity` | Used to find the primary account number |
| Organizations | `ListAccounts` | Allows finding accounts within an organization |
| CloudFormation | `ListStackInstances` | Allows finding accounts using a specific StackSet instance |
<!-- markdownlint-enable MD013 -->

## Setup Overview

The Censys Cloud Connector provider setup will ask a series of questions that
have opt-in defaults.

<!-- markdownlint-disable MD013 -->
- Select a credential profile allows you to choose which [named profile][aws-cli-profile] to use during provider setup.
  - You can optionally save the profile's credentials to `providers.yml`
- Define a role name to use STS [Assume Role][aws-sts-assume-role]. This enables running the connector without defining an access or secret key.
  - When using a role, AWS recommends using a [Session Role Name][aws-boto3-sts]. Typically, you pass the name or identifier that is associated with the user who is using your application. That way, the temporary security credentials that your application will use are associated with that user.
- If your organization has multiple accounts, provider setup will give an option to find and load these accounts into `providers.yml`.  The find accounts feature has two ways to look up accounts:
  - Find accounts with a CloudFormation StackSet Instance
  - Find accounts using Organization List Accounts
<!-- markdownlint-enable MD013 -->

## Find Accounts

### Find Accounts by Organizations

Provider setup will use the Organizations [List Accounts][aws-organizations-list-accounts]
feature to find a list of accounts. You will then have the option to choose which
accounts are saved into `providers.yml`.

### Find Accounts by StackSet Instance

Censys has a CloudFormation [StackSet Template](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=stack_name&templateURL=https://censys-cloud-connector.s3.us-east-2.amazonaws.com/CensysRoleDeploy.json)
available to create the `CensysCloudConnectorRole`. It also serves as a way to
list your organization's account numbers with the CloudFormation [Stack Instance][aws-cloudformation-list-stack-instances]
API.
[![StackSet Template](https://d2908q01vomqb2.cloudfront.net/b3f0c7f6bb763af1be91d9e74eabfeb199dc1f1f/2022/06/09/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=stack_name&templateURL=https://censys-cloud-connector.s3.us-east-2.amazonaws.com/CensysRoleDeploy.json)

### Account Roles

If you are utilizing multiple accounts in `providers.yml`, it's possible to
configure different roles per account.

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

<!-- References -->
[aws-boto3-sts]: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
[aws-cli-configure]: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html
[aws-cli-profile]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html
[aws-cli-sso]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html
[aws-sts-assume-role]: https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html
[aws-organizations-list-accounts]: https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListAccounts.html
[aws-cloudformation-list-stack-instances]: https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ListStackInstances.html
