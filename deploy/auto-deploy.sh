#!/usr/bin/env bash
# Updates this server to the newest main, using the images GitHub Actions built
# (.github/workflows/images.yml). Run every few minutes by fire-auto-deploy.timer
# (install with deploy/install-auto-deploy.sh). Does nothing when already up to date.
set -euo pipefail
cd "$(dirname "$0")/.."

REGISTRY=ghcr.io/bardkidd/firedashboard

git fetch -q origin main
current=$(git rev-parse HEAD)
target=$(git rev-parse origin/main)
[ "$current" = "$target" ] && exit 0

# Wait until Actions has finished building this exact commit. If its tests
# failed, the images never appear and the server stays on the old version.
for service in backend frontend; do
  if ! docker manifest inspect "$REGISTRY-$service:$target" >/dev/null 2>&1; then
    echo "main 已更新到 ${target:0:7}，但 $service 的 image 還沒建好（或 package 不是 Public），下次再試"
    exit 0
  fi
done

echo "更新 ${current:0:7} -> ${target:0:7}"
git merge --ff-only -q origin/main
docker compose pull -q backend frontend
docker compose up -d
docker image prune -f >/dev/null
echo "完成：$(git log -1 --format='%h %s')"
