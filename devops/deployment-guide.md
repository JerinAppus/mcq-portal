# MCQ Battle Platform: Linux Administration & Deployment Guide

This guide provides step-by-step instructions to deploy, secure, backup, and monitor the MCQ Battle Platform on an AWS EC2 instance running Ubuntu Server (20.04 or 22.04 LTS).

---

## Table of Contents
1. [Prerequisites & EC2 Setup](#1-prerequisites--ec2-setup)
2. [Environment and Dependency Installation](#2-environment-and-dependency-installation)
3. [Nginx Reverse Proxy Configuration](#3-nginx-reverse-proxy-configuration)
4. [Systemd Service Management](#4-systemd-service-management)
5. [SSH Hardening & Fail2ban Security](#5-ssh-hardening--fail2ban-security)
6. [AWS S3 Backup Automation with Cron](#6-aws-s3-backup-automation-with-cron)
7. [Log Rotation Setup](#7-log-rotation-setup)
8. [Monitoring & Troubleshooting](#8-monitoring--troubleshooting)

---

## 1. Prerequisites & EC2 Setup

### Step 1.1: Launch AWS EC2 Instance
1. Log into your AWS Console and navigate to the **EC2 Dashboard**.
2. Click **Launch Instance** and configure:
   - **Name**: `mcq-battle-server`
   - **AMI**: Ubuntu Server 22.04 LTS (HVM), SSD Volume Type.
   - **Instance Type**: `t2.micro` or `t3.micro` (eligible for Free Tier).
   - **Key Pair**: Create a new RSA key pair, download the `.pem` file, and keep it safe.
3. **Network Settings (Security Group)**:
   - Allow **SSH** (Port 22) - *highly recommended to restrict source to your IP address*.
   - Allow **HTTP** (Port 80) from anywhere.
   - Allow **HTTPS** (Port 443) from anywhere.

### Step 1.2: Connect via SSH
On your local terminal, set correct key permissions and connect:
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

---

## 2. Environment and Dependency Installation

Once connected to your Ubuntu server, update system repositories and install core dependencies:

```bash
# Update Ubuntu package lists
sudo apt update && sudo apt upgrade -y

# Install Python, build dependencies, git, and Nginx
sudo apt install -y python3-pip python3-venv python3-dev git nginx sqlite3 awscli fail2ban
```

### Step 2.1: Clone Repository & Setup Virtual Environment
```bash
# Clone the repository
cd /home/ubuntu
git clone https://github.com/JerinAppus/mcq-portal.git mcq-portal
cd mcq-portal

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies + Gunicorn
pip install -r requirements.txt
pip install gunicorn
```

### Step 2.2: Configure Environment Variables
Copy `.env.example` to `.env` and configure security credentials:
```bash
cp .env.example .env
nano .env
```
Inside `.env`, configure:
- `SECRET_KEY` and `JWT_SECRET_KEY` with secure, random values.
- `FLASK_ENV=production`
- `DATABASE_URL` (Defaults to SQLite fallback `sqlite:///instance/mcq_battle.db`).
- `S3_BACKUP_BUCKET=your-custom-s3-backup-bucket-name` (For backups).

---

## 3. Nginx Reverse Proxy Configuration

Nginx acts as a high-performance reverse proxy. It serves the static frontend assets directly and proxies backend `/api/` calls to Gunicorn.

### Step 3.1: Copy Nginx Config Template
```bash
# Copy template from repository to Nginx directory
sudo cp devops/nginx/mcq-portal.conf /etc/nginx/sites-available/mcq-portal

# Enable the configuration by creating a symlink
sudo ln -s /etc/nginx/sites-available/mcq-portal /etc/nginx/sites-enabled/

# Remove default Nginx welcome site configuration
sudo rm /etc/nginx/sites-enabled/default
```

### Step 3.2: Test and Reload Nginx
```bash
# Test for syntax errors
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx
```

### Step 3.3: Configure SSL with Let's Encrypt Certbot (Recommended)
To enable HTTPS, use Certbot to automatically configure SSL certificates:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 4. Systemd Service Management

Systemd ensures your Python Flask Gunicorn application runs continuously, auto-restarts on crashes, and boots on system start.

### Step 4.1: Install Systemd Unit File
```bash
# Copy unit file to system directory
sudo cp devops/systemd/mcq.service /etc/systemd/system/mcq.service

# Create log directory and set permissions
mkdir -p /home/ubuntu/mcq-portal/logs
chown -R ubuntu:ubuntu /home/ubuntu/mcq-portal/logs
```

### Step 4.2: Start and Enable Backend Service
```bash
# Reload systemd manager configurations
sudo systemctl daemon-reload

# Start MCQ service
sudo systemctl start mcq

# Enable service to run on boot
sudo systemctl enable mcq
```

---

## 5. SSH Hardening & Fail2ban Security

Secure the server from external brute-force attacks and root exploits.

### Step 5.1: Run the SSH Hardening Script
The script disables password login (only key-based access works), restricts root logins, and configures Fail2ban.

```bash
# Ensure script is executable
chmod +x devops/scripts/harden-ssh.sh

# Run script as root
sudo ./devops/scripts/harden-ssh.sh
```

### Step 5.2: Verification
> [!WARNING]
> Keep your current SSH session open. Open a new terminal window on your local machine and verify you can connect using your key. Do not close the original terminal window until you have confirmed SSH access works.

---

## 6. AWS S3 Backup Automation with Cron

The backup script packages the database and application data, then uploads it directly to your AWS S3 bucket.

### Step 6.1: Configure AWS CLI Credentials
Ensure your EC2 server has permissions to write to AWS S3. Run configuration:
```bash
# Set AWS region, access key id, and secret key
aws configure
```
*(Alternatively, create an IAM Role with AmazonS3FullAccess policy and attach it to your EC2 instance to bypass credentials management).*

### Step 6.2: Ensure Script is Executable
```bash
chmod +x devops/scripts/backup.sh
```

### Step 6.3: Schedule Backup using Cron
Open the crontab editor for the `ubuntu` user:
```bash
crontab -e
```
Add the following line at the bottom to run the backup script every night at 2:00 AM:
```text
0 2 * * * /bin/bash /home/ubuntu/mcq-portal/devops/scripts/backup.sh >> /home/ubuntu/mcq-portal/logs/backup_cron.log 2>&1
```

---

## 7. Log Rotation Setup

Logrotate prevents your server storage from running out of space by compressing and archiving application logs.

### Step 7.1: Configure Logrotate
```bash
# Copy config file to logrotate system directory
sudo cp devops/logrotate/mcq-portal /etc/logrotate.d/mcq-portal

# Set correct permissions
sudo chmod 644 /etc/logrotate.d/mcq-portal
```

### Step 7.2: Force Test Rotation
You can run a dry-run or force logrotate execution to verify syntax correctness:
```bash
sudo logrotate -d /etc/logrotate.d/mcq-portal
```

---

## 8. Monitoring & Troubleshooting

### Check Service Status
```bash
# Check Gunicorn Flask app status
sudo systemctl status mcq

# Check Nginx web server status
sudo systemctl status nginx

# Check Fail2ban active jails status
sudo fail2ban-client status sshd
```

### Watch Active Logs
Use `journalctl` to view real-time standard output logs from Gunicorn:
```bash
sudo journalctl -u mcq -f
```

To view application backup logs:
```bash
cat /home/ubuntu/mcq-portal/logs/backup.log
```

To view Nginx error logs:
```bash
sudo tail -f /var/log/nginx/error.log
```
