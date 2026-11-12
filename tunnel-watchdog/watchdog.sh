#!/bin/sh
# Keeps the Cloudflare Tunnel alive after the host sleeps or the VM is paused.
#
# Two triggers restart the cloudflared container:
#   1. Sleep detected: this loop runs every CHECK_EVERY seconds. If far more time
#      than that passed between two rounds, the whole machine was frozen
#      (host sleep / VM pause) and the tunnel's connections are likely dead.
#   2. Unhealthy: cloudflared's own healthcheck (`cloudflared tunnel ready`)
#      reports no live connection to Cloudflare.
# Plain Docker never restarts unhealthy containers on its own, hence this script.
set -u

CHECK_EVERY="${CHECK_EVERY:-15}"
SLEEP_GAP="${SLEEP_GAP:-60}"
SERVICE="${WATCH_SERVICE:-cloudflared}"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }

# Find our compose project so we only touch this stack's cloudflared.
project="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$(hostname)" 2>/dev/null)"
if [ -z "$project" ]; then
  log "cannot read own compose project label; is /var/run/docker.sock mounted?"
  exit 1
fi

target() {
  docker ps -aq \
    --filter "label=com.docker.compose.project=$project" \
    --filter "label=com.docker.compose.service=$SERVICE" | head -n1
}

restart_tunnel() {
  id="$(target)"
  if [ -z "$id" ]; then
    log "no $SERVICE container found in project $project"
    return
  fi
  log "restarting $SERVICE ($1)"
  docker restart "$id" >/dev/null && log "$SERVICE restarted"
}

log "watching $SERVICE in project $project (check every ${CHECK_EVERY}s, sleep gap ${SLEEP_GAP}s)"
last="$(date +%s)"
cooldown_until=0
while :; do
  sleep "$CHECK_EVERY"
  now="$(date +%s)"
  gap=$((now - last))
  last="$now"

  if [ "$gap" -gt "$SLEEP_GAP" ]; then
    log "clock jumped ${gap}s: machine was asleep or paused"
    # Give the network a moment to come back before reconnecting.
    sleep 5
    restart_tunnel "after sleep"
    last="$(date +%s)"
    cooldown_until=$((last + 90))
    continue
  fi

  # After a restart, let cloudflared reconnect before judging its health again.
  [ "$now" -lt "$cooldown_until" ] && continue

  id="$(target)"
  [ -z "$id" ] && continue
  health="$(docker inspect -f '{{ if .State.Health }}{{ .State.Health.Status }}{{ end }}' "$id" 2>/dev/null)"
  if [ "$health" = "unhealthy" ]; then
    restart_tunnel "healthcheck failed"
    last="$(date +%s)"
    cooldown_until=$((last + 90))
  fi
done
