terraform {
  backend "s3" {
    dynamodb_table = "resiliency_terraform_state"
    bucket         = "resiliency-terraform-backend-bucket"
    region         = "us-east-1"
    key            = "terraform.tfstate"
  }
}


provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Team = "ResiliencyTeam",
    }
  }
}
