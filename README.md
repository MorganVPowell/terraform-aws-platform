# Terraform AWS Platform

Infrastructure as Code for a small AWS platform: remote state, a reusable VPC module, a Kubernetes cluster, and a Prometheus/Grafana monitoring stack.

(work in progress: Phase 1 builds remote state and the VPC)

## Layout
- bootstrap/: creates the S3 bucket that stores remote state
- modules/vpc/: reusable VPC module (public and private subnets, optional NAT gateway)
- environments/dev/: the dev environment that uses the modules
