# Jenkins Setup

## 1. Get initial admin password

SSH into Jenkins EC2:

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Open `http://<jenkins_public_ip>:8080` and complete setup wizard.

## 2. Install required Jenkins plugins

- Pipeline
- Git
- Credentials Binding
- Docker Pipeline (optional but useful)

## 3. Install kubectl on Jenkins node

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
kubectl version --client
```

## 4. Prepare kubeconfig credential

On k8s master:

```bash
sudo cat /etc/rancher/k3s/k3s.yaml
```

Replace `127.0.0.1` with your k8s master public IP in that file copy.  
Store it in Jenkins:

- Manage Jenkins -> Credentials -> System -> Global credentials
- Add secret file
- ID: `kubeconfig-file`

## 5. Add Docker Hub credential

- Type: Username with password
- ID: `dockerhub-creds`
- Username: your Docker Hub user
- Password: Docker Hub password or token

## 6. Create pipeline job

1. New Item -> Pipeline
2. Pipeline script from SCM
3. SCM: Git
4. Repo URL: your GitHub repo
5. Script Path: `jenkins/Jenkinsfile`

## 7. Update image repository in Jenkinsfile

Edit `jenkins/Jenkinsfile`:
- Set `IMAGE_REPO` to your Docker Hub repo:
  - `your_user/devops-platform-app`

