# End-to-End DevOps Automation Platform

This repository is a complete starter for an automated DevOps pipeline using:

- GitHub
- Terraform (AWS infrastructure)
- Ansible (server configuration)
- Jenkins (CI/CD)
- Docker (containerization)
- Kubernetes (orchestration)

The app is intentionally simple. The focus is pipeline automation and repeatable delivery.

## 1. Architecture

Terraform provisions:
- `jenkins` EC2 instance
- `k8s-master` EC2 instance
- `k8s-worker-1` EC2 instance
- VPC, subnet, internet gateway, route table, and security group

Ansible configures:
- Jenkins host with Java, Docker, Jenkins
- Kubernetes hosts with Docker + k3s (master/worker)

Jenkins pipeline:
- Checks out code
- Runs tests
- Builds Docker image
- Pushes image to Docker Hub (or your registry)
- Deploys to Kubernetes using `kubectl`

## 2. Prerequisites (What You Must Do)

You must do these things manually:

1. Create an AWS account and IAM user with EC2/VPC permissions.
2. Create or choose an AWS key pair in your target region.
3. Create a Docker Hub account (or use another registry).
4. Create a GitHub repository and push this project.

Local machine requirements:

- Terraform >= 1.6
- Ansible >= 2.14
- AWS CLI configured (`aws configure`)
- SSH client
- Git

## 3. Quick Start Order

1. Configure Terraform variables:
   - Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars`
   - Fill your values
2. Provision infrastructure:
   - `cd terraform`
   - `terraform init`
   - `terraform plan`
   - `terraform apply`
3. Build Ansible inventory from Terraform outputs:
   - `cd ..`
   - `pwsh ./scripts/generate-inventory.ps1`
4. Configure servers:
   - `ansible-playbook -i ansible/inventory.ini ansible/site.yml`
5. Open Jenkins:
   - `http://<jenkins_public_ip>:8080`
6. Configure Jenkins credentials and pipeline job (see `docs/jenkins-setup.md`)
7. Push code to GitHub and run pipeline.

## 4. Files and Folders

- `terraform/` AWS infrastructure as code
- `ansible/` server configuration playbooks
- `jenkins/Jenkinsfile` CI/CD pipeline
- `app/` sample Python app + tests + Dockerfile
- `k8s/` Kubernetes manifests
- `scripts/` helper scripts
- `docs/` manual setup guides

## 5. Important Notes

- Keep AWS credentials out of git.
- Restrict `0.0.0.0/0` SSH in production; this starter is for learning/demo.
- Rotate secrets and use Jenkins credentials, never hardcode passwords/tokens.

webhook test Sat Mar  7 22:13:21 UTC 2026
