resource "aws_kms_key" "s3_key" {
  description             = "Customer managed KMS key to encrypt S3 resources"
  deletion_window_in_days = 14
  enable_key_rotation     = true
}
