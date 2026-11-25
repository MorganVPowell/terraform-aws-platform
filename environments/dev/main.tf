terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "terraform-aws-platform"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source = "../../modules/vpc"

  name                 = "platform-dev"
  azs                  = slice(data.aws_availability_zones.available.names, 0, 2)
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24"]
  enable_nat_gateway   = var.enable_nat_gateway
}

# No NAT gateway: nodes run in the public subnets to save cost (a deliberate learning-project tradeoff)
module "eks" {
  source = "../../modules/eks"

  cluster_name = "platform-dev"
  subnet_ids   = module.vpc.public_subnet_ids
  desired_size = var.node_count
  max_size     = var.node_count
}
