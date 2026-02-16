#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.joeyrahme.trading.devloop"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$REPO_ROOT/artifacts/devloop"
OUT_LOG="$LOG_DIR/launchd.out.log"
ERR_LOG="$LOG_DIR/launchd.err.log"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env.devloop}"
RUN_TARS_VALUE="${RUN_TARS:-0}"
RUN_RAG_VALUE="${RUN_RAG:-0}"
NO_SLEEP_VALUE="${NO_SLEEP:-0}"
INTERVAL_SECONDS_VALUE="${INTERVAL_SECONDS:-300}"
FULL_EVERY_VALUE="${FULL_EVERY:-6}"

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

install_agent() {
  cat >"$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd "$REPO_ROOT" &amp;&amp; set -a &amp;&amp; [ -f "$ENV_FILE" ] &amp;&amp; source "$ENV_FILE" ; set +a ; ./scripts/continuous_devloop.sh start</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$REPO_ROOT</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>INTERVAL_SECONDS</key>
    <string>$INTERVAL_SECONDS_VALUE</string>
    <key>FULL_EVERY</key>
    <string>$FULL_EVERY_VALUE</string>
    <key>MAX_CYCLES</key>
    <string>0</string>
    <key>RUN_TARS</key>
    <string>$RUN_TARS_VALUE</string>
    <key>RUN_RAG</key>
    <string>$RUN_RAG_VALUE</string>
    <key>NO_SLEEP</key>
    <string>$NO_SLEEP_VALUE</string>
    <key>PATH</key>
    <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$OUT_LOG</string>
  <key>StandardErrorPath</key>
  <string>$ERR_LOG</string>
</dict>
</plist>
EOF

  # Reload if present, then load.
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
  launchctl enable "gui/$(id -u)/$LABEL" || true
  launchctl kickstart -k "gui/$(id -u)/$LABEL"

  echo "installed: $PLIST_PATH"
  echo "label: $LABEL"
}

uninstall_agent() {
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  rm -f "$PLIST_PATH"
  echo "uninstalled: $LABEL"
}

status_agent() {
  echo "plist: $PLIST_PATH"
  if [[ -f "$PLIST_PATH" ]]; then
    echo "plist_present=yes"
  else
    echo "plist_present=no"
  fi
  launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | sed -n '1,40p' || echo "launchd_status=not_loaded"
  echo "stdout_log: $OUT_LOG"
  echo "stderr_log: $ERR_LOG"
}

usage() {
  cat <<EOF
Usage: $0 <install|uninstall|status|restart>

Env overrides for install/restart:
  RUN_TARS=1           Enable TARS run each cycle
  RUN_RAG=1            Enable RAG refresh on full-profile cycles
  NO_SLEEP=1           Run cycles back-to-back (no pause)
  INTERVAL_SECONDS=60  Loop interval
  FULL_EVERY=3         Run full profile every N cycles
  ENV_FILE=.env.devloop Env file sourced before loop startup
EOF
}

cmd="${1:-}"
case "$cmd" in
  install) install_agent ;;
  uninstall) uninstall_agent ;;
  status) status_agent ;;
  restart)
    uninstall_agent
    install_agent
    ;;
  *)
    usage
    exit 1
    ;;
esac
