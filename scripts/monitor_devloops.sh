#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UID_NUM="$(id -u)"

OUT_MD="${OUT_MD:-$ROOT_DIR/artifacts/devloop/loop_monitor.md}"
OUT_JSON="${OUT_JSON:-$ROOT_DIR/artifacts/devloop/loop_monitor.json}"
OUT_STATUS="${OUT_STATUS:-$ROOT_DIR/artifacts/devloop/loop_monitor_status.txt}"
AUTO_RESTART="${AUTO_RESTART:-1}"
STALE_SECONDS="${STALE_SECONDS:-900}"
NOW_EPOCH="$(date +%s)"
NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

mkdir -p "$(dirname "$OUT_MD")"

LOOPS=(
  "main|com.joeyrahme.trading.devloop|/Users/joeyrahme/GitHubWorkspace/trading|manual_layer1_tasks.md"
  "strategy|com.joeyrahme.trading.devloop.strategy|/Users/joeyrahme/GitHubWorkspace/trading-strategy-loop|manual_layer1_tasks_strategy.md"
  "tetrate|com.joeyrahme.trading.devloop.tetrate|/Users/joeyrahme/GitHubWorkspace/trading-tetrate-loop|manual_layer1_tasks_tetrate.md"
  "evidence|com.joeyrahme.trading.devloop.evidence|/Users/joeyrahme/GitHubWorkspace/trading-evidence-loop|manual_layer1_tasks_evidence.md"
)

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  printf "%s" "$s"
}

get_pid() {
  local label="$1"
  local line
  line="$(launchctl list | awk -v l="$label" '$3==l{print $1}')"
  if [[ -z "$line" ]]; then
    echo ""
  elif [[ "$line" == "-" ]]; then
    echo ""
  else
    echo "$line"
  fi
}

read_kv_value() {
  local file="$1"
  local key="$2"
  if [[ ! -f "$file" ]]; then
    echo ""
    return
  fi
  awk -F= -v k="$key" '$1==k{print $2}' "$file" | tail -n 1
}

count_open_tasks() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "0"
    return
  fi
  grep -E "^- \\[ \\] " "$path" 2>/dev/null | wc -l | tr -d ' '
}

restart_label() {
  local label="$1"
  launchctl kickstart -k "gui/$UID_NUM/$label" >/dev/null 2>&1 || true
}

md_lines=()
json_items=()
running_count=0
stale_count=0
restart_count=0

md_lines+=("# Loop Monitor")
md_lines+=("")
md_lines+=("- Generated (UTC): \`$NOW_UTC\`")
md_lines+=("- Auto-restart: \`$AUTO_RESTART\`")
md_lines+=("- Stale threshold: \`${STALE_SECONDS}s\`")
md_lines+=("")
md_lines+=("| Loop | PID | Cycle | Profile | Last Update (UTC) | Age | Open Tasks | STOP | State | Action |")
md_lines+=("|---|---:|---:|---|---|---:|---:|---|---|---|")

for item in "${LOOPS[@]}"; do
  IFS='|' read -r name label workdir taskfile <<<"$item"
  status_file="$workdir/artifacts/devloop/status.txt"
  stop_file="$workdir/artifacts/devloop/STOP"
  task_path="$workdir/$taskfile"

  pid="$(get_pid "$label")"
  [[ -n "$pid" ]] && running_count=$((running_count + 1))

  cycle="$(read_kv_value "$status_file" "cycle")"
  profile="$(read_kv_value "$status_file" "profile")"
  ts="$(read_kv_value "$status_file" "timestamp_utc")"
  [[ -z "$cycle" ]] && cycle="n/a"
  [[ -z "$profile" ]] && profile="n/a"
  [[ -z "$ts" ]] && ts="n/a"

  if [[ -f "$status_file" ]]; then
    mod_epoch="$(stat -f %m "$status_file" 2>/dev/null || echo 0)"
    age="$((NOW_EPOCH - mod_epoch))"
  else
    age=999999
  fi

  open_tasks="$(count_open_tasks "$task_path")"
  stop_state="no"
  [[ -f "$stop_file" ]] && stop_state="yes"

  state="OK"
  action="-"
  if [[ -z "$pid" ]]; then
    state="DOWN"
  fi
  if (( age > STALE_SECONDS )); then
    state="STALE"
    stale_count=$((stale_count + 1))
  fi
  if [[ "$stop_state" == "yes" ]]; then
    state="PAUSED"
  fi

  if [[ "$AUTO_RESTART" == "1" && ( "$state" == "DOWN" || "$state" == "STALE" ) ]]; then
    restart_label "$label"
    restart_count=$((restart_count + 1))
    action="restart"
  fi

  pid_print="${pid:-n/a}"
  md_lines+=("| $name | $pid_print | $cycle | $profile | $ts | ${age}s | $open_tasks | $stop_state | $state | $action |")

  json_items+=("{\"name\":\"$(json_escape "$name")\",\"label\":\"$(json_escape "$label")\",\"workdir\":\"$(json_escape "$workdir")\",\"pid\":\"$(json_escape "${pid:-}")\",\"cycle\":\"$(json_escape "$cycle")\",\"profile\":\"$(json_escape "$profile")\",\"last_update_utc\":\"$(json_escape "$ts")\",\"age_seconds\":$age,\"open_tasks\":$open_tasks,\"stop\":\"$stop_state\",\"state\":\"$state\",\"action\":\"$action\"}")
done

summary="running=$running_count stale=$stale_count restarts=$restart_count"
md_lines+=("")
md_lines+=("- Summary: \`$summary\`")

printf "%s\n" "${md_lines[@]}" >"$OUT_MD"
{
  echo "{"
  echo "  \"generated_utc\": \"${NOW_UTC}\","
  echo "  \"auto_restart\": ${AUTO_RESTART},"
  echo "  \"stale_seconds\": ${STALE_SECONDS},"
  echo "  \"summary\": {\"running\": ${running_count}, \"stale\": ${stale_count}, \"restarts\": ${restart_count}},"
  echo "  \"loops\": ["
  if ((${#json_items[@]} > 0)); then
    for ((i = 0; i < ${#json_items[@]}; i++)); do
      if ((i + 1 < ${#json_items[@]})); then
        echo "    ${json_items[$i]},"
      else
        echo "    ${json_items[$i]}"
      fi
    done
  fi
  echo "  ]"
  echo "}"
} >"$OUT_JSON"
printf "%s\n" "$summary" >"$OUT_STATUS"

echo "ok: loop monitor updated -> $OUT_MD"
