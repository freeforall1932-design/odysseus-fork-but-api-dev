#!/usr/bin/env bash
# harness - one command for the Gifscythe AI team. Run "harness help" to see everything it can do.
# Works on Linux, WSL and macOS (bash 3.2 or newer).

HARNESS_DIR="${HARNESS_DIR:-$HOME/harness}"
VENV="${LITELLM_VENV:-$HOME/litellm-env}"
KEYS="${HARNESS_KEYS:-$HOME/.config/gifscythe-harness/keys.env}"
CONF_DIR="$(dirname "$KEYS")"
CONFIG="${LITELLM_CONFIG:-$HOME/.litellm/config.yaml}"
PORT="${LITELLM_PORT:-4000}"
UI_PORT="${GIFSCYTHE_UI_PORT:-8765}"
MAX_AGE_HOURS="${SCOUT_MAX_AGE_HOURS:-12}"
REPO="${GIFSCYTHE_REPO:-freeforall1932-design/gifscythe}"
OAT_REPO="${GIFSCYTHE_OAT_NAME:-${REPO##*/}}"
PIDFILE="$HARNESS_DIR/litellm.pid"
LOGFILE="$HARNESS_DIR/litellm.log"
UI_PIDFILE="$HARNESS_DIR/ui.pid"
UI_LOG="$HARNESS_DIR/ui.log"
TOKEN_FILE="$CONF_DIR/ui-token"
PY="$VENV/bin/python"
SCOUT="$HARNESS_DIR/model_scout.py"
UI_PY="$HARNESS_DIR/harness_ui.py"
STATE="$HARNESS_DIR/scout_state.json"
SERVICES="openrouter nvidia mistral google"
export PATH="$HOME/.local/bin:$PATH"
# In a GitHub Codespace, GitHub sets its own short-lived token. Ignore it so the token you gave us is used.
if [ -n "${CODESPACES:-}" ]; then unset GITHUB_TOKEN GH_TOKEN; fi

if [ -x "$PY" ]; then PYX="$PY"; else PYX="$(command -v python3)"; fi

say() { printf '%s\n' "$*"; }
die() { printf '\nProblem: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- small helpers
need_keys() { [ -f "$KEYS" ] || die "your keys file was not found. Run: harness setup-keys"; }

# Run a command with your keys loaded. The keys exist only inside that one command.
with_keys() {
  (
    umask 077
    t="$(mktemp "${TMPDIR:-/tmp}/harness-keys.XXXXXX")" || exit 1
    tr -d '\r' < "$KEYS" > "$t"
    set -a; . "$t"; set +a
    rm -f "$t"
    "$@"
  )
}

get_old() { [ -f "$KEYS" ] && tr -d '\r' < "$KEYS" | grep -E "^$1=" 2>/dev/null | head -1 | cut -d= -f2-; }

env_name() {
  case "$1" in
    openrouter) echo OPENROUTER_API_KEY ;; nvidia) echo NVIDIA_API_KEY ;;
    mistral) echo MISTRAL_API_KEY ;; google) echo GEMINI_API_KEY ;; *) echo "" ;;
  esac
}
nice_name() {
  case "$1" in openrouter) echo OpenRouter ;; nvidia) echo NVIDIA ;; mistral) echo Mistral ;; google) echo Google ;; *) echo "$1" ;; esac
}
valid_service() { case " $SERVICES " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

router_up() { curl -s -m 3 "http://127.0.0.1:$PORT/health/liveliness" >/dev/null 2>&1; }
ui_up() { curl -s -m 2 "http://127.0.0.1:$UI_PORT/ping" >/dev/null 2>&1; }

scout_is_old() {
  [ ! -f "$CONFIG" ] || [ ! -f "$STATE" ] || [ -z "$(find "$STATE" -mmin -$((MAX_AGE_HOURS * 60)) 2>/dev/null)" ]
}

scout_common() {
  # prints the shared options for model_scout.py, one per line
  printf '%s\n' --keys-file "$KEYS" --state "$STATE"
  [ -f "$HARNESS_DIR/scout.yaml" ] && printf '%s\n' --config "$HARNESS_DIR/scout.yaml"
  return 0
}

# Run model_scout.py WITHOUT your keys in the environment (key commands, tables).
scout_plain() {
  [ -f "$SCOUT" ] || die "model_scout.py was not found in $HARNESS_DIR. Run: bash $HARNESS_DIR/install.sh"
  local args=() line
  while IFS= read -r line; do args+=("$line"); done < <(scout_common)
  "$PYX" "$SCOUT" "${args[@]}" "$@"
}

# Run model_scout.py with your keys loaded (tests that need them).
run_scout() {
  need_keys
  [ -f "$SCOUT" ] || die "model_scout.py was not found in $HARNESS_DIR. Run: bash $HARNESS_DIR/install.sh"
  local args=() line
  while IFS= read -r line; do args+=("$line"); done < <(scout_common)
  with_keys "$PYX" "$SCOUT" --out "$CONFIG" "${args[@]}" "$@"
}

open_browser() {
  local url="$1"
  if [ -n "${CODESPACES:-}" ] && [ -n "${BROWSER:-}" ]; then "$BROWSER" "$url" >/dev/null 2>&1 && return 0; fi
  if grep -qi microsoft /proc/version 2>/dev/null; then
    if command -v wslview >/dev/null 2>&1; then wslview "$url" >/dev/null 2>&1 && return 0; fi
    if command -v powershell.exe >/dev/null 2>&1; then powershell.exe -NoProfile -Command "Start-Process '$url'" >/dev/null 2>&1 && return 0; fi
    if command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$url" >/dev/null 2>&1 && return 0; fi
  elif [ "$(uname)" = "Darwin" ]; then open "$url" >/dev/null 2>&1 && return 0
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" >/dev/null 2>&1 && return 0
  fi
  return 1
}

# ---------------------------------------------------------------- router
start_router() {
  need_keys
  [ -x "$VENV/bin/litellm" ] || die "the router (LiteLLM) was not found in $VENV. Run: bash $HARNESS_DIR/install.sh"
  [ -f "$CONFIG" ] || die "the model list was not found ($CONFIG). Run: harness scout"
  if router_up; then say "Router is already running."; return 0; fi
  with_keys bash -c '[ -n "${LITELLM_MASTER_KEY:-}" ]' || die "the router password is empty. Run: harness setup-keys"
  [ -f "$LOGFILE" ] && [ "$(wc -c < "$LOGFILE")" -gt 5000000 ] && mv -f "$LOGFILE" "$LOGFILE.old"
  say "Starting the router..."
  ( umask 077; t="$(mktemp "${TMPDIR:-/tmp}/harness-keys.XXXXXX")" || exit 1
    tr -d '\r' < "$KEYS" > "$t"; set -a; . "$t"; set +a; rm -f "$t"
    cd "$HARNESS_DIR" || exit 1
    nohup "$VENV/bin/litellm" --config "$CONFIG" --host 127.0.0.1 --port "$PORT" >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE" )
  local i
  for i in $(seq 1 45); do
    if router_up; then say "Router is running."; return 0; fi
    sleep 2
  done
  die "the router did not start. The last lines of its log are:
$(tail -8 "$LOGFILE" 2>/dev/null)"
}

stop_router() {
  local pid="" pids="" i
  [ -f "$PIDFILE" ] && pid="$(cat "$PIDFILE" 2>/dev/null)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
  fi
  rm -f "$PIDFILE"
  pids="$(pgrep -f "[l]itellm --config .*--port $PORT" 2>/dev/null)"
  [ -n "$pids" ] && kill $pids 2>/dev/null
  sleep 1
  return 0
}

# ---------------------------------------------------------------- agent team (OAT)
start_oat() {
  if ! command -v oat >/dev/null 2>&1; then
    say "The agent team (OAT) is not installed yet, so I skipped it. Run: bash $HARNESS_DIR/install.sh"
    return 0
  fi
  [ -f "$HOME/.oat/config.toml" ] || say "Note: the agent team does not know the router yet. Run: harness connect-oat"
  # Start OAT WITHOUT your AI keys in its environment: the helpers can run commands, so they must not see them.
  env -u OPENROUTER_API_KEY -u NVIDIA_API_KEY -u MISTRAL_API_KEY -u GEMINI_API_KEY -u LITELLM_MASTER_KEY \
    oat start 2>&1 | tail -3
}

# ---------------------------------------------------------------- dashboard
ensure_token() {
  if [ ! -s "$TOKEN_FILE" ]; then
    mkdir -p "$CONF_DIR" && chmod 700 "$CONF_DIR"
    ( umask 077; "$PYX" -c "import secrets; print(secrets.token_urlsafe(24))" > "$TOKEN_FILE" )
  fi
  tr -d '\n\r ' < "$TOKEN_FILE"
}

start_ui() {
  [ -f "$UI_PY" ] || die "the dashboard file was not found in $HARNESS_DIR. Run: bash $HARNESS_DIR/install.sh"
  if ui_up; then return 0; fi
  ensure_token >/dev/null
  [ -f "$UI_LOG" ] && [ "$(wc -c < "$UI_LOG")" -gt 2000000 ] && mv -f "$UI_LOG" "$UI_LOG.old"
  ( cd "$HARNESS_DIR" || exit 1
    env -u OPENROUTER_API_KEY -u NVIDIA_API_KEY -u MISTRAL_API_KEY -u GEMINI_API_KEY -u LITELLM_MASTER_KEY \
      GIFSCYTHE_UI_PORT="$UI_PORT" GIFSCYTHE_REPO="$REPO" HARNESS_KEYS="$KEYS" LITELLM_PORT="$PORT" \
      nohup "$PYX" "$UI_PY" >> "$UI_LOG" 2>&1 &
    echo $! > "$UI_PIDFILE" )
  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do ui_up && return 0; sleep 1; done
  die "the dashboard did not start. The last lines of its log are:
$(tail -8 "$UI_LOG" 2>/dev/null)"
}

stop_ui() {
  local pid=""
  [ -f "$UI_PIDFILE" ] && pid="$(cat "$UI_PIDFILE" 2>/dev/null)"
  [ -n "$pid" ] && kill "$pid" 2>/dev/null
  rm -f "$UI_PIDFILE"
  return 0
}

ui_url() {
  if [ -n "${CODESPACES:-}" ] && [ -n "${CODESPACE_NAME:-}" ] && [ -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" ]; then
    printf 'https://%s-%s.%s/?t=%s' "$CODESPACE_NAME" "$UI_PORT" "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN" "$(ensure_token)"
  else
    printf 'http://127.0.0.1:%s/?t=%s' "$UI_PORT" "$(ensure_token)"
  fi
}

# ---------------------------------------------------------------- commands
cmd_help() {
  cat <<'EOF'
harness - commands (type "harness" and then one of these):

  Open the dashboard (the easy way)
    open           start everything and open the dashboard in your browser

  First-time setup
    setup-keys     save your free AI keys one at a time (each key is tested before it is saved)
    github-login   sign in to GitHub with your token
    connect-oat    tell the agent team how to reach the router
    install-skills put the team's built-in skills in place
    add-repo       add a GitHub project:  harness add-repo https://github.com/owner/name
    doctor         check that every part is installed and working, with fixes

  Keys
    keys           show which keys are saved and whether they work
    set-key        replace one key:   harness set-key nvidia
    remove-key     remove one key:    harness remove-key nvidia

  Models
    check          test your keys and show the free models that were found
    scout          find, quick-test and rank free models, then write the router's list
    selftest       test the model picker script itself (no keys or internet needed)

  Every day
    start          refresh the model list if it is old, then start the router and the agent team
    status         show what is running and which models are picked
    ask            test the whole chain:  harness ask [architect|implementer|reviewer] ["your question"]
    stop           stop the dashboard, the agent team and the router
    logs           show the last lines of a log:  harness logs [router|dashboard|oat]
    ui / ui-stop   start or stop only the dashboard
EOF
}

# Ask for one key, test it, save it. Return 0 when finished (saved, kept or skipped).
prompt_one_key() {
  local svc="$1" label saved new out rc msg ans tries=0
  label="$(nice_name "$svc")"
  while :; do
    saved="$(get_old "$(env_name "$svc")")"
    if [ -n "$saved" ]; then
      printf '%s key is saved. Paste a new key to replace it, or press Enter to keep it: ' "$label"
    else
      printf 'Paste your %s key (or press Enter to skip): ' "$label"
    fi
    IFS= read -r -s new
    printf '\n'
    new="$(printf '%s' "$new" | tr -d ' \r\n\t"\047')"
    if [ -z "$new" ]; then
      if [ -n "$saved" ]; then say "  kept the saved key."; else say "  skipped."; fi
      return 0
    fi
    say "  testing the key..."
    out="$(SCOUT_NEW_KEY="$new" scout_plain --set-key "$svc" 2>&1)"; rc=$?
    msg="$(printf '%s' "$out" | tail -1 | cut -f3-)"
    case $rc in
      0) say "  saved. ($msg)"; return 0 ;;
      2) say "  That key was refused: $msg"
         if [ -n "$saved" ]; then say "  Your old key was kept."; fi
         tries=$((tries + 1))
         if [ $tries -ge 3 ]; then say "  Giving up on $label for now. Run: harness set-key $svc"; return 0; fi
         say "  Check that you copied all of it and try again, or press Enter to skip." ;;
      3) say "  I could not check the key: $msg"
         printf '  Save it anyway? (y/N): '
         IFS= read -r ans
         case "$ans" in
           y|Y|yes|YES) out="$(SCOUT_NEW_KEY="$new" scout_plain --set-key "$svc" --force 2>&1)"
                        say "  saved without checking. Run 'harness check' when you are online."; return 0 ;;
           *) say "  not saved." ;;
         esac
         tries=$((tries + 1)); [ $tries -ge 3 ] && return 0 ;;
      *) say "  $out"; return 1 ;;
    esac
  done
}

cmd_setup_keys() {
  mkdir -p "$CONF_DIR" && chmod 700 "$CONF_DIR"
  [ -f "$SCOUT" ] || die "model_scout.py was not found in $HARNESS_DIR. Run: bash $HARNESS_DIR/install.sh"
  say "Let's save your free AI keys, one service at a time."
  say "Nothing you type is shown. Each key is tested before it is saved."
  say "Press Enter to skip a service, or to keep a key that is already saved."
  say ""
  local svc
  for svc in $SERVICES; do
    prompt_one_key "$svc"
    say ""
  done
  if [ "$(scout_plain --ensure-master)" = "created" ]; then say "A private router password was created for you (you never need to type it)."; fi
  cmd_keys
}

cmd_keys() {
  [ -f "$SCOUT" ] || die "model_scout.py was not found in $HARNESS_DIR."
  say "Service      Status      Key        Last result"
  scout_plain --keys-table | awk -F'\t' '{ printf "%-12s %-11s %-10s %s\n", $1, "[" $2 "]", $3, $4 }'
  say ""
  say "[ok] works   [skip] no key   [refused] key rejected   [offline] could not reach it"
  say "[limit] free allowance used up for now   [blocked] an account setting blocks free models"
  say "Replace a key: harness set-key NAME      Remove a key: harness remove-key NAME"
}

cmd_set_key() {
  local svc="${1:-}"
  valid_service "$svc" || die "tell me which service: harness set-key one of: $SERVICES"
  prompt_one_key "$svc"
}

cmd_remove_key() {
  local svc="${1:-}"
  valid_service "$svc" || die "tell me which service: harness remove-key one of: $SERVICES"
  scout_plain --remove-key "$svc" >/dev/null && say "The $(nice_name "$svc") key was removed. The old keys file is kept as $(basename "$KEYS").bak."
}

cmd_selftest() {
  [ -f "$SCOUT" ] || die "model_scout.py was not found in $HARNESS_DIR. Run: bash $HARNESS_DIR/install.sh"
  "$PYX" "$SCOUT" --selftest
}

cmd_check() { run_scout --check; }

cmd_scout() {
  run_scout --probe
  local rc=$?
  case $rc in
    0)  say "Done. Nothing changed in the model list." ;;
    10) say "Done. The model list changed."
        if router_up; then
          say "Restarting the router so it uses the new list..."
          stop_router
          start_router
        fi ;;
    *)  die "the model picker stopped with a problem (code $rc). Read the lines above. For a full check run: harness doctor" ;;
  esac
}

cmd_connect_oat() {
  need_keys
  local master f
  master="$(get_old LITELLM_MASTER_KEY)"
  [ -n "$master" ] || die "no router password was found. Run: harness setup-keys"
  f="$HOME/.oat/config.toml"
  mkdir -p "$HOME/.oat"
  if [ -f "$f" ] && ! grep -q '^# written by harness' "$f"; then
    die "$f already exists with other settings, so I did not touch it. Add the 'litellm' block shown in the guide under 'If connect-oat refuses' by hand."
  fi
  (
    umask 077
    cat > "$f" <<EOF
# written by harness connect-oat (safe to re-run)
[models.providers.litellm]
models = ["architect", "implementer", "reviewer"]
class_path = "langchain_openai:ChatOpenAI"

[models.providers.litellm.params]
base_url = "http://127.0.0.1:$PORT/v1"
api_key = "$master"
EOF
  )
  chmod 600 "$f"
  # OAT refuses to add a project unless it finds some provider key in ~/.oat/.env. Our models all go through the
  # router, so we give it the router password under the standard name (and point that name at the router).
  local envf="$HOME/.oat/.env" tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/harness-env.XXXXXX")" || die "could not create a temporary file"
  [ -f "$envf" ] && awk '/^# >>> harness/{skip=1} !skip{print} /^# <<< harness/{skip=0}' "$envf" > "$tmp"
  (
    umask 077
    {
      cat "$tmp"
      echo "# >>> harness (written by harness connect-oat; lets OAT's startup check pass; all models go through the router)"
      echo "OPENAI_API_KEY=$master"
      echo "OPENAI_BASE_URL=http://127.0.0.1:$PORT/v1"
      echo "# <<< harness"
    } > "$envf"
  )
  chmod 600 "$envf"
  rm -f "$tmp"
  say "Done. The agent team will now use the router. (Wrote $f and $envf)"
}

cmd_github_login() {
  local tok
  command -v gh >/dev/null 2>&1 || die "GitHub's 'gh' program is not installed. Run: harness doctor"
  say "Paste your GitHub token (it starts with github_pat_). Nothing is shown on screen."
  printf 'Token: '
  IFS= read -r -s tok
  printf '\n'
  tok="$(printf '%s' "$tok" | tr -d ' \r\n\t')"
  [ -n "$tok" ] || die "no token was entered."
  if ! printf '%s\n' "$tok" | gh auth login --with-token; then
    say ""
    say "GitHub did not accept the token. Check that you copied all of it."
    say "If you saw a message about GITHUB_TOKEN, run:  unset GITHUB_TOKEN   and try again."
    return 1
  fi
  gh auth setup-git >/dev/null 2>&1 && say "Git will now use this token too."
  gh auth status 2>&1 | head -4
  if gh repo view "$REPO" >/dev/null 2>&1; then
    say "OK: your token can see $REPO."
  else
    say "WARNING: your token cannot see $REPO. Check that you chose this repository when you made the token."
  fi
}

cmd_install_skills() {
  local src="$HARNESS_DIR/skills" dst="$HOME/.agents/skills" d n force="${1:-}"
  [ -d "$src" ] || die "no skills folder found in $HARNESS_DIR."
  mkdir -p "$dst"
  for d in "$src"/*/; do
    n="$(basename "$d")"
    if [ -e "$dst/$n" ] && [ "$force" != "--force" ]; then
      say "kept your existing skill: $n  (use 'harness install-skills --force' to overwrite)"
    else
      rm -rf "$dst/${n:?}"
      cp -R "$d" "$dst/$n"
      say "installed skill: $n"
    fi
  done
}

cmd_add_repo() {
  local url="${1:-}" name
  case "$url" in
    https://github.com/*/*) ;;
    *) die "give me the GitHub address, for example: harness add-repo https://github.com/owner/name" ;;
  esac
  command -v oat >/dev/null 2>&1 || die "the agent team (OAT) is not installed. Run: bash $HARNESS_DIR/install.sh"
  router_up || say "Note: the router is not running yet. Run 'harness start' before giving the team work."
  name="${url##*/}"; name="${name%.git}"
  start_oat
  if oat list 2>/dev/null | grep -qw "$name"; then
    say "OAT already knows the project '$name'."
  else
    oat init "$url" --no-merge-queue --model=litellm:architect || die "adding the project failed. Run 'harness doctor' and check your GitHub sign-in."
  fi
  oat config "$name" --mq-enabled=false 2>&1 | tail -2
  oat repo use "$name" 2>&1 | tail -1
  say "Done. The project '$name' is added, auto-merge is off, and it is now the default project."
}

cmd_start() {
  need_keys
  local rc
  if scout_is_old; then
    say "Refreshing the list of free models first (this can take a few minutes)..."
    run_scout --probe
    rc=$?
    case $rc in
      0|10) : ;;
      *) if [ -f "$CONFIG" ]; then
           say "Could not refresh the list, so I will use the previous one."
         else
           die "there is no model list yet and the model picker failed. Run: harness check"
         fi ;;
    esac
  fi
  start_router
  start_oat
  say ""
  say "All started. Check anytime with: harness status"
}

cmd_stop() {
  stop_ui
  if command -v oat >/dev/null 2>&1; then oat stop-all 2>&1 | tail -2; fi
  stop_router
  say "Stopped."
}

cmd_stop_team() {
  if command -v oat >/dev/null 2>&1; then oat stop-all 2>&1 | tail -2; fi
  stop_router
  say "Stopped the agent team and the router. (The dashboard is still running.)"
}

cmd_ui() {
  start_ui
  say "Dashboard: $(ui_url)"
  say "(Only this computer can open it. Keep the link private.)"
}

cmd_ui_stop() { stop_ui; say "Dashboard stopped."; }

cmd_open() {
  need_keys
  cmd_start
  start_ui
  local url
  url="$(ui_url)"
  say ""
  say "Dashboard: $url"
  if open_browser "$url"; then say "Opened in your browser."; else say "Open that address in your browser."; fi
  say ""
  say "Leave this window open while you work. Press Ctrl+C to close this window's wait loop"
  say "(the helpers keep running; stop everything with: harness stop)."
  trap 'say ""; say "Left the wait loop. Everything keeps running. Stop it with: harness stop"; exit 0' INT TERM
  while ui_up; do sleep 5; done
  say "The dashboard stopped."
}

cmd_status() {
  say "== Router (the front door to the free AI services) =="
  if router_up; then say "running at http://127.0.0.1:$PORT"; else say "NOT running  (start it with: harness start)"; fi
  say ""
  say "== Dashboard =="
  if ui_up; then say "running  (open it with: harness open)"; else say "not running  (start it with: harness open)"; fi
  say ""
  say "== Services and keys =="
  if [ -f "$SCOUT" ]; then scout_plain --keys-table | awk -F'\t' '{ printf "%-12s %-11s %s\n", $1, "[" $2 "]", $4 }'; fi
  say ""
  say "== Current model picks (best first) =="
  if [ -f "$STATE" ]; then
    "$PYX" - "$STATE" <<'PYEOF'
import json, sys
try:
    st = json.load(open(sys.argv[1]))
except Exception:
    st = {}
sel, rs = st.get("selected") or {}, st.get("role_status") or {}
if not sel:
    print("none yet  (run: harness scout)")
for role, keys in sel.items():
    note = {"borrowed": "  (borrowing from other roles)", "unavailable": "  (UNAVAILABLE)"}.get(rs.get(role, ""), "")
    print(f"{role:12} " + ("  >  ".join(keys) if keys else "-") + note)
PYEOF
  else
    say "none yet  (run: harness scout)"
  fi
  say ""
  say "== Agent team (OAT) =="
  if command -v oat >/dev/null 2>&1; then
    oat daemon status 2>&1 | head -3
    local workers
    workers="$(oat worker list --repo "$OAT_REPO" 2>&1)"
    case "$workers" in
      *"not in a tracked"*|*"not found"*|*"unknown"*|*"No such"*|*"no repository"*)
        say "The project '$OAT_REPO' is not added yet. Run: harness add-repo https://github.com/$REPO" ;;
      *) printf '%s\n' "$workers" | head -15 ;;
    esac
  else
    say "not installed yet. Run: bash $HARNESS_DIR/install.sh"
  fi
}

cmd_ask() {
  local role="${1:-implementer}" prompt="${2:-Say hello in five words.}"
  need_keys
  router_up || die "the router is not running. Run: harness start"
  with_keys "$PYX" - "$PORT" "$role" "$prompt" "$STATE" <<'PYEOF'
import json, os, re, sys, urllib.error, urllib.request
port, role, prompt, state = sys.argv[1:5]
body = {"model": role, "messages": [{"role": "user", "content": prompt}], "max_tokens": 400}
req = urllib.request.Request(
    f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
    headers={"Authorization": "Bearer " + os.environ["LITELLM_MASTER_KEY"], "Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=180)
    r = json.load(resp)
    text = (r["choices"][0]["message"].get("content") or "").strip()
    print("Reply:", text or "(empty - the model may have used all its words thinking; try again)")
    who = resp.headers.get("x-litellm-model-id") or ""
    m = re.fullmatch(r"([a-z]+)-(\d+)", who)
    if m:
        n = int(m.group(2))
        name = ""
        try:
            name = json.load(open(state)).get("selected", {}).get(m.group(1), [])[n - 1]
        except Exception:
            pass
        print("Answered by:", (name + " " if name else "") + ("(first choice)" if n == 1 else f"(backup number {n - 1})"))
except urllib.error.HTTPError as e:
    print("The router answered with an error:", e.code, e.read().decode()[:400])
    sys.exit(1)
except Exception as e:
    print("Could not reach the router:", e)
    sys.exit(1)
PYEOF
}

cmd_logs() {
  case "${1:-router}" in
    router) tail -40 "$LOGFILE" 2>/dev/null || say "No router log yet." ;;
    dashboard|ui) tail -40 "$UI_LOG" 2>/dev/null || say "No dashboard log yet." ;;
    oat) tail -40 "$HOME/.oat/daemon.log" 2>/dev/null || say "No agent-team log yet." ;;
    *) die "use: harness logs router | dashboard | oat" ;;
  esac
}

cmd_doctor() {
  local bad=0 v
  ok() { printf '[OK]    %s\n' "$*"; }
  info() { printf '[info]  %s\n' "$*"; }
  fix() { printf '[FIX]   %s\n          -> %s\n' "$1" "$2"; bad=$((bad + 1)); }
  say "Checking every part of the AI team..."
  say ""
  if [ "$(id -u)" = "0" ]; then fix "You are running as the administrator (root)" "make a normal user for the helpers (see the guide, section Keep it separate)"; else ok "running as a normal user ($(id -un))"; fi
  if grep -qi microsoft /proc/version 2>/dev/null; then info "Windows (WSL) detected"; elif [ "$(uname)" = "Darwin" ]; then info "macOS detected"; elif [ -n "${CODESPACES:-}" ]; then info "GitHub Codespace detected"; else info "Linux detected"; fi
  for v in git curl gh uv; do
    if command -v "$v" >/dev/null 2>&1; then ok "$v is installed"; else fix "$v is missing" "run: bash $HARNESS_DIR/install.sh (it tells you the exact command)"; fi
  done
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then ok "python3 is 3.11 or newer"; else fix "python3 is older than 3.11 or missing" "install a newer Python (Ubuntu 24.04 has 3.12)"; fi
  if gh auth status >/dev/null 2>&1; then ok "signed in to GitHub"; else fix "not signed in to GitHub" "run: harness github-login"; fi
  if [ -x "$VENV/bin/litellm" ]; then ok "the router (LiteLLM) is installed"; else fix "the router is not installed" "run: bash $HARNESS_DIR/install.sh"; fi
  if command -v oat >/dev/null 2>&1; then ok "the agent team (OAT) is installed ($(oat version 2>/dev/null | head -1))"; else fix "the agent team (OAT) is not installed" "run: bash $HARNESS_DIR/install.sh"; fi
  for v in model_scout.py harness_ui.py; do
    if [ -f "$HARNESS_DIR/$v" ]; then ok "$v is in place"; else fix "$v is missing from $HARNESS_DIR" "unzip the kit again into your home folder"; fi
  done
  if [ -f "$KEYS" ] && [ -f "$SCOUT" ]; then
    local saved refused
    saved="$(scout_plain --keys-table | awk -F'\t' '$3 != "" {n++} END {print n+0}')"
    refused="$(scout_plain --keys-table | awk -F'\t' '$2 == "refused" {n++} END {print n+0}')"
    if [ "$saved" -ge 1 ]; then ok "$saved AI key(s) saved"; else fix "no AI key saved" "run: harness setup-keys"; fi
    [ "$refused" -ge 1 ] && fix "$refused saved key(s) were refused" "run: harness keys   then   harness set-key NAME"
  else
    fix "no keys file yet" "run: harness setup-keys"
  fi
  if [ -f "$CONFIG" ]; then ok "the router's model list exists"; else fix "no model list yet" "run: harness scout"; fi
  if [ -f "$STATE" ]; then
    "$PYX" - "$STATE" <<'PYEOF'
import json, sys
st = json.load(open(sys.argv[1])) if True else {}
rs = st.get("role_status") or {}
bad = [r for r, s in rs.items() if s == "unavailable"]
bor = [r for r, s in rs.items() if s == "borrowed"]
if bad:
    print("[FIX]   no working model for: " + ", ".join(bad) + "\n          -> run: harness check   (look for [offline] or [refused])")
if bor:
    print("[info]  borrowing models from other roles for: " + ", ".join(bor))
PYEOF
  fi
  if [ -f "$HOME/.oat/config.toml" ] && grep -q "providers.litellm" "$HOME/.oat/config.toml"; then ok "the agent team knows the router"; else fix "the agent team does not know the router" "run: harness connect-oat"; fi
  if [ -d "$HOME/.agents/skills/team-workflow" ]; then ok "built-in skills installed"; else fix "built-in skills are not installed" "run: harness install-skills"; fi
  if router_up; then ok "the router is running"; else info "the router is not running (harness start)"; fi
  if command -v oat >/dev/null 2>&1; then
    if oat daemon status 2>&1 | grep -q "Running: true"; then ok "the agent team is running"; else info "the agent team is not running (harness start)"; fi
    if oat list 2>/dev/null | grep -qw "$OAT_REPO"; then ok "the project '$OAT_REPO' is added"; else fix "the project '$OAT_REPO' is not added" "run: harness add-repo https://github.com/$REPO"; fi
  fi
  if ui_up; then ok "the dashboard is running"; else info "the dashboard is not running (harness open)"; fi
  say ""
  if [ "$bad" -eq 0 ]; then say "Everything looks good."; else say "$bad thing(s) to fix. Do them from the top; run 'harness doctor' again after each."; fi
}

case "${1:-help}" in
  open)          cmd_open ;;
  setup-keys)    cmd_setup_keys ;;
  keys)          cmd_keys ;;
  set-key)       shift; cmd_set_key "$@" ;;
  remove-key)    shift; cmd_remove_key "$@" ;;
  selftest)      cmd_selftest ;;
  check)         cmd_check ;;
  scout)         cmd_scout ;;
  connect-oat)   cmd_connect_oat ;;
  github-login)  cmd_github_login ;;
  install-skills) shift; cmd_install_skills "$@" ;;
  add-repo)      shift; cmd_add_repo "$@" ;;
  start)         cmd_start ;;
  stop)          cmd_stop ;;
  stop-team)     cmd_stop_team ;;
  status)        cmd_status ;;
  ask)           shift; cmd_ask "$@" ;;
  logs)          shift; cmd_logs "$@" ;;
  ui)            cmd_ui ;;
  ui-stop)       cmd_ui_stop ;;
  doctor)        cmd_doctor ;;
  help|-h|--help) cmd_help ;;
  *)             say "Unknown command: $1"; say ""; cmd_help; exit 1 ;;
esac
