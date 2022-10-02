# cluster auto scaling --------------------------------
resource "aws_autoscaling_group" "ecs_cluster" {
    vpc_zone_identifier  = [ data.aws_subnet.main.id, data.aws_subnet.sub1.id, data.aws_subnet.sub2.id ]
    name                 = "ecs-${var.cluster_name}"
    min_size             = var.autoscale ["min"]
    max_size             = var.autoscale ["max"]
    desired_capacity     = var.autoscale ["desired"]
    health_check_type    = "EC2"
    launch_configuration = aws_launch_configuration.host.name
}

resource "aws_autoscaling_policy" "memory-reservation" {
  name                   = "${var.cluster_name}-memory-reservation"
  policy_type            = "TargetTrackingScaling"
  adjustment_type        = "ChangeInCapacity"
  autoscaling_group_name = aws_autoscaling_group.ecs_cluster.name

  target_tracking_configuration {
    customized_metric_specification {
      metric_dimension {
        name  = "ClusterName"
        value = var.cluster_name
      }

      metric_name = "MemoryReservation"
      namespace   = "AWS/ECS"
      statistic   = "Average"
    }
    target_value = 70.0
  }
}


# policy for service addition ---------------------------
resource "aws_autoscaling_policy" "cpu-tracking" {
  name                      = "${var.cluster_name}-cpu-tracking"
  policy_type               = "TargetTrackingScaling"
  adjustment_type           = "ChangeInCapacity"
  autoscaling_group_name    = aws_autoscaling_group.ecs_cluster.name

  target_tracking_configuration {
    customized_metric_specification {
      metric_dimension {
        name  = "ClusterName"
        value = var.cluster_name
      }

      metric_name = "CPUReservation"
      namespace   = "AWS/ECS"
      statistic   = "Average"
    }
    target_value = 50.0
  }
}