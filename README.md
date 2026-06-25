# Resume Screening System

AI-powered resume screening with LLM-based candidate evaluation, skill matching, and guardrails safety.

---

## Architecture

```
Internet
    │
    ▼
Route53 DNS (resume.yourdomain.com)
    │
    ▼
EC2 Instance (t3.xlarge)
    │
    ├── Nginx (port 80/443)
    │       ├── /          → React Frontend (built static files)
    │       └── /api/*     → FastAPI Backend (port 8000)
    │
    ├── FastAPI Backend (port 8000)
    │       └── Qwen2.5:3B via Ollama (port 11434)
    │
    └── Ollama (port 11434)
            └── qwen2.5:3b model
```

---

## Local Development

```bash
# Start backend
python -m uvicorn api:app --host 0.0.0.0 --port 8000

# Start frontend
cd frontend && npm run dev
# Open http://localhost:5173
```

---

## Docker (Local)

```bash
# Build and start all services
docker compose up --build

# Open http://localhost
```

---

## AWS Deployment — Step by Step

### Prerequisites
- AWS account with CLI configured (`aws configure`)
- Terraform installed (`terraform -v`)
- A domain registered in Route53 (or transfer your domain)
- An EC2 key pair created in AWS console

### Step 1 — Configure Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### Step 2 — Provision AWS Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
# Note the output: public_ip and app_url
```

This creates:
- VPC + subnet + internet gateway
- Security group (ports 80, 443, 22)
- EC2 t3.xlarge instance (Ubuntu 22.04)
- Elastic IP
- Route53 A record → your domain

### Step 3 — Copy Code to EC2

```bash
# SSH into the instance
ssh -i your-key.pem ubuntu@<PUBLIC_IP>

# On the EC2 instance:
sudo mkdir -p /opt/resume-screening
sudo chown ubuntu:ubuntu /opt/resume-screening

# Option A: Clone from GitHub
git clone https://github.com/YOUR_USERNAME/resume-screening.git /opt/resume-screening

# Option B: Copy files via SCP (from your local machine)
scp -i your-key.pem -r . ubuntu@<PUBLIC_IP>:/opt/resume-screening/
```

### Step 4 — Deploy

```bash
# On EC2:
cd /opt/resume-screening
bash deploy.sh
```

This will:
1. Build Docker images
2. Start all containers (Ollama, Backend, Frontend/Nginx)
3. Pull the qwen2.5:3b model (~2GB)
4. Run health checks

### Step 5 — Enable HTTPS (Let's Encrypt)

```bash
# On EC2 (after DNS propagates ~5 min):
sudo certbot --nginx -d resume.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

Then update `nginx.conf` to redirect HTTP → HTTPS (uncomment the redirect block).

---

## CI/CD (GitHub Actions)

Add these secrets to your GitHub repository:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `EC2_HOST` | EC2 public IP or domain |
| `EC2_SSH_KEY` | Contents of your .pem file |

Every push to `main` will automatically build and deploy.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama server URL |
| `VITE_API_URL` | `/api` | Frontend API base URL |
| `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION` | `python` | Fix protobuf conflict |

---

## Useful Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f ollama

# Restart a service
docker compose restart backend

# Check running containers
docker compose ps

# Stop everything
docker compose down

# Pull new model
docker compose exec ollama ollama pull qwen2.5:3b

# SSH tunnel to access backend directly
ssh -L 8000:localhost:8000 -i your-key.pem ubuntu@<PUBLIC_IP>
```

---

## Cost Estimate (AWS ap-south-1)

| Resource | Cost/month |
|---|---|
| EC2 t3.xlarge | ~$60 |
| EBS 50GB gp3 | ~$4 |
| Elastic IP | ~$3.6 |
| Route53 hosted zone | ~$0.5 |
| Data transfer | ~$1 |
| **Total** | **~$69/month** |

> Use `t3.large` (2vCPU/8GB) to reduce cost to ~$45/month — may be slower for LLM inference.
