#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="${LABEL:-com.joeyrahme.trading.devloop.monitor}"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$REPO_ROOT/artifacts/devloop"
OUT_LOG="$LOG_DIR/loop_monitor.out.log"
ERR_LOG="$LOG_DIR/loop_monitor.err.log"
INTERVAL_SECONDS_VALUE="${INTERVAL_SECONDS:-60}"
AUTO_RESTART_VALUE="${AUTO_RESTART:-1}"
STALE_SECONDS_VALUE="${STALE_SECONDS:-900}"

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
    <string>cd "$REPO_ROOT" &amp;&amp; AUTO_RESTART="$AUTO_RESTART_VALUE" STALE_SECONDS="$STALE_SECONDS_VALUE" ./scripts/devloop_self_heal.sh &amp;&amp; AUTO_RESTART="$AUTO_RESTART_VALUE" STALE_SECONDS="$STALE_SECONDS_VALUE" ./scripts/monitor_devloops.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO_ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartInterval</key>
  <integer>$INTERVAL_SECONDS_VALUE</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$OUT_LOG</string>
  <key>StandardErrorPath</key>
  <string>$ERR_LOG</string>
</dict>
</plist>
EOF

  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
  launchctl enable "gui/$(id -u)/$LABEL" || true
  launchctl kickstart -k "gui/$(id -u)/$LABEL"
  echo "installed: $PLIST_PATH"
}

uninstall_agent() {
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  rm -f "$PLIST_PATH"
  echo "uninstalled: $LABEL"
}

status_agent() {
  echo "plist: $PLIST_PATH"
  [[ -f "$PLIST_PATH" ]] && echo "plist_present=yes" || echo "plist_present=no"
  launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | sed -n '1,40p' || echo "launchd_status=not_loaded"
}

case "${1:-}" in
  install) install_agent ;;
  uninstall) uninstall_agent ;;
  status) status_agent ;;
  restart)
    uninstall_agent
    install_agent
    ;;
  *)
    echo "Usage: $0 <install|uninstall|status|restart>"
    exit 1
    ;;
esac
