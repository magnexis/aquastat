# AquaStat GCP Module

Deploys AquaStat into a private GCP network using:

- Cloud Run for the API
- Cloud SQL PostgreSQL for metadata storage
- Memorystore Redis for cache and rate-limit state
- VPC Access and private service networking

## Usage

```bash
cd terraform/gcp
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

This module keeps the service private to the internal load balancer ingress path and private networking.

Before applying in a real GCP project, populate the provider-specific values in `terraform.tfvars` and wire in organization-managed values such as project IDs, networking ranges, service accounts, container image references, and secret bindings.
