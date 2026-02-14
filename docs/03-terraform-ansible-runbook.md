# Terraform + Ansible Runbook

## 1. Configure Terraform variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` values:
- `aws_region`
- `availability_zone`
- `ami_id`
- `key_name`
- `my_ip_cidr`

## 2. Provision infrastructure

```bash
terraform init
terraform plan
terraform apply
```

## 3. Generate Ansible inventory

From repo root:

```bash
pwsh ./scripts/generate-inventory.ps1 -SshKeyPath "~/.ssh/devops-platform-key.pem"
```

Or in WSL:

```bash
bash ./scripts/generate-inventory.sh ./terraform ./ansible/inventory.ini ~/.ssh/devops-platform-key.pem
```

## 4. Configure all servers

```bash
ansible-playbook -i ansible/inventory.ini ansible/site.yml
```

## 5. Confirm services

1. Jenkins:
   - `http://<jenkins_public_ip>:8080`
2. Kubernetes from master:
   - `sudo k3s kubectl get nodes`

