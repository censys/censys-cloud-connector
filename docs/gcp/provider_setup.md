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
- [Cloud Asset Viewer (roles/cloudasset.viewer)][cloud-asset-viewer]

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
[cloud-asset-viewer]: https://cloud.google.com/iam/docs/understanding-roles#cloudasset.viewer
