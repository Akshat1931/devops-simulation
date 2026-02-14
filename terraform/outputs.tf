output "jenkins_public_ip" {
  value = aws_instance.nodes["jenkins"].public_ip
}

output "k8s_master_public_ip" {
  value = aws_instance.nodes["k8s_master"].public_ip
}

output "k8s_worker_1_public_ip" {
  value = aws_instance.nodes["k8s_worker_1"].public_ip
}

output "jenkins_private_ip" {
  value = aws_instance.nodes["jenkins"].private_ip
}

output "k8s_master_private_ip" {
  value = aws_instance.nodes["k8s_master"].private_ip
}

output "k8s_worker_1_private_ip" {
  value = aws_instance.nodes["k8s_worker_1"].private_ip
}

