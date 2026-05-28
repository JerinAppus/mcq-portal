#!/bin/bash
# MCQ Battle Platform SSH Hardening and Fail2ban Setup Script
# Must be executed as root or via sudo

# --- WARNING AND PERMISSION CHECK ---
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root or with sudo privileges!" >&2
    exit 1
fi

echo "=========================================================="
echo "   MCQ BATTLE PLATFORM: SSH HARDENING & FAIL2BAN SETUP    "
echo "=========================================================="
echo "WARNING: Sourcing this script will disable Password Authentication"
echo "and Root login via SSH. Ensure you have key-based SSH setup"
echo "and configured BEFORE running this script to avoid lockouts!"
echo "=========================================================="
read -p "Do you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled by user."
    exit 0
fi

# --- 1. HARDEN SSH CONFIGURATION ---
SSHD_CONFIG="/etc/ssh/sshd_config"
SSHD_BACKUP="/etc/ssh/sshd_config.bak.$(date +%Y%m%d_%H%M%S)"

echo "[+] Backing up original sshd_config to $SSHD_BACKUP"
cp "$SSHD_CONFIG" "$SSHD_BACKUP"

echo "[+] Hardening SSH Settings..."

# Function to ensure a configuration is set in sshd_config
set_ssh_param() {
    local param="$1"
    local value="$2"
    # Check if parameter is commented out or exists
    if grep -qE "^[#]*\s*$param" "$SSHD_CONFIG"; then
        # Replace the existing parameter line
        sed -i -E "s|^[#]*\s*$param.*|$param $value|" "$SSHD_CONFIG"
    else
        # Append parameter to the end of the config file
        echo "$param $value" >> "$SSHD_CONFIG"
    fi
    echo "    - Set: $param = $value"
}

# Apply critical security parameters
set_ssh_param "PermitRootLogin" "no"
set_ssh_param "PasswordAuthentication" "no"
set_ssh_param "PubkeyAuthentication" "yes"
set_ssh_param "X11Forwarding" "no"
set_ssh_param "MaxAuthTries" "4"
set_ssh_param "ClientAliveInterval" "300"
set_ssh_param "ClientAliveCountMax" "2"
set_ssh_param "AllowAgentForwarding" "no"
set_ssh_param "AllowTcpForwarding" "no"

# Validate SSH configuration syntax before restarting
echo "[+] Validating new SSH configuration syntax..."
sshd -t
if [ $? -eq 0 ]; then
    echo "[+] Configuration valid. Restarting SSH service..."
    if systemctl is-active --quiet sshd; then
        systemctl restart sshd
    else
        systemctl restart ssh
    fi
    echo "[+] SSH service restarted."
else
    echo "[-] ERROR: Invalid SSH configuration detected! Restoring backup..."
    cp "$SSHD_BACKUP" "$SSHD_CONFIG"
    exit 1
fi

# --- 2. INSTALL AND CONFIGURE FAIL2BAN ---
echo "[+] Checking for Fail2ban installation..."
if ! command -v fail2ban-client &> /dev/null; then
    echo "[+] Fail2ban not found. Installing Fail2ban..."
    apt-get update && apt-get install -y fail2ban
    if [ $? -ne 0 ]; then
        echo "[-] ERROR: Failed to install Fail2ban!" >&2
        exit 1
    fi
else
    echo "[+] Fail2ban is already installed."
fi

# Configure custom local SSH jail definitions
JAIL_LOCAL="/etc/fail2ban/jail.local"
echo "[+] Creating custom SSH jail configuration at $JAIL_LOCAL"

cat <<EOF > "$JAIL_LOCAL"
# MCQ Battle Platform Custom Jail Config
[DEFAULT]
# Ban host for 1 hour (3600 seconds)
bantime = 3600

# A host is banned if it has generated "maxretry" during the last "findtime"
findtime = 600

# Number of attempts before host gets banned
maxretry = 3

# Ignore trusted local and private loopbacks
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = %(sshd_log)s
backend = %(sshd_backend)s
maxretry = 3
EOF

echo "[+] Enabling and restarting Fail2ban service..."
systemctl enable fail2ban
systemctl restart fail2ban

if systemctl is-active --quiet fail2ban; then
    echo "[+] Fail2ban is active and running!"
else
    echo "[-] WARNING: Fail2ban service failed to start. Check system logs."
fi

echo "=========================================================="
echo "   SSH HARDENING AND FAIL2BAN SETUP COMPLETED!            "
echo "=========================================================="
echo "Please keep your current SSH session OPEN while testing   "
echo "login credentials in a NEW terminal window to confirm     "
echo "that key-based access remains fully functional.           "
echo "=========================================================="
EOF_EXIT=0
exit $EOF_EXIT
