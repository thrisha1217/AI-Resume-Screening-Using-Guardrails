#!/bin/bash
set -e

# ── System update ──────────────────────────────────────────────────────────────
apt-get update -y
apt-get upgrade -y

# ── Install Docker ─────────────────────────────────────────────────────────────
apt-get install -y ca-certificates curl gnupg lsb-release git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# ── Add ubuntu user to docker group ───────────────────────────────────────────
usermod -aG docker ubuntu

# ── Start Docker ───────────────────────────────────────────────────────────────
systemctl enable docker
systemctl start docker

# ── Clone / copy app (replace with your repo URL) ─────────────────────────────
mkdir -p /opt/resume-screening
cd /opt/resume-screening

# If using git:
# git clone https://github.com/YOUR_USERNAME/resume-screening.git .

# ── Start application ──────────────────────────────────────────────────────────
# docker compose up -d --build

# ── Install Certbot for HTTPS (Let's Encrypt) ─────────────────────────────────
apt-get install -y certbot python3-certbot-nginx

# Log completion
echo "User data script completed at $(date)" >> /var/log/user_data.log
