# Kubernetes Deployment Method

This guide describes how to deploy the Censys Cloud Connector using Kubernetes.

## Prerequisites

The following prerequisites are required to deploy using Kubernetes:

- [A Kubernetes cluster](https://kubernetes.io/docs/setup/)
- [Helm](https://helm.sh/docs/intro/install/)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)

## Getting Started

1. Install the Censys Cloud Connector Chart

```sh <!-- markdownlint-disable-next-line MD013 -->
helm install censys-cloud-connectors ./kubernetes/censys-cloud-connectors --namespace YOUR_NAMESPACE
```

- To upgrade the Censys Cloud Connector Chart:

  ```sh <!-- markdownlint-disable-next-line MD013 -->
  helm upgrade censys-cloud-connectors ./kubernetes/censys-cloud-connectors --namespace YOUR_NAMESPACE
  ```
