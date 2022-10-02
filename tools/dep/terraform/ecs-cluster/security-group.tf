
resource "aws_security_group" "host" {
    name        = "${var.cluster_name}-host"
    description = "allows host service ports"
    vpc_id      = data.aws_vpc.main.id

    ingress {
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
        from_port   = 5000
        to_port     = 5000
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
        from_port   = 32768
        to_port     = 65535
        protocol    = "tcp"
        description = "Access from ALB"
        security_groups = [
            data.aws_security_group.load_balancer.id
        ]
    }

    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "${var.cluster_name}-host"
    }
}
