# task definition ----------------------------------------
resource "aws_ecs_task_definition" "skitai-dep" {
    family             = var.task_definition_name [terraform.workspace]
    execution_role_arn = data.aws_iam_role.ecs_tasks_execution_role.arn
    volume {
        name      = "pub"
        host_path = "/var/www/pub"
    }
    container_definitions = <<EOF
[
    {
        "name": "${var.alb_container_name}",
        "image": "registry.gitlab.com/skitai/skitai-dep/nginx",
        "cpu": 0,
        "memoryReservation": 16,
        "portMappings": [
            {
                "containerPort": 80,
                "hostPort": 0,
                "protocol": "tcp"
            }
        ],
        "essential": true,
        "environment": [],
        "mountPoints": [
            {
              "containerPath": "/var/www/pub",
              "sourceVolume": "pub"
            }
        ],
        "repositoryCredentials": {
            "credentialsParameter": "${data.aws_secretsmanager_secret.by_name.arn}"
        },
        "dependsOn": [
            {
                "containerName": "skitai-dep",
                "condition": "HEALTHY"
            }
        ],
        "links": [
            "skitai-dep"
        ]
    },

    {
        "name": "skitai-dep",
        "image": "registry.gitlab.com/skitai/skitai-dep",
        "cpu": 0,
        "memoryReservation": 120,
        "links": [],
        "portMappings": [
            {
                "containerPort": 5000,
                "hostPort": 0,
                "protocol": "tcp"
            }
        ],
        "essential": true,
        "entryPoint": ["./dep/production.sh"],
        "environment": [],
        "mountPoints": [
            {
              "containerPath": "/var/www/pub",
              "sourceVolume": "pub"
            }
        ],
        "repositoryCredentials": {
            "credentialsParameter": "${data.aws_secretsmanager_secret.by_name.arn}"
        },
        "healthCheck": {
            "command": [
                "CMD-SHELL",
                "wget -O/dev/null -q http://localhost:5000 || exit 1"
            ]
        }
    }
]
EOF
}


# service -------------------------------------------------------
resource "aws_ecs_service" "skitai-dep" {
    name            = var.service_name [terraform.workspace]
    cluster         = data.aws_ecs_cluster.main.id
    task_definition = aws_ecs_task_definition.skitai-dep.arn
    iam_role        = data.aws_iam_role.ecs_service_role.arn
    desired_count   = var.service_auto_scaling.desired_count
    load_balancer {
        target_group_arn = aws_alb_target_group.skitai-dep.id
        container_name   = var.alb_container_name
        container_port   = 80
    }
}


# alb target gorup and routing rule -----------------------
resource "aws_alb_target_group" "skitai-dep" {
  name     = "${var.cluster_name}-${var.service_name [terraform.workspace]}"
  port     = 80
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.main.id

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
  }

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    interval            = 300
    matcher             = "200,301,302,404"
  }
}

resource "aws_lb_listener_rule" "default" {
  listener_arn = data.aws_alb_listener.front_end.arn
  priority     = var.listener_priority [terraform.workspace]

  action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.skitai-dep.arn
  }

  condition {
    path_pattern {
      values = var.path_patterns
    }
  }

  condition {
    host_header {
      values = var.hosts [terraform.workspace]
    }
  }
}


# service auto scaling -------------------------------------------
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.service_auto_scaling.max
  min_capacity       = var.service_auto_scaling.min
  resource_id        = "service/${var.cluster_name}/${var.service_name [terraform.workspace]}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
  role_arn           = data.aws_iam_role.ecs_service_autoscale_role.arn
}

resource "aws_appautoscaling_policy" "ecs_target_cpu" {
  name               = "application-scaling-policy-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = var.service_auto_scaling.avg_cpu_utilization_threshold
  }
  depends_on = [aws_appautoscaling_target.ecs_target]
}

resource "aws_appautoscaling_policy" "ecs_target_memory" {
  name               = "application-scaling-policy-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = var.service_auto_scaling.avg_memory_usage_threshold
  }
  depends_on = [aws_appautoscaling_target.ecs_target]
}