resource "aws_appautoscaling_target" "coughoverflow_api" {
  service_namespace = "ecs"
  resource_id       = "service/${aws_ecs_cluster.coughoverflow.name}/${aws_ecs_service.coughoverflow_api.name}"

  max_capacity       = 25 # What is the best way to determine suitable values, without load numbers
  min_capacity       = 3
  scalable_dimension = "ecs:service:DesiredCount"

  depends_on = [aws_ecs_service.coughoverflow_api]
}

resource "aws_appautoscaling_policy" "coughoverflow-cpu" {
  name               = "coughoverflow-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.coughoverflow_api.resource_id
  scalable_dimension = aws_appautoscaling_target.coughoverflow_api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.coughoverflow_api.service_namespace
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 20

    # How long to wait before scaling out again
    scale_out_cooldown = 60

    scale_in_cooldown = 180
  }
}

resource "aws_appautoscaling_target" "coughoverflow_worker_relaxed" {
  service_namespace = "ecs"
  resource_id       = "service/${aws_ecs_cluster.coughoverflow.name}/${aws_ecs_service.coughoverflow_worker_relaxed.name}"

  max_capacity       = 25 # What is the best way to determine suitable values, without load numbers
  min_capacity       = 1
  scalable_dimension = "ecs:service:DesiredCount"

  depends_on = [aws_ecs_service.coughoverflow_worker_relaxed]
}


resource "aws_appautoscaling_policy" "coughoverflow_worker_relaxed" {
  name               = "coughoverflow_worker_relaxed"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.coughoverflow_worker_relaxed.resource_id
  scalable_dimension = aws_appautoscaling_target.coughoverflow_worker_relaxed.scalable_dimension
  service_namespace  = aws_appautoscaling_target.coughoverflow_worker_relaxed.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = local.max_num_messages_relaxed

    scale_out_cooldown = 60

    scale_in_cooldown = 180

    customized_metric_specification {
      metrics {
        label = "Get the queue size (the number of messages waiting to be processed)"
        id    = "queue_size"

        metric_stat {
          metric {
            metric_name = "ApproximateNumberOfMessagesVisible"
            namespace   = "AWS/SQS"

            dimensions {
              name  = "QueueName"
              value = aws_sqs_queue.coughoverflow_relaxed.name
            }
          }

          stat = "Sum"
        }

        return_data = false
      }

      metrics {
        label = "Get the ECS running task count (the number of currently running tasks)"
        id    = "num_ecs"

        metric_stat {
          metric {
            metric_name = "RunningTaskCount"
            namespace   = "ECS/ContainerInsights"

            dimensions {
              name  = "ClusterName"
              value = aws_ecs_cluster.coughoverflow.name
            }

            dimensions {
              name  = "ServiceName"
              value = aws_ecs_service.coughoverflow_worker_relaxed.name
            }
          }

          stat = "Average"
        }

        return_data = false
      }

      metrics {
        label       = "Calculate the backlog per instance"
        id          = "e1"
        expression  = "queue_size / num_ecs"
        return_data = true
      }
    }
  }
}

resource "aws_appautoscaling_target" "coughoverflow_worker_urgent" {
  service_namespace = "ecs"
  resource_id       = "service/${aws_ecs_cluster.coughoverflow.name}/${aws_ecs_service.coughoverflow_worker_urgent.name}"

  max_capacity       = 25 # What is the best way to determine suitable values, without load numbers
  min_capacity       = 1
  scalable_dimension = "ecs:service:DesiredCount"

  depends_on = [aws_ecs_service.coughoverflow_worker_urgent]
}


resource "aws_appautoscaling_policy" "coughoverflow_worker_urgent" {
  name               = "coughoverflow_worker_urgent"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.coughoverflow_worker_urgent.resource_id
  scalable_dimension = aws_appautoscaling_target.coughoverflow_worker_urgent.scalable_dimension
  service_namespace  = aws_appautoscaling_target.coughoverflow_worker_urgent.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = local.max_num_messages_urgent

    scale_out_cooldown = 60

    scale_in_cooldown = 180

    customized_metric_specification {
      metrics {
        label = "Get the queue size (the number of messages waiting to be processed)"
        id    = "m1"

        metric_stat {
          metric {
            metric_name = "ApproximateNumberOfMessagesVisible"
            namespace   = "AWS/SQS"

            dimensions {
              name  = "QueueName"
              value = aws_sqs_queue.coughoverflow_urgent.name
            }
          }

          stat = "Sum"
        }

        return_data = false
      }

      metrics {
        label = "Get the ECS running task count (the number of currently running tasks)"
        id    = "m2"

        metric_stat {
          metric {
            metric_name = "RunningTaskCount"
            namespace   = "ECS/ContainerInsights"

            dimensions {
              name  = "ClusterName"
              value = aws_ecs_cluster.coughoverflow.name
            }

            dimensions {
              name  = "ServiceName"
              value = aws_ecs_service.coughoverflow_worker_urgent.name
            }
          }

          stat = "Average"
        }

        return_data = false
      }

      metrics {
        label       = "Calculate the backlog per instance"
        id          = "e1"
        expression  = "m1 / m2"
        return_data = true
      }
    }
  }
}
