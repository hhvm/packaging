provider "random" {}
module "networking" {
  source                                      = "cn-terraform/networking/aws"
  version                                     = "2.0.15"
  name_prefix                                 = "nexus-${terraform.workspace}"
  vpc_cidr_block                              = "192.168.0.0/16"
  availability_zones                          = ["us-west-2a", "us-west-2b", "us-west-2c", "us-west-2d"]
  public_subnets_cidrs_per_availability_zone  = ["192.168.0.0/19", "192.168.32.0/19", "192.168.64.0/19", "192.168.96.0/19"]
  private_subnets_cidrs_per_availability_zone = ["192.168.128.0/19", "192.168.160.0/19", "192.168.192.0/19", "192.168.224.0/19"]
  single_nat                                  = true
}

module "ecs-fargate" {
  source  = "cn-terraform/ecs-fargate/aws"
  version = "2.0.43"

  name_prefix                       = "nexus-${terraform.workspace}"
  vpc_id                            = module.networking.vpc_id
  public_subnets_ids                = module.networking.public_subnets_ids
  private_subnets_ids               = module.networking.private_subnets_ids
  container_name                    = "nexus-${terraform.workspace}"
  container_image                   = "sonatype/nexus3"
  container_cpu                     = 4096
  container_memory                  = 8192
  container_memory_reservation      = null
  health_check_grace_period_seconds = 120

  enable_execute_command = true
  ecs_task_execution_role_custom_policies = [jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ],
        "Resource" : "*"
      }
    ]
  })]

  enable_s3_logs = false

  default_certificate_arn = "arn:aws:acm:us-west-2:223121549624:certificate/8f845b56-937f-49b8-adf4-64b69a3caf57"

  port_mappings = [
    {
      containerPort = 8081
      hostPort      = 8081
      protocol      = "tcp"
    }
  ]

  lb_https_ports = {
    forward_https_to_http = {
      listener_port         = 443
      target_group_port     = 8081
      target_group_protocol = "HTTP"
    }
  }

  lb_http_ports = {
    default_http = {
      listener_port     = 80
      target_group_port = 8081
    }
  }

  mount_points = [
    {
      sourceVolume  = "nexus-data"
      containerPath = "/nexus-data"
      readOnly      = false
    }
  ]

  volumes = [
    {
      host_path                   = null
      name                        = "nexus-data"
      docker_volume_configuration = []
      efs_volume_configuration = [
        {
          file_system_id          = module.efs.id
          root_directory          = "/"
          transit_encryption      = null
          transit_encryption_port = null
          authorization_config    = []
        }
      ]
    }
  ]

  log_configuration = {
    logDriver = "awslogs"
    options = {
      "awslogs-region"        = "us-west-2"
      "awslogs-group"         = "/ecs/service/nexus-${terraform.workspace}"
      "awslogs-stream-prefix" = "ecs"
    }
    secretOptions = null
  }

}

module "aws_cw_logs" {
  source    = "cn-terraform/cloudwatch-logs/aws"
  version   = "1.0.10"
  logs_path = "/ecs/service/nexus-${terraform.workspace}"
}

module "efs" {
  source  = "cloudposse/efs/aws"
  version = "0.32.7"

  stage                      = terraform.workspace
  name                       = "nexus"
  region                     = "us-west-2"
  vpc_id                     = module.networking.vpc_id
  subnets                    = module.networking.public_subnets_ids
  allowed_security_group_ids = [module.ecs-fargate.ecs_tasks_sg_id]
}
