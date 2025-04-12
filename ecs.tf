resource "aws_ecs_cluster" "coughoverflow" {
  name = "coughoverflow"
}


resource "aws_ecs_service" "coughoverflow" {
  name            = "coughoverflow"
  cluster         = aws_ecs_cluster.coughoverflow.id
  task_definition = aws_ecs_task_definition.coughoverflow.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.coughoverflow.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.coughoverflow.arn
    container_name   = "coughoverflow"
    container_port   = 8080
  }
}

resource "aws_ecs_task_definition" "coughoverflow" {
  family                   = "coughoverflow"
  requires_compatibilities = ["FARGATE"]

  network_mode       = "awsvpc"
  cpu                = 1024
  memory             = 2048
  execution_role_arn = data.aws_iam_role.lab.arn

  container_definitions = jsonencode([
    {
      image       = "${docker_image.coughoverflow.name}",
      cpu         = 1024,
      memory      = 2048,
      name        = "coughoverflow",
      networkMode = "awsvpc",
      portMappings = [
        {
          containerPort = 8080,
          hostPort      = 8080
        }
      ],
      environment = [
        {
          name  = "DB_URL",
          value = "postgresql+asyncpg://${local.database_username}:${local.database_password}@${aws_db_instance.coughoverflow_database.address}:${aws_db_instance.coughoverflow_database.port}/${aws_db_instance.coughoverflow_database.db_name}"
        }
      ],
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/api/v1/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = "/coughoverflow/db",
          awslogs-region        = "us-east-1",
          awslogs-stream-prefix = "ecs",
          awslogs-create-group  = "true"
        }
      }
    }
  ])
}

resource "aws_security_group" "coughoverflow" {
  name        = "coughoverflow"
  description = "CoughOverflow Security Group"

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }


  tags = {
    Name = "coughoverflow_security_group"
  }

}
