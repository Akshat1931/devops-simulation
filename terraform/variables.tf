variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "devops-platform"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "aws_profile" {
  description = "AWS CLI profile name"
  type        = string
  default     = "default"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.10.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.10.1.0/24"
}

variable "availability_zone" {
  description = "Availability zone"
  type        = string
}

variable "ami_id" {
  description = "Ubuntu AMI ID for target region"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "key_name" {
  description = "Existing EC2 key pair name"
  type        = string
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR format for SSH access (example: 1.2.3.4/32)"
  type        = string
}

