# Templates

## StackSet Template

{download}`download <../../templates/aws/stackset_role_deploy.json>`

```{literalinclude} ../../templates/aws/stackset_role_deploy.json
---
language: json
---
```

## IAM Policies

```{admonition} Note
:class: censys
As a security best-practice, the connector also supports creation of [temporary credentials][aws-sts-creds]
via Secure Token Service (STS).
```

### Recommended

In order to ease the burden of maintaining an evolving list of policies, it's
possible to run the Censys Cloud Connector using a role with the following
policies:

1. AWS [arn:aws:iam::aws:policy/SecurityAudit][aws-policy-security-audit]

2. `censysCloudConnectorPolicy` (below)

{download}`download <../../templates/aws/iam_recommended_policy.json>`

```{literalinclude} ../../templates/aws/iam_recommended_policy.json
---
language: json
---
```

### Least Privilege

Use this policy to follow the AWS best-practice of [least-privilege][aws-least-privilege].

{download}`download <../../templates/aws/iam_least_privilege_policy.json>`

```{literalinclude} ../../templates/aws/iam_least_privilege_policy.json
---
language: json
---
```

<!-- References -->
[aws-least-privilege]: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege
[aws-policy-security-audit]: https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/SecurityAudit
