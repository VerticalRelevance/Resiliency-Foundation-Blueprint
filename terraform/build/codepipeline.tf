resource "aws_codepipeline" "resiliencyvr_build" {
  name     = "resiliencyvr-package-build"
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    location = aws_s3_bucket.codepipeline_bucket.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = data.aws_codestarconnections_connection.vr_github.arn
        FullRepositoryId = var.repository_id
        BranchName       = var.repository_branch
      }
    }
  }

  stage {
    name = "Build"

    action {
      name             = "Build"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.resiliencyvr_codebuild.name
      }
    }
  }
}

resource "aws_codepipeline" "lambda_build" {
  name     = "resiliency-lambda-build-pipeline"
  role_arn = aws_iam_role.codepipeline_role.arn

  artifact_store {
    location = aws_s3_bucket.codepipeline_bucket.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = data.aws_codestarconnections_connection.vr_github.arn
        FullRepositoryId = var.repository_id
        BranchName       = var.repository_branch
      }
    }
  }


  stage {
    name = "Plan"

    action {
      name             = "Plan"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["plan_output"]
      version          = "1"

      configuration = {
        ProjectName          = aws_codebuild_project.lambda_codebuild.name
        EnvironmentVariables = "[{\"name\":\"TF_COMMAND\",\"value\":\"plan\"}]"
      }
    }
  }

  stage {
    name = "Approval"

    action {
      name      = "Approval"
      category  = "Approval"
      owner     = "AWS"
      provider  = "Manual"
      version   = "1"

      configuration = {
        CustomData = "Continue with this plan?"
      }
    }
  }
  stage {
    name = "Apply"

    action {
      name             = "Apply"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      version          = "1"

      configuration = {
        ProjectName = aws_codebuild_project.lambda_codebuild.name
        EnvironmentVariables = "[{\"name\":\"TF_COMMAND\",\"value\":\"apply -auto-approve\"}]"
      }
    }
  }
}
