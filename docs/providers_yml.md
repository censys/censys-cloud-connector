# Provider Configuration

To configure the connector, you can use the {doc}`cli`. The configuration
command is:

```{prompt} bash
poetry run censys-cc config
```

The {ref}`censys-cc config <censys-cc>` command will guide you through the
configuration of supported cloud providers. This command will assist you in
generating your [`providers.yml`](#sample-providersyml-file) file. This file
can contain multiple provider configurations.

:::{admonition} Note
:class: censys
Before configuring the connector, make sure you are logged in to your cloud
provider's CLI tool. See our [Provider Specific Setup](#provider-specific-setup)
for more information.
:::

## Provider Specific Setup

```{toctree}
---
maxdepth: 1
---

aws/provider_setup
azure/provider_setup
gcp/provider_setup

```

## Verify Configuration (Optional)

At this point, you should be able to run the cloud connector. If you would like
to run the connector once before moving onto deployment, you can run the
following command:

```{caution}
This is a real-time scan of your cloud environment and may take a long time if
you have a large cloud environment. You may adjust the environment variable
`DRY_RUN` to `true` to opt out of submitting scan results to Censys.
```

```{prompt} bash
poetry run censys-cc scan
```

## Sample `providers.yml` File

The `providers.yml` file contains the configuration for all cloud providers.

The file is a YAML file and is structured as follows:

```{literalinclude} ../providers.yml.sample
---
language: yaml
---
```
