# VPC ----------------------------------------------
resource "aws_vpc" "main" {
    cidr_block           = "10.0.0.0/16"
    enable_dns_hostnames = true
    tags = {
        Name = var.cluster_name
    }
}

resource "aws_subnet" "pub1" {
    vpc_id                  = aws_vpc.main.id
    cidr_block              = "10.0.1.0/24"
    availability_zone       = lookup (var.availability_zone, "pub1")
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.cluster_name}-pub1"
    }
}

resource "aws_subnet" "pub2" {
    vpc_id                  = aws_vpc.main.id
    cidr_block              = "10.0.2.0/24"
    availability_zone       = lookup (var.availability_zone, "pub2")
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.cluster_name}-pub2"
    }
}

resource "aws_subnet" "pub3" {
    vpc_id                  = aws_vpc.main.id
    cidr_block              = "10.0.3.0/24"
    availability_zone       = lookup (var.availability_zone, "pub3")
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.cluster_name}-pub3"
    }
}


# gateways ----------------------------------------------
resource "aws_internet_gateway" "external" {
    vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "main" {
    vpc_id = aws_vpc.main.id
    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.external.id
    }
}

resource "aws_route_table_association" "external-pub1" {
    subnet_id      = aws_subnet.pub1.id
    route_table_id = aws_route_table.main.id
}

resource "aws_route_table_association" "external-pub2" {
    subnet_id      = aws_subnet.pub2.id
    route_table_id = aws_route_table.main.id
}

resource "aws_route_table_association" "external-pub3" {
    subnet_id      = aws_subnet.pub3.id
    route_table_id = aws_route_table.main.id
}