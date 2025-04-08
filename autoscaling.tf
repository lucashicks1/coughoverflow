resource "aws_appautoscaling_target" "coughoverflow" {
  service_namespace = "ecs"
  resource_id       = "service/coughoverflow/coughoverflow"

  max_capacity       = 4
  min_capacity       = 1
  scalable_dimension = "ecs:service:DesiredCount"

  depends_on = [aws_ecs_service.coughoverflow]
}

resource "aws_appautoscaling_policy" "coughoverflow-cpu" {
  name               = "coughoverflow-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.coughoverflow.resource_id
  scalable_dimension = aws_appautoscaling_target.coughoverflow.scalable_dimension
  service_namespace  = aws_appautoscaling_target.coughoverflow.service_namespace
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 20
  }
}
