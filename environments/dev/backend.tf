# The bucket name is passed at init time so it stays out of the repo:
#   terraform init -backend-config="bucket=<state bucket name>"
terraform {
  backend "s3" {
    key          = "dev/terraform.tfstate"
    region       = "us-east-2"
    use_lockfile = true
    encrypt      = true
  }
}
