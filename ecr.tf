data "aws_ecr_authorization_token" "ecr_token" {}

resource "aws_ecr_repository" "coughoverflow" {
  name = "coughoverflow"
}

provider "docker" {
  registry_auth {
    address  = data.aws_ecr_authorization_token.ecr_token.proxy_endpoint
    username = data.aws_ecr_authorization_token.ecr_token.user_name
    password = data.aws_ecr_authorization_token.ecr_token.password
  }

}

resource "docker_image" "coughoverflow" {
  name = "${aws_ecr_repository.coughoverflow.repository_url}:latest"
  build {
    context  = "."
    platform = "linux/amd64"
  }
}

resource "docker_registry_image" "coughoverflow" {
  name = docker_image.coughoverflow.name
}
