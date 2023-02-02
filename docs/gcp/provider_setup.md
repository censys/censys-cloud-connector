# GCP Provider Setup

## Installation

Install [GCP's gcloud CLI][gcloud-cli].

## Authentication

Log in to GCP's CLI tool using the following command: `gcloud auth login`.

## Configuration

Use our {doc}`../cli` to step through the configuration process:

```{prompt} bash
censys-cc config --provider gcp
```

### Roles and Permissions

During the configuration, you will notice after you have selected the GCP account,
project, organization ID, and service account, the CLI will apply all required
roles to the service account upon your confirmation. For your reference,
these roles are listed below:

- [Security Reviewer (roles/iam.securityReviewer)][security-reviewer]
- [Folder Viewer (roles/resourcemanager.folderViewer)][folder-viewer]
- [Organization Viewer (roles/resourcemanager.organizationViewer)][organization-viewer]
- [Security Center Assets Discovery Runner (roles/securitycenter.assetsDiscoveryRunner)][securitycenter-assets-discovery-runner]
- [Security Center Assets Viewer (roles/securitycenter.assetsViewer)][securitycenter-assets-viewer]

```{admonition} Note
:class: censys
The linked documentation from GCP includes a list of permissions that come with
each role.
```

### Example

:::{asciinema} assets/gcp-setup.cast
:poster: "npt:00:31"
:::

<!-- References -->
[gcloud-cli]: https://cloud.google.com/sdk/docs/install
[security-reviewer]: https://cloud.google.com/iam/docs/understanding-roles#iam.securityReviewer
[folder-viewer]: https://cloud.google.com/iam/docs/understanding-roles#resourcemanager.folderViewer
[organization-viewer]: https://cloud.google.com/iam/docs/understanding-roles#resourcemanager.organizationViewer
[securitycenter-assets-discovery-runner]: https://cloud.google.com/iam/docs/understanding-roles#securitycenter.assetsDiscoveryRunner
[securitycenter-assets-viewer]: https://cloud.google.com/iam/docs/understanding-roles#securitycenter.assetsViewer
