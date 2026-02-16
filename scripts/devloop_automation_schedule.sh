#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT_LABEL="com.joeyrahme.trading.devloop.commit4h"
REPORT_LABEL="com.joeyrahme.trading.devloop.report9am"
COMMIT_PLIST="$HOME/Library/LaunchAgents/$COMMIT_LABEL.plist"
REPORT_PLIST="$HOME/Library/LaunchAgents/$REPORT_LABEL.plist"
LOG_DIR="$REPO_ROOT/artifacts/devloop"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

write_commit_plist() {
  cat >"$COMMIT_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$COMMIT_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd "$REPO_ROOT" &amp;&amp; ./scripts/devloop_commit_and_report.sh commit</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO_ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartInterval</key>
  <integer>14400</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/commit4h.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/commit4h.err.log</string>
</dict>
</plist>
EOF
}

write_report_plist() {
  cat >"$REPORT_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$REPORT_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd "$REPO_ROOT" &amp;&amp; ./scripts/devloop_commit_and_report.sh report</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO_ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/report9am.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/report9am.err.log</string>
</dict>
</plist>
EOF
}

load_label() {
  local label="$1"
  local plist="$2"
  launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$plist"
  launchctl enable "gui/$(id -u)/$label" || true
  launchctl kickstart -k "gui/$(id -u)/$label" || true
}

install_agents() {
  write_commit_plist
  write_report_plist
  load_label "$COMMIT_LABEL" "$COMMIT_PLIST"
  load_label "$REPORT_LABEL" "$REPORT_PLIST"
  echo "installed: $COMMIT_LABEL"
  echo "installed: $REPORT_LABEL"
}

uninstall_agents() {
  launchctl bootout "gui/$(id -u)/$COMMIT_LABEL" >/dev/null 2>&1 || true
  launchctl bootout "gui/$(id -u)/$REPORT_LABEL" >/dev/null 2>&1 || true
  rm -f "$COMMIT_PLIST" "$REPORT_PLIST"
  echo "uninstalled: $COMMIT_LABEL"
  echo "uninstalled: $REPORT_LABEL"
}

status_agents() {
  echo "commit_plist: $COMMIT_PLIST"
  echo "report_plist: $REPORT_PLIST"
  launchctl print "gui/$(id -u)/$COMMIT_LABEL" 2>/dev/null | sed -n '1,30p' || echo "commit_status=not_loaded"
  launchctl print "gui/$(id -u)/$REPORT_LABEL" 2>/dev/null | sed -n '1,30p' || echo "report_status=not_loaded"
  echo "logs:"
  echo "- $LOG_DIR/commit4h.out.log"
  echo "- $LOG_DIR/commit4h.err.log"
  echo "- $LOG_DIR/report9am.out.log"
  echo "- $LOG_DIR/report9am.err.log"
}

usage() {
  cat <<EOF
Usage: $0 <install|uninstall|status|restart|run-now>

Commands:
  install   Install 4h commit scheduler and 9:00 AM report scheduler.
  uninstall Remove both schedulers.
  status    Show scheduler status.
  restart   Reinstall both schedulers.
  run-now   Execute immediate report+commit once.
EOF
}

cmd="${1:-}"
case "$cmd" in
  install) install_agents ;;
  uninstall) uninstall_agents ;;
  status) status_agents ;;
  restart)
    uninstall_agents
    install_agents
    ;;
  run-now)
    cd "$REPO_ROOT"
    ./scripts/devloop_commit_and_report.sh both
    ;;
  *)
    usage
    exit 1
    ;;
esac
