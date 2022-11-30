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

- Installs dependencies for Azure, AWS, and GCP

  ```{prompt} bash
  make install-all
  ```

- Installs dependencies for Azure

  ```{prompt} bash
  make install-azure
  ```

- Installs dependencies for AWS

  ```{prompt} bash
  make install-aws
  ```

- Installs dependencies for GCP

  ```{prompt} bash
  make install-gcp
  ```

Copy .env.sample to .env

```{prompt} bash
cp .env.sample .env
```

## Environment Variables

The connector uses environment variables to configure the connector. The
{envvar}`CENSYS_API_KEY` environment variable is required to run the connector.

To learn more about the environment variables, see {doc}`env`.

## Configuration

```{note}
Before configuring the connector, make sure you are logged in to your cloud
provider's CLI tool. See our {doc}`providers` for more
information.
```

To configure the connector, you can use the command line interface. The base
command is {ref}`censys-cc`. The configuration command is:

```{prompt} bash
poetry run censys-cc config
```

The {ref}`censys-cc config <censys-cc>` command will guide you through the
configuration of supported cloud providers. This command will assist you in
generating {doc}`providers_yml`. This file can contain multiple provider
configurations.

**You have successfully configured your cloud connector if your
{doc}`providers_yml` is populated with your credentials.**

## Running the Connector

To run the connector, you can use the command line interface. The scan command
is:

```{prompt} bash
poetry run censys-cc scan
```

The {ref}`censys-cc scan <censys-cc>` command will enumerate the configured
cloud providers and scan the resources. The scan command will submit the public
cloud assets to Censys ASM as Seeds and Cloud Assets.

## Deploying the Connector

The connector can be deployed to a variety of environments. We have provided
several deployment methods. See {doc}`deployment_methods` for more information.

## Confirm Results

Visit the [Seed Data Page][seed-data] and the
[Storage Buckets Page][storage-bucket] to confirm that you're seeing seeds and
storage buckets from your cloud provider(s).

## Additional options

- You can specify one or more providers in the command line with the flag
`--provider`. The connector will only scan for assets from the specified
providers.

- You can set a scheduled interval for the connector to run on with the flag
`--daemon`. This option takes in a time interval in hours. If you do not
specify an interval, the default will be set to 1 hour.

  ```sh
  censys-cc scan --daemon       # Run every 1 hour
  censys-cc scan --daemon 1.5   # Run every 1.5 hours
  ```

<!-- References -->
[python-install]: https://www.python.org/downloads/
[poetry-install]: https://python-poetry.org/docs/
[pip-install]: https://pip.pypa.io/en/stable/installation/
[seed-data]: https://app.censys.io/seeds
[storage-bucket]: https://app.censys.io/storage-bucket
