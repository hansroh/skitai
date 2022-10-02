terraform {
  required_version = ">= 1.1.2"
  backend "s3" {
    bucket  = "states-data"
    key     = "terraform/skitai/cloud-infra/terraform.tfstate"
    region  = "ap-northeast-2"
    encrypt = true
    acl     = "bucket-owner-full-control"
  }
}

provider "aws" {}

variable "cluster_name" {
    default = "skitai-cluster"
}

variable "availability_zone" {
  default = {
      pub1 = "ap-northeast-1d"
      pub2 = "ap-northeast-1c"
      pub3 = "ap-northeast-1a"
  }
}

variable "dns" {
  default = {
    zone      = "sns.co.kr"
    name      = "skitai.sns.co.kr"
    alt_names = ["qa.skitai.sns.co.kr"]
  }
}

data "aws_route53_zone" "primary" {
    name = var.dns ["zone"]
}
