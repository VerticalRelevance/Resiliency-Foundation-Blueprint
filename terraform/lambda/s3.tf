resource "aws_s3_object" "lambda_file" {
  bucket     = var.resiliency_bucket
  key        = "chaos_resiliency_lambda-${var.owner}.zip"
  source     = data.archive_file.lambda_source_package.output_path
  depends_on = [data.archive_file.lambda_source_package]
  kms_key_id = aws_kms_key.s3_key.arn
}
