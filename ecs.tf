resource "aws_ecs_cluster" "coughoverflow" {
  name = "coughoverflow"
}

resource "aws_ecs_service" "coughoverflow_api" {
  name            = "coughoverflow_api"
  cluster         = aws_ecs_cluster.coughoverflow.id
  task_definition = aws_ecs_task_definition.coughoverflow_api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.coughoverflow_api.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.coughoverflow.arn
    container_name   = "coughoverflow_api"
    container_port   = 8080
  }
}

resource "aws_ecs_task_definition" "coughoverflow_api" {
  family                   = "coughoverflow_api"
  requires_compatibilities = ["FARGATE"]

  network_mode       = "awsvpc"
  cpu                = 1024
  memory             = 2048
  execution_role_arn = data.aws_iam_role.lab.arn

  container_definitions = jsonencode([
    {
      image       = "${docker_image.coughoverflow_api.name}",
      cpu         = 1024,
      memory      = 2048,
      name        = "coughoverflow_api",
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
        },
        {
          name  = "QUEUE_TYPE",
          value = "sqs"
        },
        {
          name  = "AWS_SQS_URL",
          value = "${aws_sqs_queue.coughoverflow_relaxed.url}"
        },
        {
          name  = "AWS_SQS_URL_URGENT",
          value = "${aws_sqs_queue.coughoverflow_urgent.url}"
        },
      ],
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

resource "aws_security_group" "coughoverflow_api" {
  name        = "coughoverflow_api"
  description = "CoughOverflow API Security Group"

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
    Name = "coughoverflow_api_security_group"
  }

}

resource "aws_security_group" "coughoverflow_worker" {
  name        = "coughoverflow_worker"
  description = "CoughOverflow Worker Security Group"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "coughoverflow_worker_security_group"
  }
}

resource "aws_ecs_service" "coughoverflow_worker_relaxed" {
  name            = "coughoverflow_worker_relaxed"
  cluster         = aws_ecs_cluster.coughoverflow.id
  task_definition = aws_ecs_task_definition.coughoverflow_worker_relaxed.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  iam_role        = data.aws_iam_role.lab.arn

  network_configuration {
    subnets         = data.aws_subnets.private.ids
    security_groups = [aws_security_group.coughoverflow_worker.id]
  }
}

resource "aws_ecs_task_definition" "coughoverflow_worker_relaxed" {
  family                   = "coughoverflow_worker_relaxed"
  requires_compatibilities = ["FARGATE"]

  network_mode       = "awsvpc"
  cpu                = 1024
  memory             = 2048
  execution_role_arn = data.aws_iam_role.lab.arn

  container_definitions = jsonencode([
    {
      image       = "${docker_image.coughoverflow_worker.name}",
      cpu         = 1024,
      memory      = 2048,
      name        = "coughoverflow_worker",
      networkMode = "awsvpc",
      environment = [
        {
          name  = "DB_URL",
          value = "postgres://${local.database_username}:${local.database_password}@${aws_db_instance.coughoverflow_database.address}:${aws_db_instance.coughoverflow_database.port}/${aws_db_instance.coughoverflow_database.db_name}?pool_max_conns=10"
        },
        {
          name  = "AWS_SQS_URL",
          value = "${aws_sqs_queue.coughoverflow_relaxed.url}"
        }
      ],

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

resource "aws_ecs_service" "coughoverflow_worker_urgent" {
  name            = "coughoverflow_worker_urgent"
  cluster         = aws_ecs_cluster.coughoverflow.id
  task_definition = aws_ecs_task_definition.coughoverflow_worker_urgent.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  iam_role        = data.aws_iam_role.lab.arn

  network_configuration {
    subnets         = data.aws_subnets.private.ids
    security_groups = [aws_security_group.coughoverflow_worker.id]
  }
}

resource "aws_ecs_task_definition" "coughoverflow_worker_urgent" {
  family                   = "coughoverflow_worker_urgent"
  requires_compatibilities = ["FARGATE"]

  network_mode       = "awsvpc"
  cpu                = 1024
  memory             = 2048
  execution_role_arn = data.aws_iam_role.lab.arn

  container_definitions = jsonencode([
    {
      image       = "${docker_image.coughoverflow_worker.name}",
      cpu         = 1024,
      memory      = 2048,
      name        = "coughoverflow_worker",
      networkMode = "awsvpc",
      environment = [
        {
          name  = "DB_URL",
          value = "postgres://${local.database_username}:${local.database_password}@${aws_db_instance.coughoverflow_database.address}:${aws_db_instance.coughoverflow_database.port}/${aws_db_instance.coughoverflow_database.db_name}?pool_max_conns=10"
        },
        {
          name  = "AWS_SQS_URL",
          value = "${aws_sqs_queue.coughoverflow_urgent.url}"
        }
      ],

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

