resource "aws_key_pair" "default" {
    key_name   = var.cluster_name
    public_key = file (var.public_key_file)
}

data "aws_ami" "latest_ecs" {
  most_recent = true
  filter {
    name   = "name"
    values = ["*amazon-ecs-optimized"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["591542846629"] # AWS
}


resource "aws_iam_instance_profile" "profile" {
  name = "${var.cluster_name}-profile"
  role = aws_iam_role.ecs_host_role.name
}

resource "aws_launch_configuration" "host" {
    name                        = var.cluster_name
    image_id                    = data.aws_ami.latest_ecs.id
    instance_type               = var.instance_type
    security_groups             = [ aws_security_group.host.id ]
    iam_instance_profile        = aws_iam_instance_profile.profile.name
    key_name                    = aws_key_pair.default.key_name
    associate_public_ip_address = true
    user_data                   = "#!/bin/bash\necho ECS_CLUSTER='${var.cluster_name}' > /etc/ecs/ecs.config"
}

resource "aws_launch_template" "host" {
    name                        = var.cluster_name
    image_id                    = data.aws_ami.latest_ecs.id
    instance_type               = var.instance_type
    iam_instance_profile {
      name = aws_iam_instance_profile.profile.name
    }
    monitoring {
      enabled = true
    }
    network_interfaces {
      security_groups             = [ aws_security_group.host.id ]
      subnet_id                   = random_shuffle.subnets.result [0]
      associate_public_ip_address = true
    }
    key_name                    = aws_key_pair.default.key_name
    user_data                   = base64encode ("#!/bin/bash\necho ECS_CLUSTER='${var.cluster_name}' > /etc/ecs/ecs.config")
}