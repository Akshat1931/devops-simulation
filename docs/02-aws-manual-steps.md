# AWS Manual Steps

You must perform these manually in AWS console.

## 1. Create IAM user for Terraform

Grant enough permissions for:
- EC2
- VPC
- Security Groups
- Route tables
- Subnets

For learning/demo, `AdministratorAccess` is easiest. For production, use least privilege.

## 2. Create EC2 key pair

1. Go to EC2 -> Key Pairs -> Create key pair
2. Name it (example: `devops-platform-key`)
3. Download `.pem`
4. Store securely, e.g. `~/.ssh/devops-platform-key.pem`
5. Fix permissions:

```bash
chmod 400 ~/.ssh/devops-platform-key.pem
```

## 3. Find Ubuntu AMI ID

Get AMI for your exact region (Ubuntu 22.04 LTS recommended).  
Use AWS console or:

```bash
aws ssm get-parameters --names /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id --query "Parameters[0].Value" --output text --region us-east-1
```

## 4. Get your public IP for SSH allowlist

```bash
curl ifconfig.me
```

Use `/32` suffix in Terraform, e.g. `203.0.113.10/32`.

