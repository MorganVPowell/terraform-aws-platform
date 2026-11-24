variable "name" {
  type        = string
  description = "Name prefix for all resources"
}

variable "cidr_block" {
  type    = string
  default = "10.0.0.0/16"
}

variable "azs" {
  type        = list(string)
  description = "Availability zones, one subnet pair per zone"
}

variable "public_subnet_cidrs" {
  type = list(string)
}

variable "private_subnet_cidrs" {
  type = list(string)
}

variable "enable_nat_gateway" {
  type        = bool
  default     = false
  description = "NAT gateways cost money every hour, so this is off by default"
}
