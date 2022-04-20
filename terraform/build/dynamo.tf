resource "aws_dynamodb_table" "terraform-backend" {
  name           = "resiliency_terraform_state"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
  tags = {
    "Name" = "DynamoDB Terraform State Lock Table for Resiliency Testing"
  }
}