# Supported Providers

The following providers and services are supported and will be used to import
Seeds (IP Addresses, Domain Names, CIDRs, and ASNs) as well as Cloud Assets
(Object Storage Buckets) into the Censys ASM platform.

## Amazon Web Services

- [Compute](https://aws.amazon.com/products/compute/)
  - [Elastic Container Service (ECS)](https://aws.amazon.com/ecs/)
  - [Elastic Compute Cloud (EC2)](https://aws.amazon.com/ec2/)
- [Database](https://aws.amazon.com/products/databases/)
  - [Relational Database Service (RDS)](https://aws.amazon.com/rds/)
- [Network & Content Delivery](https://aws.amazon.com/products/networking)
  - [API Gateway](https://aws.amazon.com/api-gateway)
  - [Elastic Load Balancing (ELB)](https://aws.amazon.com/elasticloadbalancing/)
  - [Route53](https://aws.amazon.com/route53/)
- [Cloud Storage](https://aws.amazon.com/products/storage/)
  - [Simple Storage Service (S3)](https://aws.amazon.com/s3/features/)

## Azure Cloud

- [Azure Networking](https://azure.microsoft.com/en-us/product-categories/networking/)
  - [Azure DNS](https://azure.microsoft.com/en-us/services/dns/)
- [Azure Container Services](https://azure.microsoft.com/en-us/product-categories/containers/)
  - [Container Instances](https://azure.microsoft.com/en-us/services/container-instances/)
- [Azure Databases](https://azure.microsoft.com/en-us/product-categories/databases/)
  - [Azure SQL](https://azure.microsoft.com/en-us/products/azure-sql/)
- [Azure Storage](https://azure.microsoft.com/en-us/product-categories/storage/)
  - [Azure Blob Storage](https://azure.microsoft.com/en-us/services/storage/blobs/)

## Google Cloud Platform

- [Google Cloud Compute](https://cloud.google.com/products/compute)
  - [Compute Engine](https://cloud.google.com/compute)
- [Google Cloud Containers](https://cloud.google.com/containers)
  - [Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
- [Google Cloud Networking](https://cloud.google.com/products/networking)
  - [Cloud DNS](https://cloud.google.com/dns)
- [Google Cloud Databases](https://cloud.google.com/products/databases)
  - [Cloud SQL](https://cloud.google.com/sql)
- [Google Cloud Storage](https://cloud.google.com/products/storage)
  - [Cloud Storage](https://cloud.google.com/storage)

## Authenticating

Log in to your cloud provider's CLI tool using the following commands:

- [AWS CLI][aws-cli]: `aws configure` or `aws configure sso`

- [Azure CLI][azure-cli]: `az login`

- [Google's gcloud CLI][gcloud-cli]: `gcloud auth login`

<!-- References -->
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
[azure-cli]: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
[gcloud-cli]: https://cloud.google.com/sdk/docs/install
