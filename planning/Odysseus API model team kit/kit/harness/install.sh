#!/usr/bin/env bash
# One-time installer for the AI team kit. Safe to run again.
#   Run:  bash ~/harness/install.sh
# It installs the router (LiteLLM) and the agent team (OAT), puts the "harness" command in place and
# installs the built-in skills. It never uses sudo: if something is missing it tells you the exact command.

HARNESS_DIR="${HARNESS_DIR:-$HOME/harness}"
VENV="${LITELLM_VENV:-$HOME/litellm-env}"
OAT_VERSION="${OAT_VERSION:-v0.1.0}"
OAT_INSTALLER_URL="https://raw.githubusercontent.com/Root-IO-Labs/open-agent-teams/main/install.sh"
export PATH="$HOME/.local/bin:$PATH"

say() { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
good() { printf '[OK]   %s\n' "$*"; }
stop_here() { printf '\n[STOP] %s\n' "$*" >&2; exit 1; }

say "AI team installer"
say "This takes about 5 to 10 minutes. Most of it is waiting for downloads."

# ---------------------------------------------------------------- 1. where are we?
step "1/6  Checking your computer"
OS="$(uname -s)"
case "$OS" in
  Linux|Darwin) ;;
  *) stop_here "This installer is for Linux, Mac or Windows with Ubuntu (WSL). See the guide, Step 1." ;;
esac
if [ "$(id -u)" = "0" ] && [ "${HARNESS_ALLOW_ROOT:-}" != "1" ]; then
  stop_here "You are the administrator (root). The helpers can run commands as whoever installs them, so use a normal user.
       Make one:  adduser aiteam   then:  su - aiteam   and run this installer again. (Guide: 'Keep it separate'.)"
fi
[ -f "$HARNESS_DIR/harness.sh" ] || stop_here "I cannot find $HARNESS_DIR/harness.sh. Unzip the kit into your home folder first (see the guide)."
good "$OS, user $(id -un)"

# ---------------------------------------------------------------- 2. needed programs
step "2/6  Checking the programs we need"
missing=""
for p in git curl python3 gh; do
  if command -v "$p" >/dev/null 2>&1; then good "$p is installed"; else missing="$missing $p"; fi
done
if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    good "python3 is $(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])') (3.11 or newer is needed)"
  else
    stop_here "python3 is older than 3.11. On Windows, install a newer Ubuntu: wsl --install -d Ubuntu-24.04. On Mac: brew install python."
  fi
  if ! python3 -c 'import venv, ensurepip' 2>/dev/null; then missing="$missing python3-venv"; fi
fi
if [ -n "$missing" ]; then
  say ""
  if [ "$OS" = "Darwin" ]; then
    stop_here "Missing:$missing
       Run this, then run the installer again:   brew install git gh python"
  fi
  stop_here "Missing:$missing
       Run this, then run the installer again:
         sudo apt update && sudo apt install -y git curl python3 python3-venv gh"
fi

if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv (a small helper that OAT uses) from its official site..."
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 || stop_here "Could not install uv. Check your internet connection and try again."
  export PATH="$HOME/.local/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 && good "uv is installed" || stop_here "uv is still missing. Run:  curl -LsSf https://astral.sh/uv/install.sh | sh"

# ---------------------------------------------------------------- 3. harness command + PATH
step "3/6  Setting up the harness command"
chmod +x "$HARNESS_DIR/harness.sh"
mkdir -p "$HOME/.local/bin"
ln -sf "$HARNESS_DIR/harness.sh" "$HOME/.local/bin/harness"
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ "$rc" = "$HOME/.zshrc" ] && [ "$OS" != "Darwin" ] && [ ! -f "$rc" ]; then continue; fi
  if ! grep -q 'gifscythe-harness PATH' "$rc" 2>/dev/null; then
    printf '\n# gifscythe-harness PATH\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
  fi
done
good "typing 'harness' now works (open a new terminal window, or run: source ~/.bashrc)"

# ---------------------------------------------------------------- 4. router
step "4/6  Installing the router (LiteLLM). This is the slow part: 3 to 6 minutes"
if [ -x "$VENV/bin/litellm" ]; then
  good "the router is already installed"
else
  python3 -m venv "$VENV" || stop_here "Could not make the router's folder. On Ubuntu run: sudo apt install -y python3-venv"
  "$VENV/bin/pip" install --quiet --disable-pip-version-check "litellm[proxy]" || stop_here "Downloading the router failed. Check your internet connection and run this installer again."
  [ -x "$VENV/bin/litellm" ] && good "the router is installed" || stop_here "The router did not install. Run the installer again."
fi

# ---------------------------------------------------------------- 5. agent team
step "5/6  Installing the agent team (OAT $OAT_VERSION)"
if command -v oat >/dev/null 2>&1 && oat version 2>/dev/null | grep -q "${OAT_VERSION#v}"; then
  good "OAT is already installed ($(oat version 2>/dev/null | head -1))"
else
  tmp="$(mktemp "${TMPDIR:-/tmp}/oat-install.XXXXXX")" || stop_here "Could not create a temporary file."
  curl -fsSL "$OAT_INSTALLER_URL" -o "$tmp" || { rm -f "$tmp"; stop_here "Could not download OAT's installer. Check your internet connection."; }
  OAT_VERSION="$OAT_VERSION" bash "$tmp" </dev/null 2>&1 | grep -v "tmpdir: unbound variable" | tail -4
  rm -f "$tmp"
  export PATH="$HOME/.local/bin:$PATH"
  if command -v oat >/dev/null 2>&1; then good "OAT is installed ($(oat version 2>/dev/null | head -1))"; else stop_here "OAT did not install. Run this installer again, or ask for help with the message above."; fi
fi

# ---------------------------------------------------------------- 6. skills + windows shortcuts
step "6/6  Skills and shortcuts"
"$HARNESS_DIR/harness.sh" install-skills
if grep -qi microsoft /proc/version 2>/dev/null && command -v powershell.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
  desk="$(powershell.exe -NoProfile -Command '[Environment]::GetFolderPath("Desktop")' 2>/dev/null | tr -d '\r')"
  if [ -n "$desk" ] && deskl="$(wslpath "$desk" 2>/dev/null)" && [ -d "$deskl" ]; then
    for f in "$HARNESS_DIR"/windows/*.bat; do
      sed -e "s/set \"WSL_USER=\"/set \"WSL_USER=$(id -un)\"/" -e "s/set \"WSL_DISTRO=\"/set \"WSL_DISTRO=${WSL_DISTRO_NAME:-}\"/" "$f" > "$deskl/$(basename "$f")"
    done
    good "put 'Start AI Team' and 'Stop AI Team' on your Windows desktop (set up for user $(id -un))"
  else
    say "To get the double-click shortcuts on your Windows desktop, run:"
    say "  cp ~/harness/windows/*.bat /mnt/c/Users/YOURNAME/Desktop/"
  fi
fi

say ""
say "All installed. Next steps (each one is explained in the guide):"
say "  1.  harness setup-keys      save your free AI keys"
say "  2.  harness github-login    sign in to GitHub"
say "  3.  harness connect-oat     connect the agent team to the router"
say "  4.  harness start           start the router and the agent team (the first time it also picks free models)"
say "  5.  harness add-repo https://github.com/OWNER/NAME"
say "  6.  harness open            start everything and open the dashboard"
say ""
say "Not sure what is missing at any point?  Run:  harness doctor"
