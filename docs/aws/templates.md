# Templates

## IAM

To dynamically find accounts by StackSet, `cloudformation:ListStackInstances`
is required.

### Provider Setup Policy

This policy contains roles that might be used during provider setup.

{download}`download <../../templates/aws/iam_provider_setup_policy.json>`

```{literalinclude} ../../templates/aws/iam_provider_setup_policy.json
---
language: json
---
```

### Least Privilege Policy

Use this policy to follow the AWS best-practice of [least-privilege][aws-least-privilege].

{download}`download <../../templates/aws/iam_least_privilege_policy.json>`

```{literalinclude} ../../templates/aws/iam_least_privilege_policy.json
---
language: json
---
```

### Recommended Policy

In order to ease the burden of maintaining an evolving list of policies, it's
possible to run the Censys Cloud Connector using a role with the following
policies:

1. AWS [arn:aws:iam::aws:policy/SecurityAudit][aws-policy-security-audit]

2. Additional policy

{download}`download <../../templates/aws/iam_recommended_policy.json>`

```{literalinclude} ../../templates/aws/iam_recommended_policy.json
---
language: json
---
```

## StackSet Template

{download}`download <../../templates/aws/stackset_role_deploy.json>`

```{literalinclude} ../../templates/aws/stackset_role_deploy.json
---
language: json
---
```

<!-- References -->
[aws-least-privilege]: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege
[aws-policy-security-audit]: https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/SecurityAudit
