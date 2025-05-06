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
    scale_out_cooldown = 30

    scale_in_cooldown = 30
  }
}
