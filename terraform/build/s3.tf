resource "aws_s3_bucket" "codepipeline_bucket" {
  bucket = "resiliency-package-build-bucket"
}

resource "aws_s3_bucket_acl" "codepipeline_bucket_acl" {
  bucket = aws_s3_bucket.codepipeline_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket" "backend_bucket" {
  bucket = "resiliency-terraform-backend-bucket"
}

resource "aws_s3_bucket_acl" "backend_bucket_acl" {
  bucket = aws_s3_bucket.backend_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "backend_bucket_versioning" {
  bucket = aws_s3_bucket.backend_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backend_bucket_sse" {
  bucket = aws_s3_bucket.backend_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}