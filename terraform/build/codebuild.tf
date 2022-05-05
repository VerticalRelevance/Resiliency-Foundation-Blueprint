resource "aws_codebuild_project" "resiliencyvr_codebuild" {
  name          = "resiliencyvr-package-codebuild"
  description   = "Builds the resiliencyvr package"
  build_timeout = "5"
  service_role  = aws_iam_role.resiliencyvr_codebuild_package_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type         = "LINUX_CONTAINER"
  }

  logs_config {
    s3_logs {
      status   = "ENABLED"
      location = "${aws_s3_bucket.codepipeline_bucket.id}/build-log"
    }
  }

  source {
    buildspec    = data.template_file.resiliencyvr_package_buildspec.rendered
    insecure_ssl = false
    type         = "CODEPIPELINE"
  }

}

resource "aws_codebuild_project" "lambda_codebuild" {
  name          = "resiliency-lambda-codebuild"
  description   = "Builds the resiliency lambda to run VR Resiliency tests"
  build_timeout = "5"
  service_role  = aws_iam_role.resiliencyvr_codebuild_lambda_role.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type         = "LINUX_CONTAINER"

    environment_variable {
      name  = "TF_COMMAND"
      value = ""
    }

    environment_variable {
      name  = "TF_VAR_resiliency_bucket"
      value = aws_s3_bucket.codepipeline_bucket.id
    }

  }

  logs_config {
    s3_logs {
      status   = "ENABLED"
      location = "${aws_s3_bucket.codepipeline_bucket.id}/build-log"
    }
  }

  source {
    buildspec    = data.template_file.lambda_buildspec.rendered
    insecure_ssl = false
    type         = "CODEPIPELINE"
  }

}