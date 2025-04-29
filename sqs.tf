resource "aws_sqs_queue" "coughoverflow_relaxed" {
  name                       = "coughoverflow_main"
  message_retention_seconds  = 3600
  visibility_timeout_seconds = 30
}

resource "aws_sqs_queue" "coughoverflow_urgent" {
  name                       = "coughoverflow_main"
  message_retention_seconds  = 3600
  visibility_timeout_seconds = 30
}
