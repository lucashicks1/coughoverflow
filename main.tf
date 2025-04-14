terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.0.2"
    }
  }
}

provider "aws" {
  region                   = "us-east-1"
  shared_credentials_files = ["./credentials"]
  default_tags {
    tags = {
      Course     = "CSSE6400"
      Name       = "CoughOverflow"
      Automation = "Terraform"
    }
  }
}

locals {
  database_username = "administrator"
  database_password = "VerySecurePassword123XYZ"
}


data "aws_iam_role" "lab" {
  name = "LabRole"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "local_file" "url" {
  content  = "http://${aws_lb.coughoverflow.dns_name}/ap1/v1" # Replace this string with a URL from your Terraform.
  filename = "./api.txt"
}
