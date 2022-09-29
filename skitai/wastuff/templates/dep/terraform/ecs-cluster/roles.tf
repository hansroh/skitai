# ecs task execution role -----------------------------
data "aws_iam_policy_document" "ecs_tasks_execution_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_tasks_execution_role" {
  name = "ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_execution_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_tasks_execution_attach" {
  role       = aws_iam_role.ecs_tasks_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceRole"
}

resource "aws_iam_role_policy_attachment" "ecs_tasks_execution_attach2" {
  role       = aws_iam_role.ecs_tasks_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_secret_read_policy_attach" {
  name   = "ecs-secret-read-policy"
  role   = aws_iam_role.ecs_tasks_execution_role.id
  policy = file("policies/ecs-secret-read.json")
}


# ec2 policy ----------------------------------
resource "aws_iam_role" "ecs_host_role" {
    name               = "ecs-host-role"
    assume_role_policy = file("policies/ec2-role.json")
}

resource "aws_iam_instance_profile" "ecs" {
    name = "instance-profile"
    path = "/"
    role = aws_iam_role.ecs_host_role.name
}

resource "aws_iam_role_policy" "ecs_host_policy" {
  name   = "ecs-ec2-role-policy"
  role   = aws_iam_role.ecs_host_role.id
  policy = file("policies/ecs-ec2-role-policy.json")
}


# ecs service role -----------------------------
resource "aws_iam_role" "ecs_service_role" {
    name               = "ecs-service-role"
    assume_role_policy = file("policies/ecs-role.json")
}

resource "aws_iam_role_policy_attachment" "ecs_service_attach" {
  role       = aws_iam_role.ecs_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceRole"
}


# ecs service auto scaling -------------------------------
resource "aws_iam_role" "ecs_service_autoscale_role" {
  name = "ecs-service-scale-application"
  assume_role_policy = file("policies/ecs-service-auto-scaling-role.json")
}

resource "aws_iam_role_policy_attachment" "ecs-autoscale" {
  role = aws_iam_role.ecs_service_autoscale_role.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole"
}