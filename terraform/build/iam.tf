resource "aws_iam_role" "codepipeline_role" {
  name = "resiliencyvr-package-build-pipeline-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codepipeline.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  name = "codepipeline_policy"
  role = aws_iam_role.codepipeline_role.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect":"Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:GetBucketVersioning",
        "s3:PutObjectAcl",
        "s3:PutObject"
      ],
      "Resource": [
        "${aws_s3_bucket.codepipeline_bucket.arn}",
        "${aws_s3_bucket.codepipeline_bucket.arn}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "codestar-connections:UseConnection"
      ],
      "Resource": "${data.aws_codestarconnections_connection.github.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "codebuild:BatchGetBuilds",
        "codebuild:StartBuild"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role" "resiliencyvr_codebuild_package_role" {
  name = "resiliencyvr-codebuild-package-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "resiliencyvr_codebuild_package_policy" {
  role = aws_iam_role.resiliencyvr_codebuild_package_role.name

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    },
    { "Effect": "Allow",
      "Action": [
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
      ],
      "Resource": [
          "${aws_codeartifact_repository.res_ca_dev.arn}",
          "${aws_codeartifact_domain.res_ca_dev_domain.arn}/*",
          "${aws_codeartifact_domain.res_ca_dev_domain.arn}"  
          
      ]
    },
    { "Effect": "Allow",
      "Action": "sts:GetServiceBearerToken",
      "Resource": "*",
      "Condition": {
          "StringEquals": {
              "sts:AWSServiceName": "codeartifact.amazonaws.com"
            }
        }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "${aws_s3_bucket.codepipeline_bucket.arn}",
        "${aws_s3_bucket.codepipeline_bucket.arn}/*"
      ]
    }
  ]
}
POLICY
}



resource "aws_iam_role" "resiliencyvr_codebuild_lambda_role" {
  name = "resiliencyvr-codebuild-lambda-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "resiliencyvr_codebuild_lambda_policy" {
  role = aws_iam_role.resiliencyvr_codebuild_lambda_role.name

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    },
    { "Effect": "Allow",
      "Action": [
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
      ],
      "Resource": [
          "${aws_codeartifact_repository.res_ca_dev.arn}",
          "${aws_codeartifact_domain.res_ca_dev_domain.arn}/*",
          "${aws_codeartifact_domain.res_ca_dev_domain.arn}"  
          
      ]
    },
    { "Effect": "Allow",
      "Action": "sts:GetServiceBearerToken",
      "Resource": "*",
      "Condition": {
          "StringEquals": {
              "sts:AWSServiceName": "codeartifact.amazonaws.com"
            }
        }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "${aws_s3_bucket.codepipeline_bucket.arn}",
        "${aws_s3_bucket.codepipeline_bucket.arn}/*",
        "${aws_s3_bucket.backend_bucket.arn}",
        "${aws_s3_bucket.backend_bucket.arn}/*"
      ]
    },
      {
      "Effect": "Allow",
      "Action": [
        "dynamodb:*"
      ],
      "Resource": [
        "${aws_dynamodb_table.terraform-backend.arn}"
      ]
    },
      {
      "Effect": "Allow",
      "Action": [
        "kms:*"
      ],
      "Resource": [
        "*"
      ]
    },
      {
      "Effect": "Allow",
      "Action": [
        "iam:*"
      ],
      "Resource": "*"
    },
      {
      "Effect": "Allow",
      "Action": [
        "lambda:*"
      ],
      "Resource": "*"
    }
  ]
}
POLICY
}
