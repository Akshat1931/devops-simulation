# Verify and Troubleshoot

## Verify infra

```bash
cd terraform
terraform output
```

You should see public/private IP outputs for all nodes.

## Verify Ansible connectivity

```bash
ansible -i ansible/inventory.ini all -m ping
```

## Verify Jenkins service

On Jenkins node:

```bash
sudo systemctl status jenkins
sudo systemctl status docker
```

## Verify k3s cluster

On k8s master:

```bash
sudo k3s kubectl get nodes -o wide
sudo k3s kubectl get pods -A
```

## Verify deployed app

```bash
kubectl get deploy,svc,pods
curl http://<k8s_node_public_ip>:30080/
```

Expected response:

```json
{"service":"devops-platform-app","status":"ok"}
```

## Common issues

1. SSH timeout:
   - Check security group inbound for port 22 from your current IP.
2. Jenkins cannot run Docker:
   - Ensure `jenkins` user is in `docker` group.
   - Restart Jenkins: `sudo systemctl restart jenkins`
3. Worker not joining cluster:
   - Check port `6443` is open between nodes.
   - Re-run `ansible-playbook ansible/playbooks/k3s-worker.yml`
4. Jenkins deploy stage fails with kubectl auth:
   - Recreate `kubeconfig-file` credential.
   - Ensure server IP in kubeconfig is reachable from Jenkins host.

