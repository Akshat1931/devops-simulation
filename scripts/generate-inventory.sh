#!/usr/bin/env bash
set -euo pipefail

TERRAFORM_DIR="${1:-./terraform}"
OUTPUT_PATH="${2:-./ansible/inventory.ini}"
SSH_KEY_PATH="${3:-~/.ssh/your-key.pem}"

jenkins_ip="$(terraform -chdir="$TERRAFORM_DIR" output -raw jenkins_public_ip)"
master_ip="$(terraform -chdir="$TERRAFORM_DIR" output -raw k8s_master_public_ip)"
worker_ip="$(terraform -chdir="$TERRAFORM_DIR" output -raw k8s_worker_1_public_ip)"

cat > "$OUTPUT_PATH" <<EOF
[jenkins]
jenkins ansible_host=$jenkins_ip ansible_user=ubuntu

[k8s_master]
k8s-master ansible_host=$master_ip ansible_user=ubuntu

[k8s_workers]
k8s-worker-1 ansible_host=$worker_ip ansible_user=ubuntu

[all:vars]
ansible_ssh_private_key_file=$SSH_KEY_PATH
EOF

echo "Inventory generated at $OUTPUT_PATH"

