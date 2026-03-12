# Neural Time Machine DevOps Pipeline

This repository deploys the Neural Time Machine application through an end-to-end DevOps pipeline on AWS.

## Stack

- GitHub for source control and webhook trigger
- Terraform for AWS infrastructure
- Ansible for server configuration
- Jenkins for CI/CD orchestration
- Docker for image build and packaging
- Kubernetes `k3s` for deployment and rollout management
- Streamlit + Python for the application

## Application

Neural Time Machine analyzes synthetic time-based production logs, detects change points, identifies likely root causes, and can generate an optional Gemini-powered incident narrative.

Main app modules:

- `app/dashboard.py` Streamlit dashboard
- `src/detect/` change-point detection
- `src/explain/` root-cause analysis and Gemini client
- `src/utils/` synthetic data generation and preparation

## CI/CD Flow

1. Developer pushes code to GitHub
2. Jenkins detects the commit
3. Jenkins runs a Python sanity check
4. Jenkins builds a Docker image
5. Jenkins pushes the image to Docker Hub
6. Jenkins pauses at a manual approval gate
7. On approval, Jenkins deploys the image to Kubernetes
8. Jenkins checks rollout health
9. If rollout fails, Jenkins automatically rolls back to the previous stable revision

## Production-style Features

### Approval Gate

The pipeline pauses after image push and waits for manual approval before deployment.

Defined in:

- `jenkins/Jenkinsfile`

### Automatic Rollback

If `kubectl rollout status` fails after deployment, Jenkins runs:

```bash
kubectl rollout undo deployment/devops-platform-app
```

This restores the last working Kubernetes deployment revision.

## Kubernetes App Access

The app is exposed through a NodePort service:

- App URL: `http://<k8s-master-public-ip>:30080/`
- Streamlit container port: `8501`

## Gemini Key Setup

The app can run without Gemini. If no Gemini key is set, it falls back to a built-in heuristic explanation.

To enable Gemini in Kubernetes, create a secret on the cluster:

```bash
kubectl create secret generic neural-time-machine-secrets \
  --from-literal=GOOGLE_API_KEY="<your-gemini-api-key>"
```

The deployment reads:

- `GOOGLE_API_KEY` from Kubernetes secret `neural-time-machine-secrets`
- `GEMINI_MODEL_NAME` from deployment environment

If you need to update the key later:

```bash
kubectl delete secret neural-time-machine-secrets
kubectl create secret generic neural-time-machine-secrets \
  --from-literal=GOOGLE_API_KEY="<your-gemini-api-key>"
kubectl rollout restart deployment/devops-platform-app
```

## Important Files

- `terraform/` AWS infrastructure
- `ansible/` Jenkins and k3s setup
- `jenkins/Jenkinsfile` CI/CD pipeline
- `app/Dockerfile` app container build
- `k8s/deployment.yaml` deployment and rollback-ready rollout config
- `k8s/service.yaml` app exposure
- `requirements.txt` Python dependencies

## Local Sanity Check

Build the container locally:

```bash
docker build -t neural-time-machine-dev -f app/Dockerfile .
```

Run the app locally:

```bash
docker run --rm -p 8501:8501 neural-time-machine-dev
```

Then open:

```text
http://localhost:8501
```

## Deployment Notes

- Keep `.env` out of git
- Store API keys as Jenkins credentials or Kubernetes secrets
- If EC2 instances are stopped and restarted, public IPs may change
- Update Jenkins URL and GitHub webhook when Jenkins public IP changes
