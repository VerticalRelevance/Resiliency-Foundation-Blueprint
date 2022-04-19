data "aws_codestarconnections_connection" "vr_github" {
  arn = var.codestar_connection_arn
}

data "template_file" "resiliencyvr_package_buildspec" {
  template = file("${path.module}/buildspec-resiliencyvr.yml")
  vars = {
    DOMAIN_NAME = var.domain_name
    OWNER       = var.owner
    REPO_NAME   = var.repo_name
  }
}

data "template_file" "lambda_buildspec" {
  template = file("${path.module}/buildspec-lambda.yml")
  vars = {
    DOMAIN_NAME = var.domain_name
    OWNER       = var.owner
    REPO_NAME   = var.repo_name
  }
}