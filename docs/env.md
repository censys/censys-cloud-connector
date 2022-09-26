# Environment Variables

The following environment variables are available for use in the connector:

```{envvar} CENSYS_API_KEY

Your Censys ASM API key found in the
[ASM Integrations Page](https://app.censys.io/integrations). (**Required**)
```

```{envvar} PROVIDERS_CONFIG_FILE

The path to the {doc}`providers_yml` file.

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

## Sample .env File

`.env.sample` is a sample file that contains the above environment variables.
Please use this file as a template to create your own `.env` file.

```{literalinclude} ../.env.sample
---
language: bash
---
```
