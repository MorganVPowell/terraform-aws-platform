variable "cluster_name" {
  type = string
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets for the control plane and worker nodes"
}

variable "kubernetes_version" {
  type        = string
  default     = null
  description = "Leave null to use the EKS default version"
}

variable "instance_types" {
  type    = list(string)
  default = ["t3.small"]
}

variable "desired_size" {
  type    = number
  default = 2
}

variable "max_size" {
  type    = number
  default = 2
}

variable "disk_size" {
  type    = number
  default = 20
}
