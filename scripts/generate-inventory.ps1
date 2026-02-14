param(
  [string]$TerraformDir = ".\terraform",
  [string]$OutputPath = ".\ansible\inventory.ini",
  [string]$SshKeyPath = "~/.ssh/your-key.pem"
)

$jenkinsIp = terraform -chdir=$TerraformDir output -raw jenkins_public_ip
$masterIp = terraform -chdir=$TerraformDir output -raw k8s_master_public_ip
$workerIp = terraform -chdir=$TerraformDir output -raw k8s_worker_1_public_ip

$content = @"
[jenkins]
jenkins ansible_host=$jenkinsIp ansible_user=ubuntu

[k8s_master]
k8s-master ansible_host=$masterIp ansible_user=ubuntu

[k8s_workers]
k8s-worker-1 ansible_host=$workerIp ansible_user=ubuntu

[all:vars]
ansible_ssh_private_key_file=$SshKeyPath
"@

$content | Set-Content -Path $OutputPath -Encoding ASCII
Write-Host "Inventory generated at $OutputPath"

