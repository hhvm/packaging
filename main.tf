terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.17.0"
    }
  }
  backend "s3" {
    region = "us-west-2"
    bucket = "hhvm-packging-terraform-state"
    key = "hhvm-packging/tfstate"
    dynamodb_table = "hhvm-packging-tfstate"
  }
}
