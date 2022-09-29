terraform {
  required_version = ">= 1.1.2"
  backend "s3" {
    bucket = "states-data"
    key = "terraform/skitai/services/skitai-dep/terraform.tfstate"
    region = "ap-northeast-2"
    encrypt = true
    acl = "bucket-owner-full-control"
  }
}

provider "aws" {}

# variables -----------------------------------------------
variable "cluster_name" {
  default = "skitai-cluster"
}

variable "path_patterns" {
  default = [ "/*" ]
}

variable "service_name" {
  default = {
    production = "skitai-dep"
    qa         = "skitai-dep-qa"
  }
}

variable "task_definition_name" {
  default = {
    production = "skitai-dep"
    qa         = "skitai-dep-qa"
  }
}

variable "hosts" {
  default = {
    production = [ "skitai.sns.co.kr" ]
    qa         = [ "qa.skitai.sns.co.kr" ]
  }
}

variable "listener_priority" {
  default = {
    production = 101
    qa         = 100
  }
}

variable "registry_secret_name" {
  default = "gitlab/deploy/dep-test"
}

variable "alb_container_name" {
   default = "skitai-nginx"
}

variable "service_auto_scaling" {
  default = {
    desired_count = 1
    min = 1
    max = 16
    avg_cpu_utilization_threshold = 40.0 # 2 services and nginx will be not busy
    avg_memory_usage_threshold = 80.0
  }
}

# infra -----------------------------------------------
data "aws_vpc" "main" {
  tags = {
  Name = var.cluster_name
  }
}

data "aws_security_group" "host" {
    name = "${var.cluster_name}-host"
}

data "aws_alb" "load_balancer" {
  name = var.cluster_name
}

data "aws_iam_role" "ecs_tasks_execution_role" {
  name = "ecs-task-execution-role"
}

data "aws_iam_instance_profile" "profile" {
  name = "${var.cluster_name}-profile"
}

data "aws_iam_role" "ecs_service_role" {
  name = "ecs-service-role"
}

data "aws_ecs_cluster" "main" {
  cluster_name = var.cluster_name
}

data "aws_alb_listener" "front_end" {
  load_balancer_arn = data.aws_alb.load_balancer.arn
  port              = 443
}

data "aws_secretsmanager_secret" "by_name" {
  name = var.registry_secret_name
}

data "aws_launch_template" "host" {
  name = var.cluster_name
}

data "aws_iam_role" "ecs_service_autoscale_role" {
  name = "ecs-service-scale-application"
}
