# shellcheck shell=bash
# Flags + ouverture du simulateur local. Sourcé par les hooks preview.

DEV="$REPO/naviguide-simulator/.dev"
FLAG_FIRST="$DEV/open-on-first-reply"
FLAG_EDIT="$DEV/open-browser-on-stop"
FLAG_ASK="$DEV/open-browser-on-request"
FLAG_OPENED="$DEV/browser-opened-session"
STAMP="$DEV/last-browser-open"
HOOK_LOG="$DEV/preview-hook.log"
HOOK_STDIN="${SIMULATOR_HOOK_STDIN:-}"

preview_dev_dir() {
  mkdir -p "$DEV"
}

preview_log() {
  preview_dev_dir
  printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$HOOK_LOG" 2>/dev/null || true
}

preview_read_stdin() {
  if [[ -n "$HOOK_STDIN" ]]; then
    printf '%s' "$HOOK_STDIN"
  else
    cat
  fi
}

preview_is_background() {
  printf '%s' "$1" | python3 -c '
import json, sys
try:
    data = json.loads(sys.stdin.read() or "{}")
except json.JSONDecodeError:
    raise SystemExit(1)
if data.get("is_background_agent") is True:
    raise SystemExit(0)
raise SystemExit(1)
'
}

preview_prompt_asks_open() {
  printf '%s' "$1" | python3 "$REPO/.cursor/hooks/simulator-preview-ask.py"
}

preview_reset_session_flags() {
  preview_dev_dir
  rm -f "$FLAG_EDIT" "$FLAG_ASK" "$FLAG_OPENED"
  printf '1\n' > "$FLAG_FIRST"
}

preview_mark_ask() {
  preview_dev_dir
  printf '1\n' > "$FLAG_ASK"
}

preview_should_open() {
  [[ -f "$FLAG_FIRST" || -f "$FLAG_ASK" || -f "$FLAG_EDIT" || ! -f "$FLAG_OPENED" ]]
}

preview_consume_flags() {
  rm -f "$FLAG_FIRST" "$FLAG_ASK" "$FLAG_EDIT"
}

preview_open_url() {
  local url="http://localhost:5174"
  local app
  # Chemins complets : Launch Services du hook ne trouve pas toujours « Safari ».
  for app in \
    "/Applications/Google Chrome.app" \
    "/Applications/Safari.app" \
    "/System/Applications/Safari.app" \
    "/Applications/Firefox.app"
  do
    if [[ -d "$app" ]] && /usr/bin/open -a "$app" "$url" >> "$HOOK_LOG" 2>&1; then
      preview_log "open via $app"
      return 0
    fi
  done
  if /usr/bin/open "$url" >> "$HOOK_LOG" 2>&1; then
    return 0
  fi
  open "$url" >> "$HOOK_LOG" 2>&1
}

# $1 = force → ignore flags / debounce (demande explicite).
preview_open_browser() {
  local force="${1:-}"
  if [[ "$force" != "force" ]] && ! preview_should_open; then
    preview_log "skip: no flag and already opened this session"
    return 0
  fi
  preview_dev_dir
  if [[ "${SIMULATOR_HOOK_DRY_RUN:-0}" == "1" ]]; then
    preview_consume_flags
    printf '1\n' > "$FLAG_OPENED"
    echo "would-open"
    return 0
  fi
  now="$(date +%s)"
  if [[ "$force" != "force" && -f "$STAMP" && -f "$FLAG_OPENED" ]]; then
    last="$(cat "$STAMP" 2>/dev/null || echo 0)"
    if [[ "$last" =~ ^[0-9]+$ ]] && (( now - last < 20 )); then
      preview_log "skip: debounce ${now}-${last}s"
      preview_consume_flags
      return 0
    fi
  fi
  if [[ -x "$REPO/naviguide-simulator/ensure-dev.sh" ]]; then
    bash "$REPO/naviguide-simulator/ensure-dev.sh" --quiet --open
  fi
  if preview_open_url; then
    preview_log "opened http://localhost:5174${force:+ force}"
    printf '%s\n' "$now" > "$STAMP"
    printf '1\n' > "$FLAG_OPENED"
    preview_consume_flags
  else
    preview_log "open failed"
  fi
}
