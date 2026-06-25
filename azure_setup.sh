#!/bin/bash
set -e
echo "======================================"
echo " Resume Screening - Azure VM Setup"
echo "======================================"

# 1. Install Docker
echo "[1/5] Installing Docker..."
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker azureuser
sudo systemctl enable docker
sudo systemctl start docker

# 2. Install docker compose plugin
echo "[2/5] Installing Docker Compose..."
sudo apt-get install -y docker-compose-plugin

# 3. Create app directory
echo "[3/5] Creating app directory..."
sudo mkdir -p /opt/resume-screening
sudo chown azureuser:azureuser /opt/resume-screening

echo "[4/5] Docker installed successfully!"
docker --version
docker compose version

echo "[5/5] VM is ready for deployment!"
echo "======================================"
echo " Setup Complete!"
echo "======================================"
