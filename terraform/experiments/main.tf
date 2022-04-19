resource "aws_s3_bucket" "experiments_bucket" {
  bucket = "resiliency-testing-experiments"
}    

resource "aws_s3_bucket_acl" "experiments_bucket_acl" {
  bucket = aws_s3_bucket.experiments_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "experiments_bucket_versioning" {
  bucket = aws_s3_bucket.experiments_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "experiments_bucket_sse" {
  bucket = aws_s3_bucket.experiments_bucket.id

    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
}

resource "aws_s3_object" "experiment_files" {
  for_each = fileset("./experiments/", "**")
  bucket = aws_s3_bucket.experiments_bucket.id
  key = each.value
  source = "./experiments/${each.value}"
  etag = filemd5("./experiments/${each.value}")
  content_type = "application/x-yaml"
}
