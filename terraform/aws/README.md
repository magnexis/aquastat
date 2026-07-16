# AquaStat AWS Module

Deploys AquaStat into a private AWS VPC using:

- ECS Fargate for the API
- RDS PostgreSQL for metadata storage
- ElastiCache Redis for cache and rate-limit state
- Internal ALB for ingress

## Usage

```bash
cd terraform/aws
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

This module is private-by-default. The ALB is internal and only accepts traffic from `allowed_ingress_cidrs`.

Before applying in a real AWS account, populate the provider-specific values in `terraform.tfvars` and wire in organization-managed values such as VPC CIDRs, certificate strategy, container image, DNS, and secret references.
