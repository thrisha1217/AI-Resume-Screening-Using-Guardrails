variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"  # Mumbai — closest to India
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "resume-screening"
}

variable "instance_type" {
  description = "EC2 instance type (t3.xlarge = 4vCPU/16GB recommended for Qwen2.5:3B)"
  type        = string
  default     = "t3.xlarge"
}

variable "key_pair_name" {
  description = "AWS EC2 key pair name (must exist in your AWS account)"
  type        = string
}

variable "domain_name" {
  description = "Full domain name e.g. resume.yourdomain.com"
  type        = string
}

variable "hosted_zone_name" {
  description = "Route53 hosted zone name e.g. yourdomain.com"
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed for SSH (use your IP: x.x.x.x/32)"
  type        = string
  default     = "0.0.0.0/0"  # Restrict this in production
}
