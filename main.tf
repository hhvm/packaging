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
module "base-network" {
  source                                      = "cn-terraform/networking/aws"
  name_prefix                                 = "${terraform.workspace}-networking-nexus"
  vpc_cidr_block                              = "192.168.0.0/16"
  availability_zones                          = ["us-west-2"]
  public_subnets_cidrs_per_availability_zone  = ["192.168.0.0/19"]
  private_subnets_cidrs_per_availability_zone = ["192.168.128.0/19"]
}

module "nexus" {
  source              = "cn-terraform/nexus/aws"
  name_prefix         = "${terraform.workspace}-nexus"
  region              = "us-west-2"
  vpc_id              = module.base-network.vpc_id
  availability_zones  = module.base-network.availability_zones
  public_subnets_ids  = module.base-network.public_subnets_ids
  private_subnets_ids = module.base-network.private_subnets_ids
}
