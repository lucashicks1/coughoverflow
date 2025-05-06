resource "aws_db_instance" "coughoverflow_database" {
  allocated_storage      = 20
  max_allocated_storage  = 1000
  engine                 = "postgres"
  engine_version         = "17"
  instance_class         = "db.t4g.medium"
  db_name                = "coughoverflow"
  username               = local.database_username
  password               = local.database_password
  parameter_group_name   = aws_db_parameter_group.db_params.name
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.coughoverflow_database.id]
  publicly_accessible    = true
  tags = {
    Name = "coughoverflow_database"
  }
}

// Parameters (increase max connections)
resource "aws_db_parameter_group" "db_params" {
  family = "postgres17"
  parameter {
    name         = "max_connections"
    value        = 400 # Set max num connections
    apply_method = "pending-reboot"
  }
}

resource "aws_security_group" "coughoverflow_database" {
  name        = "coughoverflow_database"
  description = "Allow inbound Postgres traffic"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "coughoverflow_db_security_group"
  }
}
