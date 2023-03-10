# Kubernetes Deployment Method

This guide describes how to deploy the Censys Cloud Connector using Kubernetes.

## Prerequisites

The following prerequisites are required to deploy using Kubernetes:

- [A Kubernetes cluster](https://kubernetes.io/docs/setup/)
- [Helm](https://helm.sh/docs/intro/install/)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)
<!-- markdownlint-disable MD013 -->
- A valid [`providers.yml`](http://censys-cloud-connector.readthedocs.io/en/latest/providers_yml.html) file

## Getting Started

> **Note**
>
> The following steps assume that you have already cloned the Censys Cloud
> Connector repository and are in the root directory.

<!-- markdownlint-disable MD013 MD029 -->
1. If you haven't already, create a namespace for the Censys Cloud Connector

```{prompt} bash
kubectl create namespace censys-cloud-connectors
```

Please note that the the above namespace is used in the following steps. If you
choose to use a different namespace, please update the commands accordingly.

2. Set the current namespace to the Censys Cloud Connector namespace

```{prompt} bash
kubectl config set-context --current --namespace=censys-cloud-connectors
```

3. Create a Kubernetes secret for the Environment Variables from the `.env`
file

```{prompt} bash
kubectl create secret generic censys-cloud-connectors-env \
  --from-env-file=.env \
  --dry-run=client \
  --save-config \
  -o yaml | kubectl apply -f -
```

4. Create a Kubernetes secret for the Censys Cloud Connector `providers.yml`
file

The chart will look for a secret named `censys-cloud-connectors-providers` in
the `censys-cloud-connectors` namespace. The secret should contain a file named
`providers.yml` with the contents of your `providers.yml` file.

```{prompt} bash
kubectl create secret generic censys-cloud-connectors-providers \
  --from-file=providers.yml \
  --dry-run=client \
  --save-config \
  -o yaml | kubectl apply -f -
```

5. (Optional) Create a Kubernetes secret for the Censys Cloud Connector
`secrets` directory

> **Note**
>
> This step is required if you are scanning Google Cloud Platform.
>
> If you choose to use this method, you will need to uncomment the
> `credentialsSecretName` value in the `values.yaml` file which should be set
> to `censys-cloud-connectors-secrets`.

```{prompt} bash
kubectl create secret generic censys-cloud-connectors-secrets \
  --from-file=secrets \
  --dry-run=client \
  --save-config \
  -o yaml | kubectl apply -f -
```

6. (Optional) Modify the `values.yaml` file to customize the deployment

This is the place to customize the schedule of the Censys Cloud Connector, the
default is to run every 4 hours. We recommend that you do not run the Censys
Cloud Connector more frequently than every hour. For assistance with
writing the cron schedule, please see the [Crontab Guru](https://crontab.guru/)
website.

See the [Configuration](#configuration) section for more information on the
available configuration options.

7. Install the Censys Cloud Connector Chart

```{prompt} bash
helm upgrade --install censys-cloud-connectors ./kubernetes/censys-cloud-connectors
```

8. Run the Censys Cloud Connector Manually

```{prompt} bash
kubectl create job --from=cronjob/censys-cloud-connectors censys-cloud-connectors-manual --dry-run=client -o yaml | kubectl apply -f -
```

9. Check the logs of the Censys Cloud Connector Job

```{prompt} bash
kubectl logs job.batch/censys-cloud-connectors-manual --follow
```
<!-- markdownlint-enable MD029 -->
## Configuration

The following table describes the available configuration options for the
Censys Cloud Connector Chart.

| Key                         | Description                                                                                                                 |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `envSecretName`             | The name of the secret containing the .env file.                                                                            |
| `providersSecretName`       | The name of the secret containing the providers.yml file.                                                                   |
| `nameOverride`              | (Optional) The override for the name of the chart.                                                                          |
| `fullnameOverride`          | (Optional) The override for the fullname (including release name) of the chart.                                             |
| `imagePullSecrets`          | (Optional) The authorization token to use when accessing the docker registry.                                               |
| `image.repository`          | The image for the censys-cloud-connector container.                                                                         |
| `image.pullPolicy`          | (Optional) Overrides the image pull policy.                                                                                 |
| `image.tag`                 | (Optional) Overrides the image tag whose default is latest.                                                                 |
| `cronjob.schedule`          | (Optional) The interval at which the censys-cloud-connector container will run (in cron format). Defaults to every 4 hours. |
| `cronjob.concurrencyPolicy` | (Optional) The concurrency policy for the cronjob.                                                                          |
| `podAnnotations`            | (Optional) The annotations to add to the pod.                                                                               |
| `podSecurityContext`        | (Optional) The security context to add to the pod.                                                                          |
| `securityContext`           | (Optional) The security context to add to the container.                                                                    |
| `resources`                 | (Optional) The resources to allocate to the container.                                                                      |
| `nodeSelector`              | (Optional) The node selector to use when scheduling the pod.                                                                |
| `tolerations`               | (Optional) The tolerations to use when scheduling the pod.                                                                  |
| `affinity`                  | (Optional) The affinity to use when scheduling the pod.                                                                     |
<!-- markdownlint-enable MD013 -->

## Upgrading

To upgrade the Censys Cloud Connector Chart, ensure that you have the latest
version of the chart and run the following command:

```{prompt} bash
helm upgrade --install censys-cloud-connectors ./kubernetes/censys-cloud-connectors
```

## Uninstalling

To uninstall the Censys Cloud Connector Chart, run the following command:

```{prompt} bash
helm uninstall censys-cloud-connectors
```

You can also delete the Censys Cloud Connector namespace:

```{prompt} bash
kubectl delete namespace censys-cloud-connectors
```

## Troubleshooting

### The Censys Cloud Connector is not running

If the Censys Cloud Connector is not running, you can check the logs of the
Censys Cloud Connector Job to see if there are any errors.

```{prompt} bash
kubectl logs job.batch/censys-cloud-connectors-manual --follow
```

#### The Censys Cloud Connector is not able to access the `.env` file

If you see an error similar to the following, it means that the Censys Cloud
Connector is not able to access the `.env` file.

```{prompt} bash
ERROR:censys_cloud_connectors: n validation error for Settings
...
```

This means that the `envSecretName` value in the `values.yaml` file is
either incorrect or the secret does not contain the `.env` file. You may also
be provided with a more specific error message indicating which environment
variable is missing or invalid.

#### The Censys Cloud Connector is not able to access the `providers.yml` file

If you see an error similar to the following, it means that the Censys Cloud
Connector is not able to access the `providers.yml` file.

```{prompt}
Error: [Errno 2] No such file or directory: '/providers/providers.yml'
```

This means that the `providersSecretName` value in the `values.yaml` file is
or the secret does not contain the `providers.yml` file.

#### The Censys Cloud Connector is not able to access the `secrets` directory

If you see an error similar to the following, it means that the Censys Cloud
Connector is not able to access the `secrets` directory.

```{prompt}
Error: [Errno 2] No such file or directory: 'secrets/<file>'
```

This means that the `secretsSecretName` value in the `values.yaml` file is
either incorrect or the secrets directory does not contain the required files.

### My issue is not listed here

If your issue is not listed here, please contact [Censys Support](mailto:support@censys.io).
