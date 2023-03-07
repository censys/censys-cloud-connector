# Local Deployment

## Run the Connector

To run the connector, you can use the command line interface. The scan command
is:

```{prompt} bash
poetry run censys-cc scan
```

The {ref}`censys-cc scan <censys-cc>` command will enumerate the configured
cloud providers and scan the resources. The scan command will submit the public
cloud assets to Censys ASM as Seeds and Cloud Assets.

## Additional Options

You can set a scheduled interval for the connector to run on with the flag
`--daemon`. This option takes in a time interval in hours. If you do not
specify an interval, the default will be set to 1 hour.

```{prompt} bash
censys-cc scan --daemon         # Run every 1 hour
censys-cc scan --daemon 1.5     # Run every 1.5 hours
```
