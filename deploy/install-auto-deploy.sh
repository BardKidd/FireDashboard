#!/usr/bin/env bash
# Installs a systemd timer that runs deploy/auto-deploy.sh every 5 minutes as
# the current user. Run once on the server: bash deploy/install-auto-deploy.sh
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
user=$(id -un)

sudo tee /etc/systemd/system/fire-auto-deploy.service >/dev/null <<UNIT
[Unit]
Description=FireDashboard auto deploy (pull newest main + images)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
User=$user
WorkingDirectory=$repo
ExecStart=/bin/bash $repo/deploy/auto-deploy.sh
UNIT

sudo tee /etc/systemd/system/fire-auto-deploy.timer >/dev/null <<UNIT
[Unit]
Description=Check for a new FireDashboard version every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
UNIT

# The timer only reacts to new commits, so switch to the prebuilt images once
# now (otherwise a server that just ran `git pull` keeps its old local build).
(cd "$repo" && docker compose pull -q backend frontend && docker compose up -d)

sudo systemctl daemon-reload
sudo systemctl enable --now fire-auto-deploy.timer
echo "已安裝。立刻跑一次："
sudo systemctl start fire-auto-deploy.service || true
sudo journalctl -u fire-auto-deploy.service -n 20 --no-pager
