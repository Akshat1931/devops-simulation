# Prerequisites for Your Current Setup

You currently have:
- Docker
- WSL
- Git

Install the remaining required tools inside WSL (Ubuntu recommended).

## 1. Install Terraform

```bash
sudo apt-get update
sudo apt-get install -y gnupg software-properties-common curl
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update
sudo apt-get install -y terraform
terraform -version
```

## 2. Install AWS CLI

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

## 3. Configure AWS credentials

```bash
aws configure
```

Provide:
- Access key ID
- Secret access key
- Region (example: `us-east-1`)
- Output format: `json`

## 4. Install Ansible

```bash
sudo apt-get update
sudo apt-get install -y ansible
ansible --version
```

## 5. Verify Docker in WSL

```bash
docker version
docker run --rm hello-world
```

If Docker command fails in WSL, enable WSL integration in Docker Desktop settings.

