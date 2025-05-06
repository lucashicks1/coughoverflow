resource "aws_appautoscaling_target" "relaxed_ecs_target" {
  max_capacity       = 25
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.coughoverflow.name}/${aws_ecs_service.coughoverflow_worker_relaxed.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "relaxed_scaling_policy" {
  name               = "relaxed_scaling_policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.relaxed_ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.relaxed_ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.relaxed_ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = local.max_num_messages_relaxed

    scale_in_cooldown  = 30
    scale_out_cooldown = 30

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
              value = aws_sqs_queue.coughoverflow_relaxed.name
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
            metric_name = "DesiredTaskCount"
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
        expression  = "m1 / m2"
        return_data = true
      }
    }
  }
}
