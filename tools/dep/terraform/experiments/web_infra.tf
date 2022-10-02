# ssh-keygen -t rsa -b 4096 -C "<EMAIL_ADDRESS>" -f "$HOME/.ssh/web_admin" -N ""
resource "aws_key_pair" "web_admin" {
  key_name = "web_admin"
  public_key = file("~/.ssh/web_admin.pub")
}

resource "aws_security_group" "ssh" {
  name = "allow_ssh_from_all"
  description = "Allow SSH port from all"
  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_security_group" "default" {
  name = "default"
}

resource "aws_instance" "web" {
  ami = "ami-00bc9b7f0e98dc134" # Ubuntu Server 18.04 LTS (HVM), SSD Volume Type
  instance_type = "t2.nano"
  key_name = aws_key_pair.web_admin.key_name
  vpc_security_group_ids = [
    aws_security_group.ssh.id,
    data.aws_security_group.default.id
  ]
}

resource "aws_security_group" "postgres" {
  name = "allow_postgres_from_all"
  description = "Allow SSH port from all"
  ingress {
    from_port = 5432
    to_port = 5432
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "web_db2" {
  allocated_storage = 8
  engine = "postgres"
  engine_version = "12.8"
  instance_class = "db.t2.micro"
  name = "terraform"
  username = "terraform"
  password = "password"
  skip_final_snapshot = true
  publicly_accessible = true
  vpc_security_group_ids = [
    aws_security_group.postgres.id,
    data.aws_security_group.default.id
  ]
}