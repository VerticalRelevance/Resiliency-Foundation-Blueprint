resource "aws_kms_key" "vr_ca_dev_key" {
  description = "vr-ca-dev repository key"
}

resource "aws_codeartifact_domain" "vr_ca_dev_domain" {
  domain         = "vr-ca-dev"
  encryption_key = aws_kms_key.vr_ca_dev_key.arn
}

resource "aws_codeartifact_repository" "pypi_store" {
  repository = "pypi-store"
  domain     = aws_codeartifact_domain.vr_ca_dev_domain.domain

  external_connections {
    external_connection_name = "public:pypi"
  }
}

resource "aws_codeartifact_repository" "vr_ca_dev" {
  repository = "vr-ca-dev"
  domain     = aws_codeartifact_domain.vr_ca_dev_domain.domain

  upstream {
    repository_name = aws_codeartifact_repository.pypi_store.repository
  }
}


resource "aws_codeartifact_domain_permissions_policy" "vr_ca_dev_policy_doc" {
  domain          = aws_codeartifact_domain.vr_ca_dev_domain.domain
  policy_document = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
          "Action": [
            "codeartifact:PublishPackageVersion"
            ],
          "Effect": "Allow",
          "Principal": {
            "AWS": "${aws_iam_role.resiliencyvr_codebuild_package_role.arn}"
            },
          "Resource": "*"
        },
        {
          "Action": [
            "codeartifact:DescribePackageVersion",
            "codeartifact:DescribeRepository",
            "codeartifact:GetPackageVersionReadme",
            "codeartifact:GetRepositoryEndpoint",
            "codeartifact:ListPackages",
            "codeartifact:ListPackageVersions",
            "codeartifact:ListPackageVersionAssets",
            "codeartifact:ListPackageVersionDependencies",
            "codeartifact:ReadFromRepository"
            ],
          "Effect": "Allow",
          "Principal": {
            "AWS": "${aws_iam_role.resiliencyvr_codebuild_lambda_role.arn}"
            },
          "Resource": "*"
        }
      ]
    }
EOF
}
