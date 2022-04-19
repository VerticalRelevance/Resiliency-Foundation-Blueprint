locals {
  lambda_src_path = "${path.module}${var.lambda_relative_path}lambda"
}

resource "random_uuid" "lambda_src_hash" {
  keepers = {
    for filename in setunion(
      fileset(local.lambda_src_path, "*.py"),
      fileset(local.lambda_src_path, "requirements.txt")
    ) :
    filename => filemd5("${local.lambda_src_path}/${filename}")
  }
}

resource "null_resource" "install_dependencies" {
  provisioner "local-exec" {
    command = "pip install -r ${local.lambda_src_path}/requirements.txt -t ${local.lambda_src_path}"
  }

  triggers = {
    dependencies_versions = filemd5("${local.lambda_src_path}/requirements.txt")
  }
}

resource "aws_iam_role" "resiliency_lambda_role" {
  name               = "resiliency_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust_policy.json
}

resource "aws_iam_policy" "resiliency_lambda_policy" {
  name   = "resiliency_lambda_policy"
  policy = file("lambda_policy.json")
}

resource "aws_iam_role_policy_attachment" "test-attach" {
  role       = aws_iam_role.resiliency_lambda_role.name
  policy_arn = aws_iam_policy.resiliency_lambda_policy.arn
}

resource "aws_lambda_function" "resiliency_lambda" {
  function_name = "resiliency_lambda-${var.owner}"
  description   = "Resiliency Testing Lambda for ${var.owner}"
  role          = aws_iam_role.resiliency_lambda_role.arn
  runtime       = "python3.8"
  handler       = "handler.handler"
  memory_size   = 1024
  timeout       = 600

  s3_bucket = var.resiliency_bucket
  s3_key    = aws_s3_object.lambda_file.id

  source_code_hash = data.archive_file.lambda_source_package.output_base64sha256
  environment {
    variables = {
      LOG_LEVEL = var.lambda_log_level
    }
  }
  lifecycle {
    ignore_changes = [environment]
  }

  depends_on = [aws_s3_object.lambda_file]
}
