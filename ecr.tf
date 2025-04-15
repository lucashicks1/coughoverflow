data "aws_ecr_authorization_token" "ecr_token" {}

provider "docker" {
  registry_auth {
    address  = data.aws_ecr_authorization_token.ecr_token.proxy_endpoint
    username = data.aws_ecr_authorization_token.ecr_token.user_name
    password = data.aws_ecr_authorization_token.ecr_token.password
  }
}


resource "aws_ecr_repository" "coughoverflow_api" {
  name = "coughoverflow_api"
}

resource "docker_image" "coughoverflow_api" {
  name = "${aws_ecr_repository.coughoverflow_api.repository_url}:latest"
  build {
    context  = "api"
    platform = "linux/amd64"
  }
}

resource "docker_registry_image" "coughoverflow_api" {
  name = docker_image.coughoverflow_api.name
}


resource "aws_ecr_repository" "coughoverflow_worker" {
  name = "coughoverflow_worker"
}


resource "docker_image" "coughoverflow_worker" {
  name = "${aws_ecr_repository.coughoverflow_worker.repository_url}:latest"
  build {
    context  = "worker"
    platform = "linux/amd64"
  }
}

resource "docker_registry_image" "coughoverflow_worker" {
  name = docker_image.coughoverflow_worker.name
}
