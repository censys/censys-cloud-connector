# Getting Started

It is important to note that this connector is a Python package. This allows
you to run the connector from the command line as well as enables you to run
the connector in as many different environments as you wish. We have provided
a variety of deployment types and configuration options. We recommend that you
install the package locally to take advantage of the configuration command line
interface ({ref}`censys-cc`). After you have configured the
connector, you can deploy it to your environment.

## Prerequisites

- [Python 3.9+][python-install]
- [Pip][pip-install]
- [Poetry][poetry-install]

```{admonition} Note
:class: censys
There may be additional requirements depending on the deployment method
```

## Installation

Clone the repo

```{prompt} bash
git clone https://github.com/censys/censys-cloud-connector.git
cd censys-cloud-connector
```

Ensure you have poetry installed (may require restarting shell)

```{prompt} bash
pip install --upgrade poetry
```

Start a shell and activate the virtual environment
(this is optional if you'd like to install dependencies globally)

```{prompt} bash
poetry shell
```

Install the dependencies
(a Makefile is provided for convenience in installation)

  ```{prompt} bash
  make install-all     # Install dependencies for all providers
  make install-azure   # Azure only
  make install-aws     # AWS only
  make install-gcp     # GCP only
  ```

Copy .env.sample to .env

```{prompt} bash
cp .env.sample .env
```

## Environment Variables

The connector uses environment variables to configure the connector. The
{envvar}`CENSYS_API_KEY` environment variable is required to run the connector.

The following environment variables are available for use in the connector:

```{envvar} CENSYS_API_KEY

Your Censys ASM API key found in the
[ASM Integrations Page](https://app.censys.io/integrations). (**Required**)
```

```{envvar} PROVIDERS_CONFIG_FILE

The path to {doc}`providers_yml`.

Default: `./providers.yml`
```

```{envvar} SECRETS_DIR

The path to the directory containing the secrets.

Default: `./secrets`
```

```{envvar} LOGGING_LEVEL

The logging level. Valid values are `DEBUG`, `INFO`, `WARN`, `ERROR`, and `CRITICAL`.

Default: `INFO`
```

```{envvar} DRY_RUN

If set to `true`, the connector will not write any data to the ASM platform.

Default: `false`
```

```{envvar} HEALTHCHECK_ENABLED

If set to `false`, the connector will not report its health to the ASM platform.

Default: `true`
```

```{envvar} AZURE_REFRESH_ALL_REGIONS

Azure-specific environmental variable. If set to `true`, the connector will
clear stale seeds from regions no longer containing assets. This may take
longer to run, but will ensure that the connector is not submitting stale seeds.
If set to `false`, the connector will submit seeds that are found as normal.

Default: `false`
```

### Sample `.env` File

`.env.sample` is a sample file that contains the above environment variables.
Please use this file as a template to create your own `.env` file.

```{literalinclude} ../.env.sample
---
language: bash
---
```

<!-- References -->
[python-install]: https://www.python.org/downloads/
[poetry-install]: https://python-poetry.org/docs/
[pip-install]: https://pip.pypa.io/en/stable/installation/
