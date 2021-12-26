terraform {
  required_version = ">= 1.1.2"
  backend "s3" {
    bucket  = "states-data"
    key     = "terraform/skitai/ecs-cluster/terraform.tfstate"
    region  = "ap-northeast-2"
    encrypt = true
    acl     = "bucket-owner-full-control"
  }
}

provider "aws" {}

variable "cluster_name" {
    default = "skitai-cluster"
}

variable "instance_type" {
  default = "t3.micro"
}

variable "public_key_file" {
  default = "~/.ssh/id_rsa.pub"
}

variable "autoscale" {
  default = {
      min     = 1
      max     = 4
      desired = 1
  }
}

# infra --------------------------------------------------
data "aws_vpc" "main" {
  tags = {
    Name = var.cluster_name
  }
}

data "aws_security_group" "default" {
  name   = "default"
  vpc_id = data.aws_vpc.main.id
}

data "aws_security_group" "load_balancer" {
  name = "${var.cluster_name}-load-balancer"
}

data "aws_subnet" "main" {
    vpc_id = data.aws_vpc.main.id
    tags = {
        Name = "${var.cluster_name}-pub1"
    }
}

data "aws_subnet" "sub1" {
    vpc_id = data.aws_vpc.main.id
    tags = {
        Name = "${var.cluster_name}-pub2"
    }
}

data "aws_subnet" "sub2" {
    vpc_id = data.aws_vpc.main.id
    tags = {
        Name = "${var.cluster_name}-pub3"
    }
}

resource "random_shuffle" "subnets" {
  input        = [ data.aws_subnet.main.id, data.aws_subnet.sub1.id, data.aws_subnet.sub2.id ]
  result_count = 1
}
