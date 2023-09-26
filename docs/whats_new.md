# What's new?

## v3.2.0

### Changelog

- ([Details](#details-about-gcp-api-migration)) Migration from Google’s
soon-to-be-deprecated Security Command Center Asset API to Google’s Cloud
Asset Inventory API. ([#26][pr-26])

- Remove GCP stale seeds on each scan ([#26][pr-26])

- Reset AWS STS creds between scanning for seeds and cloud assets. This will
remedy the recursion errors that some customers have been seeing in their
healthcheck logs. ([#41][pr-41])

- Combine seeds submission for resource types with multiple versions (ex: AWS
API Gateway v1 and API Gateway v2) ([#40][pr-40])

- CI updates ([#38][pr-38])

- Update dependencies ([#39][pr-39])

- ([Details](#details-about-azure-stale-seeds-workaround)) Optional
environmental variable AZURE_REFRESH_ALL_REGIONS available to scan all Azure
regions and clear out lingering stale seeds ([#34][pr-34])

- Updates to documentation ([#42][pr-42])

### Details about GCP API migration

In response to Google’s deprecation of the Security Command Center (SCC) Asset
API, the cloud connector will now use the Cloud Asset Inventory (CAI) as its
source of truth.

Currently, we use GCP's Security Command Center (SCC) API to list assets by
asset type within an organization. [SCC is deprecating functionality related
to assets on June 26, 2024][scc-deprecation]. Existing users of the SCC Asset
API can continue using it until then, but new customers can no longer enable
the API.

The Cloud Connector will migrate to using GCP's [Cloud Asset Inventory (CAI)
API][cai-api] as its source of truth. All customers will need to enable this
API and upgrade their cloud connector instances to v3.2.0 by June 26, 2024.

#### Changes

##### API usage

[SCC List Assets request][scc-list-assets] --> [CAI Search All Resources
request][cai-search-assets]

##### Permissions

Service accounts will need the [Cloud Asset Viewer
(roles/cloudasset.viewer)][cloud-asset-viewer] role.

Service accounts no longer need the roles [Security Command Center Assets
Discovery Runner (securitycenter.assetsDiscoveryRunner)][scc-perm-1] and
[Security Command Center Assets Viewer (securitycenter.assetsViewer)][scc-perm-2].

#### What do customers need to do?

##### Recommended

Run through the configuration CLI (`censys-cc config --provider gcp`) and
select the same organization, project, and service account that you've been
using. This will enable the CAI API and apply the new permissions to the
service account.

##### Manual

Enable the CAI API:

gcloud CLI: ```gcloud services enable cloudasset.googleapis.com --project {PROJECT_ID}```

Apply new permissions to service account:
<!-- markdownlint-disable MD013 -->
gcloud CLI: ```gcloud organizations add-iam-policy-binding {ORGANIZATION ID} --member 'serviceAccount:{SERVICE ACCOUNT EMAIL}' --role 'roles/cloudasset.viewer' --condition=None --quiet```
<!-- markdownlint-enable MD013 -->

### Details about Azure stale seeds workaround

The Azure cloud connector currently submits assets that it finds during each
scan to the Censys seeds API. When set to true, the environmental variable
`AZURE_REFRESH_ALL_REGIONS` will submit an empty list to the Censys seeds
API for every possible label (subscription+region) where assets were not found.
This may cause the scan to run more slowly, so it is not enabled by default.
Users can opt in on a per-connector basis by setting the environmental variable
to true in the connector’s `.env`` file.

<!-- References -->
[pr-26]: https://github.com/censys/censys-cloud-connector/pull/26
[pr-34]: https://github.com/censys/censys-cloud-connector/pull/34
[pr-38]: https://github.com/censys/censys-cloud-connector/pull/38
[pr-39]: https://github.com/censys/censys-cloud-connector/pull/39
[pr-40]: https://github.com/censys/censys-cloud-connector/pull/40
[pr-41]: https://github.com/censys/censys-cloud-connector/pull/41
[pr-42]: https://github.com/censys/censys-cloud-connector/pull/42
[scc-deprecation]: https://cloud.google.com/security-command-center/docs/how-to-api-list-assets
[cai-api]: https://cloud.google.com/asset-inventory/docs/overview
[scc-list-assets]: https://cloud.google.com/security-command-center/docs/how-to-api-list-assets#list_all_assets
[cai-search-assets]: https://cloud.google.com/asset-inventory/docs/searching-resources#search_resources
[cloud-asset-viewer]: https://cloud.google.com/iam/docs/understanding-roles#cloudasset.viewer
[scc-perm-1]: https://cloud.google.com/iam/docs/understanding-roles#securitycenter.assetsDiscoveryRunner
[scc-perm-2]: https://cloud.google.com/iam/docs/understanding-roles#securitycenter.assetsViewer
