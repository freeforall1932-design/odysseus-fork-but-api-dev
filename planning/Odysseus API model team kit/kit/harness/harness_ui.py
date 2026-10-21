#!/usr/bin/env python3
"""harness_ui.py - the AI team dashboard: a small web page that runs only on your own computer.

Start it with:  harness open      (or: harness ui)
It needs nothing but Python 3.9+ (no extra packages). It talks to the same tools you would type:
  oat (the agent team), gh (GitHub), git, and the model picker (model_scout.py).

Safety: it listens on 127.0.0.1 only, needs the secret link printed by `harness ui`, refuses other
website names (DNS rebinding), and refuses requests that did not come from its own page (CSRF).
Your AI keys are never sent to the page and never put in the helpers' environment.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model_scout as ms  # noqa: E402

VERSION = "1.0"
HOME = Path(os.environ.get("HOME") or Path.home())
KEYS = Path(os.environ.get("HARNESS_KEYS") or HOME / ".config/gifscythe-harness/keys.env")
CONF_DIR = KEYS.parent
TOKEN_FILE = CONF_DIR / "ui-token"
CHAT_FILE = CONF_DIR / "ui-chat.json"
OAT_HOME = Path(os.environ.get("OAT_HOME") or HOME / ".oat")
PORT = int(os.environ.get("GIFSCYTHE_UI_PORT", "8765"))
ROUTER_PORT = int(os.environ.get("LITELLM_PORT", "4000"))
STATE_FILE = HERE / "scout_state.json"
REPORT_FILE = HERE / "scout_report.md"
SCOUT_CFG = HERE / "scout.yaml"
HARNESS = os.environ.get("HARNESS_BIN") or shutil.which("harness") or str(HERE / "harness.sh")
SKILLS_DIR = HOME / ".agents" / "skills"
ALLOW_LOCAL_URLS = os.environ.get("GIFSCYTHE_ALLOW_LOCAL_URLS") == "1"
SECRET_ENV = ("OPENROUTER_API_KEY", "NVIDIA_API_KEY", "MISTRAL_API_KEY", "GEMINI_API_KEY", "LITELLM_MASTER_KEY")
ROLES = ("architect", "implementer", "reviewer")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
GH_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Za-z0-9]|\x1b[=>MNOPXZc78]")


class ApiError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


# --------------------------------------------------------------------------- helpers
def clean_env() -> dict:
    """Environment for programs we start: your AI keys are NOT included."""
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV}
    env["PATH"] = f"{HOME}/.local/bin:" + env.get("PATH", "")
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def run(args: list, timeout: int = 25, cwd: Optional[str] = None, input_text: Optional[str] = None) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=clean_env(),
                           input=input_text, errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except FileNotFoundError:
        return 127, f"{args[0]} was not found"
    except OSError as e:
        return 126, str(e)


def clean_term(text: str) -> str:
    text = ANSI.sub("", text)
    lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if "\r" in line:
            line = line.split("\r")[-1]  # a redraw: keep the last version of the line
        lines.append("".join(ch for ch in line if ch == "\t" or ch >= " ").rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip("\n")


def check_name(name: str, what: str = "name") -> str:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ApiError(400, f"that {what} is not valid")
    return name


def safe_join(base: Path, rel: str) -> Path:
    base = base.resolve()
    p = (base / (rel or "").lstrip("/")).resolve()
    if p != base and base not in p.parents:
        raise ApiError(400, "that path is outside the project")
    return p


def http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310  # nosec B310 - fixed local address
            return 200 <= r.status < 300
    except Exception:  # noqa: BLE001
        return False


_CACHE: dict[str, tuple[float, Any]] = {}


def cached(key: str, ttl: float, fn: Callable[[], Any]) -> Any:
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    val = fn()
    _CACHE[key] = (now, val)
    return val


def read_json(path: Path, default: Any) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def oat_state() -> dict:
    st = read_json(OAT_HOME / "state.json", {})
    return st if isinstance(st, dict) else {}


def repo_info(name: str) -> dict:
    check_name(name, "project name")
    r = (oat_state().get("repos") or {}).get(name)
    if not isinstance(r, dict):
        raise ApiError(404, f"the agent team does not know a project called '{name}'")
    return r


def owner_repo(url: str) -> str:
    m = GH_URL_RE.match(url or "")
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def daemon_running() -> bool:
    try:
        pid = int((OAT_HOME / "daemon.pid").read_text().strip())
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except Exception:  # noqa: BLE001
        return False


def token() -> str:
    try:
        t = TOKEN_FILE.read_text().strip()
        if t:
            return t
    except OSError:
        pass
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    t = secrets.token_urlsafe(24)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(t)
    return t


def scout_cfg() -> dict:
    try:
        return ms.load_config(str(SCOUT_CFG))
    except Exception:  # noqa: BLE001
        return ms.deep_merge(ms.DEFAULTS, {})


def front_matter(path: Path) -> dict:
    out: dict = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:6000]
    except OSError:
        return out
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip().strip("'\"")
    return out


# --------------------------------------------------------------------------- jobs
JOBS: dict[str, dict] = {}
JOB_ACTIONS = {
    "start": ("Starting the router and the agent team", ["start"]),
    "stop": ("Stopping the router and the agent team", ["stop-team"]),
    "scout": ("Refreshing the free models", ["scout"]),
    "check": ("Checking your keys", ["check"]),
    "doctor": ("Checking every part", ["doctor"]),
    "install-skills": ("Installing the built-in skills", ["install-skills"]),
}


def start_job(title: str, args: list) -> str:
    jid = secrets.token_hex(4)
    job: dict[str, Any] = {"id": jid, "title": title, "started": time.time(), "status": "running", "rc": None, "lines": []}
    JOBS[jid] = job
    for old in sorted(JOBS.values(), key=lambda j: j["started"])[:-12]:
        JOBS.pop(old["id"], None)

    def work() -> None:
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                 env=clean_env(), stdin=subprocess.DEVNULL, errors="replace")
            assert p.stdout is not None
            for line in p.stdout:
                job["lines"].append(clean_term(line.rstrip("\n")))
                del job["lines"][:-600]
            p.wait()
            job["rc"] = p.returncode
        except Exception as e:  # noqa: BLE001
            job["lines"].append(f"could not run: {e}")
            job["rc"] = 1
        job["status"] = "done" if job["rc"] in (0, 10) else "failed"
        job["ended"] = time.time()

    threading.Thread(target=work, daemon=True).start()
    return jid


# --------------------------------------------------------------------------- chat history (kept on this computer)
_CHAT_LOCK = threading.Lock()


def chat_load() -> dict:
    d = read_json(CHAT_FILE, {})
    return d if isinstance(d, dict) else {}


def chat_add(repo: str, text: str, offset: int) -> None:
    with _CHAT_LOCK:
        d = chat_load()
        d.setdefault(repo, []).append({"text": text, "ts": time.time(), "offset": offset})
        d[repo] = d[repo][-200:]
        CONF_DIR.mkdir(parents=True, exist_ok=True)
        tmp = str(CHAT_FILE) + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(tmp, CHAT_FILE)


def workspace_agent(repo: str) -> str:
    for name, a in (repo_info(repo).get("agents") or {}).items():
        if isinstance(a, dict) and a.get("type") == "workspace":
            return name
    return "workspace"


def agent_log_path(repo: str, agent: str, worker: bool = False) -> Path:
    base = OAT_HOME / "output" / repo
    return (base / "workers" / f"{agent}.log") if worker else (base / f"{agent}.log")


# --------------------------------------------------------------------------- API: state
def checklist(st: dict) -> list:
    keys_ok = any(r["status"] in ("ok", "limit", "blocked", "warn") for r in st["services"])
    sel = st.get("picks") or {}
    return [
        {"id": "keys", "label": "Add at least one free AI key", "ok": keys_ok,
         "hint": "Open Connections and paste a key. It is tested before it is saved.", "action": "tab:connections"},
        {"id": "models", "label": "Pick the best free models", "ok": bool(sel),
         "hint": "Press Refresh models (it takes a few minutes the first time).", "action": "job:scout"},
        {"id": "router", "label": "Start the router", "ok": st["router"]["up"],
         "hint": "Press Start.", "action": "job:start"},
        {"id": "github", "label": "Connect GitHub", "ok": bool(st["github"]["ok"]),
         "hint": "Open Connections and paste your GitHub token.", "action": "tab:connections"},
        {"id": "repo", "label": "Add your project", "ok": bool(st["repos"]),
         "hint": "Use 'Add project' on the left and paste the GitHub address.", "action": "add-repo"},
        {"id": "team", "label": "Start the agent team", "ok": st["daemon"],
         "hint": "Press Start.", "action": "job:start"},
    ]


def gh_status() -> dict:
    rc, out = run(["gh", "auth", "status"], timeout=15)
    m = re.search(r"account (\S+)", out)
    return {"ok": rc == 0, "user": m.group(1) if m else "", "msg": "" if rc == 0 else "not signed in"}


def api_state(q: dict, b: dict) -> dict:
    cfg = scout_cfg()
    oat = oat_state()
    repos = []
    for name, r in (oat.get("repos") or {}).items():
        if isinstance(r, dict):
            repos.append({"name": name, "url": r.get("github_url", ""), "owner_repo": owner_repo(r.get("github_url", "")),
                          "model": r.get("model", ""), "idle": bool(r.get("idle_mode"))})
    current = oat.get("current_repo") or ""
    want = (q.get("repo") or [""])[0]
    if want and any(r["name"] == want for r in repos):
        current = want
    if not any(r["name"] == current for r in repos):
        current = repos[0]["name"] if repos else ""
    agents, history = [], []
    if current:
        r = (oat.get("repos") or {}).get(current) or {}
        for name, a in (r.get("agents") or {}).items():
            if isinstance(a, dict):
                agents.append({"name": name, "type": a.get("type", ""), "task": a.get("task", ""),
                               "summary": a.get("summary", ""), "pr": a.get("pr_number", 0), "model": a.get("model", ""),
                               "tokens": a.get("total_tokens", 0), "created": a.get("created_at", ""),
                               "waiting_for_pr": bool(a.get("waiting_for_pr")),
                               "verification": a.get("verification_status", ""),
                               "has_tree": bool(a.get("worktree_path")) and Path(a.get("worktree_path", "")).is_dir()})
        agents.sort(key=lambda a: a["created"], reverse=True)
        history = list(reversed((r.get("task_history") or [])[-20:]))
    sc = ms.load_state(str(STATE_FILE))
    state = {
        "time": time.time(), "version": VERSION, "repos": repos, "current": current, "agents": agents,
        "history": history,
        "router": {"up": http_ok(f"http://127.0.0.1:{ROUTER_PORT}/health/liveliness"), "port": ROUTER_PORT},
        "daemon": daemon_running(),
        "github": cached("gh", 45, gh_status),
        "services": ms.keys_table(cfg, str(KEYS), str(STATE_FILE)),
        "picks": sc.get("selected") or {}, "role_status": sc.get("role_status") or {}, "models_updated": sc.get("updated", 0),
        "jobs": [{"id": j["id"], "title": j["title"], "status": j["status"]}
                 for j in sorted(JOBS.values(), key=lambda j: -j["started"])[:5]],
    }
    state["setup"] = checklist(state)
    return state


# --------------------------------------------------------------------------- API: keys and connections
def tavily_saved() -> bool:
    try:
        return bool(re.search(r"^TAVILY_API_KEY=.+$", (OAT_HOME / ".env").read_text(), re.M))
    except OSError:
        return False


def api_keys(q: dict, b: dict) -> dict:
    return {"services": ms.keys_table(scout_cfg(), str(KEYS), str(STATE_FILE)),
            "extras": [{"name": "tavily", "label": "Web search (Tavily)", "saved": tavily_saved()}]}


def set_env_line(path: Path, key: str, value: str) -> None:
    lines = []
    try:
        lines = path.read_text().splitlines()
    except OSError:
        pass
    lines = [ln for ln in lines if not ln.startswith(key + "=")]
    if value:
        lines.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")


def api_key_set(q: dict, b: dict) -> dict:
    service, key = str(b.get("service", "")), str(b.get("key", ""))
    if service == "tavily":
        key = ms.normalize_key(key)
        if not key:
            raise ApiError(400, "no key was entered")
        set_env_line(OAT_HOME / ".env", "TAVILY_API_KEY", key)
        return {"saved": True, "status": "ok", "message": "saved. Restart the agent team (Stop, then Start) so helpers can use web search."}
    saved, status, msg = ms.set_key(scout_cfg(), ms.IO(), service, key, str(KEYS), str(STATE_FILE), bool(b.get("force")))
    return {"saved": saved, "status": status, "message": msg}


def api_key_remove(q: dict, b: dict) -> dict:
    service = str(b.get("service", ""))
    if service == "tavily":
        set_env_line(OAT_HOME / ".env", "TAVILY_API_KEY", "")
        return {"ok": True}
    ok, msg = ms.remove_key(scout_cfg(), service, str(KEYS), str(STATE_FILE), time.time())
    if not ok:
        raise ApiError(400, msg)
    return {"ok": True}


def api_github_login(q: dict, b: dict) -> dict:
    tok = re.sub(r"\s", "", str(b.get("token", "")))
    if not tok:
        raise ApiError(400, "no token was entered")
    rc, out = run(["gh", "auth", "login", "--with-token"], input_text=tok + "\n", timeout=30)
    _CACHE.pop("gh", None)
    if rc != 0:
        return {"ok": False, "message": "GitHub did not accept the token. Check that you copied all of it. " + out.strip()[:200]}
    return {"ok": True, "message": "signed in", "github": cached("gh", 0, gh_status)}


# --------------------------------------------------------------------------- API: chat and tasks
def api_chat_send(q: dict, b: dict) -> dict:
    repo, text = str(b.get("repo", "")), str(b.get("text", "")).strip()
    repo_info(repo)
    if not text or len(text) > 6000:
        raise ApiError(400, "type a message (up to 6000 characters)")
    agent = workspace_agent(repo)
    try:
        offset = agent_log_path(repo, agent).stat().st_size
    except OSError:
        offset = 0
    rc, out = run(["oat", "agent", "tell", agent, text, "--repo", repo], timeout=25)
    if rc != 0:
        raise ApiError(502, "the agent team did not take the message: " + clean_term(out)[:300] +
                       "  (Is the team running? Press Start.)")
    chat_add(repo, text, offset)
    return {"ok": True}


def api_chat(q: dict, b: dict) -> dict:
    repo = (q.get("repo") or [""])[0]
    repo_info(repo)
    agent = workspace_agent(repo)
    path = agent_log_path(repo, agent)
    msgs = chat_load().get(repo, [])
    try:
        size = path.stat().st_size
    except OSError:
        return {"agent": agent, "log_exists": False, "messages": [{"role": "user", "text": m["text"]} for m in msgs[-20:]]}
    start = max(0, size - 80000)
    with open(path, "rb") as f:
        f.seek(start)
        raw = f.read(size - start)  # bytes: your messages were placed by byte position
    marks = [m for m in msgs if m.get("offset", 0) >= start]
    out: list = []
    prev = 0
    for m in marks:
        seg_end = max(prev, min(len(raw), m["offset"] - start))
        seg = clean_term(raw[prev:seg_end].decode("utf-8", errors="replace"))
        if seg:
            out.append({"role": "agent", "text": seg})
        out.append({"role": "user", "text": m["text"]})
        prev = seg_end
    tail = clean_term(raw[prev:].decode("utf-8", errors="replace"))
    if tail:
        out.append({"role": "agent", "text": tail})
    return {"agent": agent, "log_exists": True, "truncated": start > 0, "messages": out[-60:]}


def api_task(q: dict, b: dict) -> dict:
    repo, text, role = str(b.get("repo", "")), str(b.get("text", "")).strip(), str(b.get("role", "implementer"))
    repo_info(repo)
    if role not in ROLES:
        raise ApiError(400, "choose architect, implementer or reviewer")
    if not text or len(text) > 6000:
        raise ApiError(400, "describe the task (up to 6000 characters)")
    rc, out = run(["oat", "worker", "create", text, "--model", f"litellm:{role}", "--repo", repo], timeout=40)
    if rc != 0:
        raise ApiError(502, clean_term(out)[:400] or "the agent team did not accept the task")
    return {"ok": True, "message": clean_term(out)[:400]}


def api_ask(q: dict, b: dict) -> dict:
    role, text = str(b.get("role", "implementer")), str(b.get("text", "")).strip()
    if role not in ROLES or not text:
        raise ApiError(400, "choose a role and type a question")
    master = ms.read_keys(str(KEYS)).get("LITELLM_MASTER_KEY", "")
    if not master:
        raise ApiError(400, "no router password yet. Run: harness setup-keys")
    body = json.dumps({"model": role, "messages": [{"role": "user", "content": text}], "max_tokens": 800}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{ROUTER_PORT}/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {master}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310  # nosec B310 - fixed local address
            data = json.loads(r.read().decode("utf-8", "replace"))
            who = r.headers.get("x-litellm-model-id") or ""
    except urllib.error.HTTPError as e:
        raise ApiError(502, "the router answered " + str(e.code) + ": " + e.read().decode("utf-8", "replace")[:300]) from None
    except Exception as e:  # noqa: BLE001
        raise ApiError(502, f"could not reach the router ({e}). Press Start.") from None
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    answered = ""
    m = re.fullmatch(r"([a-z]+)-(\d+)", who)
    if m:
        picks = (ms.load_state(str(STATE_FILE)).get("selected") or {}).get(m.group(1), [])
        n = int(m.group(2))
        answered = (picks[n - 1] if 0 < n <= len(picks) else "") + (" (first choice)" if n == 1 else f" (backup {n - 1})")
    return {"text": ms.as_text(msg.get("content")).strip() or "(empty answer - try again)", "answered_by": answered.strip()}


# --------------------------------------------------------------------------- API: jobs
def api_job_start(q: dict, b: dict) -> dict:
    action = str(b.get("action", ""))
    if action == "add-repo":
        url = str(b.get("url", "")).strip()
        if not GH_URL_RE.match(url):
            raise ApiError(400, "paste a GitHub address like https://github.com/owner/name")
        return {"id": start_job("Adding the project", [HARNESS, "add-repo", url])}
    if action not in JOB_ACTIONS:
        raise ApiError(400, "unknown action")
    title, args = JOB_ACTIONS[action]
    return {"id": start_job(title, [HARNESS, *args])}


def api_job(q: dict, b: dict) -> dict:
    j = JOBS.get((q.get("id") or [""])[0])
    if not j:
        raise ApiError(404, "unknown job")
    return {k: j.get(k) for k in ("id", "title", "status", "rc")} | {"lines": j["lines"][-300:]}


def api_repo_use(q: dict, b: dict) -> dict:
    name = check_name(str(b.get("name", "")), "project name")
    repo_info(name)
    rc, out = run(["oat", "repo", "use", name], timeout=15)
    return {"ok": rc == 0, "message": clean_term(out)[:200]}


# --------------------------------------------------------------------------- API: files and changes
def tree_base(repo: str, tree: str) -> Path:
    info = repo_info(repo)
    if tree in ("", "main"):
        p = OAT_HOME / "repos" / repo
    else:
        a = (info.get("agents") or {}).get(check_name(tree, "helper name"))
        if not isinstance(a, dict) or not a.get("worktree_path"):
            raise ApiError(404, "that helper has no working copy")
        p = Path(a["worktree_path"])
    if not p.is_dir():
        raise ApiError(404, "that working copy is not on this computer (yet)")
    return p


def api_files(q: dict, b: dict) -> dict:
    repo, tree, rel = (q.get("repo") or [""])[0], (q.get("tree") or ["main"])[0], (q.get("path") or [""])[0]
    base = tree_base(repo, tree)
    d = safe_join(base, rel)
    if not d.is_dir():
        raise ApiError(404, "not a folder")
    out = []
    for e in sorted(d.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if e.name == ".git":
            continue
        try:
            out.append({"name": e.name, "type": "dir" if e.is_dir() else "file", "size": 0 if e.is_dir() else e.stat().st_size})
        except OSError:
            continue
        if len(out) >= 500:
            break
    return {"path": str(d.relative_to(base.resolve())) if d != base.resolve() else "", "entries": out}


def api_file(q: dict, b: dict) -> dict:
    repo, tree, rel = (q.get("repo") or [""])[0], (q.get("tree") or ["main"])[0], (q.get("path") or [""])[0]
    f = safe_join(tree_base(repo, tree), rel)
    if not f.is_file():
        raise ApiError(404, "not a file")
    size = f.stat().st_size
    with open(f, "rb") as fh:
        raw = fh.read(300_000)
    if b"\x00" in raw[:4096]:
        return {"binary": True, "size": size}
    return {"text": raw.decode("utf-8", errors="replace"), "truncated": size > 300_000, "size": size}


def git(args: list, cwd: Path, timeout: int = 15) -> tuple[int, str]:
    return run(["git", "-C", str(cwd), *args], timeout=timeout)


def merge_base(wt: Path, target: str) -> Optional[str]:
    for ref in (f"origin/{target}", target, "origin/main", "origin/master", "main", "master"):
        rc, out = git(["merge-base", "HEAD", ref], wt)
        if rc == 0 and out.strip():
            return out.strip().splitlines()[0]
    return None


def api_changes(q: dict, b: dict) -> dict:
    repo, tree = (q.get("repo") or [""])[0], (q.get("tree") or ["main"])[0]
    wt = tree_base(repo, tree)
    target = repo_info(repo).get("target_branch") or "main"
    mb = merge_base(wt, target)
    files: dict[str, dict] = {}
    if mb:
        rc, out = git(["diff", "--numstat", mb], wt)
        for line in out.splitlines():
            parts = line.split("\t")
            if rc == 0 and len(parts) == 3:
                a, d, path = parts
                files[path] = {"path": path, "add": int(a) if a.isdigit() else 0, "del": int(d) if d.isdigit() else 0,
                               "binary": a == "-", "new": False}
    rc, out = git(["status", "--porcelain"], wt)
    for line in out.splitlines():
        if line.startswith("?? "):
            path = line[3:].strip().strip('"')
            if path in files:
                continue
            try:
                p = safe_join(wt, path)
                n = sum(1 for _ in open(p, "rb")) if p.is_file() and p.stat().st_size < 400_000 else 0
            except (ApiError, OSError):
                n = 0
            files[path] = {"path": path, "add": n, "del": 0, "binary": False, "new": True}
    rc, branch = git(["rev-parse", "--abbrev-ref", "HEAD"], wt)
    rc, log = git(["log", "--oneline", "-n", "8"], wt)
    lst = sorted(files.values(), key=lambda f: f["path"])
    return {"base": (mb or "")[:8], "branch": branch.strip() if rc == 0 else "", "files": lst,
            "add": sum(f["add"] for f in lst), "del": sum(f["del"] for f in lst), "commits": log.strip().splitlines()}


def api_diff(q: dict, b: dict) -> dict:
    repo, tree, rel = (q.get("repo") or [""])[0], (q.get("tree") or ["main"])[0], (q.get("path") or [""])[0]
    wt = tree_base(repo, tree)
    p = safe_join(wt, rel)
    mb = merge_base(wt, repo_info(repo).get("target_branch") or "main")
    text = ""
    if mb:
        rc, text = git(["diff", mb, "--", str(p.relative_to(wt.resolve()))], wt, 20)
    if not text.strip() and p.is_file():
        rc, text = git(["diff", "--no-index", "--", "/dev/null", str(p)], wt, 20)
    return {"diff": text[:250_000], "truncated": len(text) > 250_000}


# --------------------------------------------------------------------------- API: GitHub pull requests
def gh_repo(repo: str) -> str:
    o = owner_repo(repo_info(repo).get("github_url", ""))
    if not o:
        raise ApiError(400, "this project is not a GitHub address")
    return o


def api_prs(q: dict, b: dict) -> dict:
    repo, state = (q.get("repo") or [""])[0], (q.get("state") or ["open"])[0]
    if state not in ("open", "merged", "closed"):
        raise ApiError(400, "state must be open, merged or closed")
    rc, out = run(["gh", "pr", "list", "--repo", gh_repo(repo), "--state", state, "--limit", "30", "--json",
                   "number,title,headRefName,additions,deletions,changedFiles,url,author,updatedAt,isDraft,mergeStateStatus"],
                  timeout=30)
    if rc != 0:
        return {"error": clean_term(out)[:300] or "could not read pull requests (are you signed in to GitHub?)", "prs": []}
    try:
        prs = json.loads(out)
    except ValueError:
        return {"error": "GitHub sent an unreadable answer", "prs": []}
    return {"prs": [{"number": p.get("number"), "title": p.get("title", ""), "branch": p.get("headRefName", ""),
                     "add": p.get("additions", 0), "del": p.get("deletions", 0), "files": p.get("changedFiles", 0),
                     "url": p.get("url", ""), "author": (p.get("author") or {}).get("login", ""),
                     "updated": p.get("updatedAt", ""), "draft": bool(p.get("isDraft")),
                     "merge_state": p.get("mergeStateStatus", "")} for p in prs]}


def pr_number(b: dict) -> str:
    n = str(b.get("number", ""))
    if not n.isdigit():
        raise ApiError(400, "bad pull request number")
    return n


def api_pr_diff(q: dict, b: dict) -> dict:
    repo, n = (q.get("repo") or [""])[0], (q.get("number") or [""])[0]
    if not n.isdigit():
        raise ApiError(400, "bad pull request number")
    rc, out = run(["gh", "pr", "diff", n, "--repo", gh_repo(repo)], timeout=40)
    if rc != 0:
        raise ApiError(502, clean_term(out)[:300])
    return {"diff": out[:300_000], "truncated": len(out) > 300_000}


def api_pr_merge(q: dict, b: dict) -> dict:
    method = str(b.get("method", "squash"))
    if method not in ("squash", "merge", "rebase"):
        raise ApiError(400, "method must be squash, merge or rebase")
    rc, out = run(["gh", "pr", "merge", pr_number(b), "--repo", gh_repo(str(b.get("repo", ""))), f"--{method}", "--delete-branch"], timeout=60)
    return {"ok": rc == 0, "message": clean_term(out)[:400]}


def api_pr_close(q: dict, b: dict) -> dict:
    rc, out = run(["gh", "pr", "close", pr_number(b), "--repo", gh_repo(str(b.get("repo", "")))], timeout=40)
    return {"ok": rc == 0, "message": clean_term(out)[:400]}


# --------------------------------------------------------------------------- API: models and logs
def api_models(q: dict, b: dict) -> dict:
    sc = ms.load_state(str(STATE_FILE))
    try:
        report = REPORT_FILE.read_text(encoding="utf-8")[:20000]
    except OSError:
        report = ""
    return {"picks": sc.get("selected") or {}, "role_status": sc.get("role_status") or {},
            "services": ms.keys_table(scout_cfg(), str(KEYS), str(STATE_FILE)), "updated": sc.get("updated", 0), "report": report}


def tail_text(path: Path, lines: int = 200) -> str:
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - 60000))
            raw = f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(clean_term(raw).splitlines()[-lines:])


def api_logs(q: dict, b: dict) -> dict:
    which = (q.get("which") or ["router"])[0]
    repo, agent = (q.get("repo") or [""])[0], (q.get("agent") or [""])[0]
    if which == "router":
        p = HERE / "litellm.log"
    elif which == "dashboard":
        p = HERE / "ui.log"
    elif which == "oat":
        p = OAT_HOME / "daemon.log"
    elif which == "scout":
        p = REPORT_FILE
    elif which == "agent":
        repo_info(repo)
        a = (repo_info(repo).get("agents") or {}).get(check_name(agent, "helper name")) or {}
        p = agent_log_path(repo, agent, a.get("type") == "worker")
    else:
        raise ApiError(400, "unknown log")
    text = tail_text(p)
    return {"text": text or "(nothing here yet)"}


# --------------------------------------------------------------------------- API: skills
PREVIEWS: dict[str, dict] = {}


def list_skills() -> list:
    out = []
    roots = [("yours", SKILLS_DIR)]
    for name in (oat_state().get("repos") or {}):
        if NAME_RE.match(name):
            roots.append((f"project {name}", OAT_HOME / "repos" / name / ".agents" / "skills"))
    for label, root in roots:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            md = d / "SKILL.md"
            if md.is_file():
                fm = front_matter(md)
                out.append({"name": d.name, "title": fm.get("name", d.name), "description": fm.get("description", ""),
                            "source": label, "removable": label == "yours"})
    return out


def api_skills(q: dict, b: dict) -> dict:
    return {"skills": list_skills()}


def skill_url_ok(url: str) -> bool:
    return bool(GH_URL_RE.match(url)) or (ALLOW_LOCAL_URLS and url.startswith("file://"))


def api_skill_preview(q: dict, b: dict) -> dict:
    url = str(b.get("url", "")).strip()
    if not skill_url_ok(url):
        raise ApiError(400, "paste a GitHub address like https://github.com/owner/name")
    for k in [k for k, v in PREVIEWS.items() if time.time() - v["ts"] > 900]:
        shutil.rmtree(PREVIEWS.pop(k)["dir"], ignore_errors=True)
    tmp = tempfile.mkdtemp(prefix="skills-")
    rc, out = run(["git", "clone", "--depth", "1", "--quiet", url, tmp + "/repo"], timeout=90)
    if rc != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ApiError(502, "could not download that repository: " + clean_term(out)[:200])
    root = Path(tmp) / "repo"
    licence = next((p.name for p in root.iterdir() if p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))), "")
    found = []
    for md in sorted(root.rglob("SKILL.md")):
        if ".git" in md.parts or md.is_symlink() or len(md.relative_to(root).parts) > 7:
            continue
        d = md.parent
        fm = front_matter(md)
        scripts = any(f.suffix.lower() in (".sh", ".py", ".js", ".ps1", ".bat", ".cmd", ".rb") for f in d.rglob("*") if f.is_file())
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file() and not f.is_symlink())
        name = fm.get("name") or d.name
        found.append({"folder": str(d.relative_to(root)), "name": name, "description": fm.get("description", ""),
                      "scripts": scripts, "size": size, "valid": bool(SKILL_RE.match(name)) and size < 10_000_000})
        if len(found) >= 200:
            break
    pid = secrets.token_hex(6)
    PREVIEWS[pid] = {"dir": tmp, "root": str(root), "ts": time.time(), "items": {f["name"]: f for f in found}}
    return {"id": pid, "licence": licence, "skills": found}


def api_skill_install(q: dict, b: dict) -> dict:
    pv = PREVIEWS.get(str(b.get("id", "")))
    if not pv:
        raise ApiError(404, "that preview expired; preview the address again")
    names = b.get("names") or []
    if not isinstance(names, list) or not names:
        raise ApiError(400, "choose at least one skill")
    root = Path(pv["root"]).resolve()
    done, skipped = [], []
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    for n in names:
        item = pv["items"].get(str(n))
        if not item or not item["valid"]:
            skipped.append(f"{n}: not a valid skill name or too large")
            continue
        src = safe_join(root, item["folder"])
        dst = SKILLS_DIR / item["name"]
        if dst.exists() and not b.get("overwrite"):
            skipped.append(f"{n}: you already have a skill with this name")
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=False, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        for f in dst.rglob("*"):
            if f.is_symlink():
                f.unlink()
        done.append(item["name"])
    return {"installed": done, "skipped": skipped}


def api_skill_remove(q: dict, b: dict) -> dict:
    name = str(b.get("name", ""))
    if not SKILL_RE.match(name):
        raise ApiError(400, "bad skill name")
    d = safe_join(SKILLS_DIR, name)
    if not d.is_dir() or d == SKILLS_DIR.resolve():
        raise ApiError(404, "no such skill")
    shutil.rmtree(d)
    return {"ok": True}


ROUTES_GET: dict[str, Callable] = {
    "/api/state": api_state, "/api/keys": api_keys, "/api/chat": api_chat, "/api/files": api_files, "/api/file": api_file,
    "/api/changes": api_changes, "/api/diff": api_diff, "/api/prs": api_prs, "/api/pr/diff": api_pr_diff,
    "/api/skills": api_skills, "/api/models": api_models, "/api/logs": api_logs, "/api/job": api_job,
}
ROUTES_POST: dict[str, Callable] = {
    "/api/job": api_job_start, "/api/keys/set": api_key_set, "/api/keys/remove": api_key_remove,
    "/api/github/login": api_github_login, "/api/chat/send": api_chat_send, "/api/task": api_task, "/api/ask": api_ask,
    "/api/pr/merge": api_pr_merge, "/api/pr/close": api_pr_close, "/api/skills/preview": api_skill_preview,
    "/api/skills/install": api_skill_install, "/api/skills/remove": api_skill_remove, "/api/repos/use": api_repo_use,
}


# --------------------------------------------------------------------------- web server
def allowed_host(host: str) -> bool:
    h = host.rsplit(":", 1)[0].strip("[]").lower() if not host.startswith("[") else host.split("]")[0].strip("[").lower()
    extra = [x.strip().lower() for x in os.environ.get("GIFSCYTHE_UI_HOSTS", "").split(",") if x.strip()]
    if h in ("127.0.0.1", "localhost", "::1") or h in extra:
        return True
    if os.environ.get("CODESPACES") == "true" and h.endswith((".app.github.dev", ".githubpreview.dev")):
        return True
    return False


class Handler(BaseHTTPRequestHandler):
    server_version = "AITeamPanel/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, _fmt: str, *args: Any) -> None:
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra: Optional[dict] = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                         "script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, obj: Any) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _token_ok(self) -> bool:
        tok = self.headers.get("X-AIT-Token", "")
        if not tok:
            for part in (self.headers.get("Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == "ait":
                    tok = v
        return bool(tok) and hmac.compare_digest(tok.encode(), token().encode())

    def _handle(self, method: str) -> None:
        try:
            raw_body = b""
            if method == "POST":
                n = int(self.headers.get("Content-Length") or 0)
                if n > 200_000:
                    self.close_connection = True
                    return self._json(413, {"error": "too large"})
                raw_body = self.rfile.read(n) if n > 0 else b""
            u = urllib.parse.urlparse(self.path)
            if u.path == "/ping" and method == "GET":
                return self._send(200, b"ok", "text/plain")
            if not allowed_host(self.headers.get("Host", "")):
                return self._send(403, b"This address is not allowed.", "text/plain")
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/" and method == "GET":
                given = (q.get("t") or [""])[0]
                if given and hmac.compare_digest(given.encode(), token().encode()):
                    return self._send(200, INDEX_HTML.encode(), "text/html; charset=utf-8",
                                      {"Set-Cookie": f"ait={given}; Path=/; HttpOnly; SameSite=Strict"})
                if self._token_ok():
                    return self._send(200, INDEX_HTML.encode(), "text/html; charset=utf-8")
                return self._send(401, LOCKED_HTML.encode(), "text/html; charset=utf-8")
            if not u.path.startswith("/api/"):
                return self._send(404, b"Not found", "text/plain")
            if not self._token_ok():
                return self._json(401, {"error": "locked: open the dashboard with the link from 'harness open'"})
            body: dict = {}
            if method == "POST":
                if self.headers.get("X-Requested-With") != "ait" or "application/json" not in (self.headers.get("Content-Type") or ""):
                    return self._json(403, {"error": "request refused"})
                try:
                    body = json.loads(raw_body or b"{}")
                except ValueError:
                    return self._json(400, {"error": "bad request"})
                if not isinstance(body, dict):
                    return self._json(400, {"error": "bad request"})
            fn = (ROUTES_POST if method == "POST" else ROUTES_GET).get(u.path)
            if not fn:
                return self._json(404, {"error": "unknown call"})
            return self._json(200, fn(q, body))
        except ApiError as e:
            return self._json(e.code, {"error": e.message})
        except (BrokenPipeError, ConnectionResetError):
            return None
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"error in {self.path}: {type(e).__name__}: {e}\n")
            return self._json(500, {"error": "something went wrong inside the dashboard (see: harness logs dashboard)"})

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle("GET")


LOCKED_HTML = """<!doctype html><meta charset="utf-8"><title>AI Team</title>
<body style="font-family:system-ui;max-width:34rem;margin:4rem auto;padding:0 1rem;line-height:1.5">
<h2>This dashboard is locked</h2><p>Open it with the private link. In your terminal, run <b>harness open</b>
(or <b>harness ui</b>) and use the address it prints.</p></body>"""

INDEX_HTML = r"""<!doctype html>
<html lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Team</title>
<style>
:root{--bg:#0e1116;--bg2:#141923;--card:#181e2a;--line:#262f40;--text:#e8ecf3;--mut:#93a0b8;--acc:#7c9cff;--acc2:#5b7cff;--ok:#3ecf8e;--warn:#f5b94a;--bad:#f06a6a;--add:rgba(62,207,142,.16);--del:rgba(240,106,106,.16);--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
[data-theme=light]{--bg:#f4f6fa;--bg2:#ffffff;--card:#ffffff;--line:#dfe4ee;--text:#1b2230;--mut:#5f6c85;--acc:#3d63e8;--acc2:#2f52cf;--add:rgba(30,150,90,.14);--del:rgba(220,70,70,.14)}
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;display:flex;flex-direction:column}
button,input,select,textarea{font:inherit;color:inherit}button{cursor:pointer}
header{display:flex;align-items:center;gap:10px;padding:8px 14px;background:var(--bg2);border-bottom:1px solid var(--line);flex-wrap:wrap}
.logo{font-weight:700;letter-spacing:.2px}.logo b{color:var(--acc)}
.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:99px;border:1px solid var(--line);background:var(--card);font-size:12px;color:var(--mut)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--mut)}.dot.ok{background:var(--ok)}.dot.bad{background:var(--bad)}.dot.warn{background:var(--warn)}
.sp{flex:1}.btn{border:1px solid var(--line);background:var(--card);padding:6px 12px;border-radius:8px}.btn:hover{border-color:var(--acc)}
.btn.pri{background:var(--acc2);border-color:var(--acc2);color:#fff}.btn.bad{border-color:var(--bad);color:var(--bad)}.btn.sm{padding:3px 8px;font-size:12px}
.btn:disabled{opacity:.5;cursor:default}
#app{flex:1;min-height:0;display:grid;grid-template-columns:250px minmax(320px,1fr) 440px}
aside,section{min-height:0;overflow:auto}#side{background:var(--bg2);border-right:1px solid var(--line);padding:12px}#right{background:var(--bg2);border-left:1px solid var(--line);display:flex;flex-direction:column}
#center{display:flex;flex-direction:column;min-width:0}
h4{margin:14px 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut)}
.item{padding:7px 9px;border-radius:8px;cursor:pointer;display:flex;gap:8px;align-items:center;justify-content:space-between}.item:hover{background:var(--card)}.item.on{background:var(--card);outline:1px solid var(--acc)}
.mut{color:var(--mut)}.small{font-size:12px}.mono{font-family:var(--mono)}
.tabs{display:flex;gap:2px;padding:6px 8px 0;border-bottom:1px solid var(--line);overflow-x:auto;flex:none}.tab{padding:7px 12px;border:0;background:none;border-bottom:2px solid transparent;color:var(--mut);white-space:nowrap}.tab.on{color:var(--text);border-color:var(--acc)}
.pane{padding:12px;overflow:auto;flex:1;min-height:0}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:10px}
#msgs{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px}.bub{max-width:88%;padding:9px 12px;border-radius:14px;white-space:pre-wrap;word-break:break-word}
.bub.user{align-self:flex-end;background:var(--acc2);color:#fff;border-bottom-right-radius:4px}.bub.agent{align-self:flex-start;background:var(--card);border:1px solid var(--line);border-bottom-left-radius:4px;font-family:var(--mono);font-size:12.5px}
.bub .who{display:block;font:600 11px system-ui;color:var(--mut);margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px}
.composer{display:flex;gap:8px;padding:10px 12px;border-top:1px solid var(--line);background:var(--bg2);align-items:flex-end;flex:none}
textarea,input[type=text],input[type=password],select{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:8px 10px;width:100%}textarea{resize:vertical;min-height:44px;max-height:200px}
textarea:focus,input:focus,select:focus{outline:2px solid var(--acc);outline-offset:-1px}
.badge{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;border:1px solid var(--line);color:var(--mut)}.badge.ok{color:var(--ok);border-color:var(--ok)}.badge.bad{color:var(--bad);border-color:var(--bad)}.badge.warn{color:var(--warn);border-color:var(--warn)}
.row{display:flex;gap:8px;align-items:center}.row.wrap{flex-wrap:wrap}.grow{flex:1;min-width:0}
.add{color:var(--ok)}.del{color:var(--bad)}.file{display:flex;justify-content:space-between;gap:8px;padding:5px 8px;border-radius:6px;cursor:pointer}.file:hover{background:var(--bg)}
pre{margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.5 var(--mono)}.code{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:10px;overflow:auto;max-height:60vh}
.dl{display:block}.dl.a{background:var(--add)}.dl.d{background:var(--del)}.dl.h{color:var(--acc)}.dl.m{color:var(--mut)}
.check{display:flex;gap:10px;align-items:flex-start;padding:6px 0}.check .tick{width:20px;height:20px;border-radius:50%;border:2px solid var(--line);flex:none;display:grid;place-items:center;font-size:12px}.check.ok .tick{background:var(--ok);border-color:var(--ok);color:#06210f}
#toasts{position:fixed;right:14px;bottom:14px;display:flex;flex-direction:column;gap:8px;z-index:50}.toast{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);padding:9px 12px;border-radius:10px;max-width:340px;box-shadow:0 6px 24px rgba(0,0,0,.25)}.toast.bad{border-left-color:var(--bad)}.toast.ok{border-left-color:var(--ok)}
#modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:grid;place-items:center;z-index:60;padding:16px}#modal[hidden]{display:none}#modal .box{background:var(--bg2);border:1px solid var(--line);border-radius:14px;width:min(760px,100%);max-height:85vh;display:flex;flex-direction:column}
#modal header{border-radius:14px 14px 0 0}#modal .body{padding:12px;overflow:auto}
.menu{display:none}
@media (max-width:1100px){#app{grid-template-columns:1fr;grid-template-rows:auto minmax(420px,1fr) minmax(420px,1fr);overflow:auto}#side{border-right:0;border-bottom:1px solid var(--line)}#right{border-left:0;border-top:1px solid var(--line)}}
</style></head><body>
<header>
  <div class="logo">AI <b>Team</b></div>
  <select id="repoSel" style="width:auto" aria-label="Project"></select>
  <span id="pills" class="row wrap"></span>
  <span class="sp"></span>
  <button class="btn pri" data-act="job:start">Start</button>
  <button class="btn" data-act="job:stop">Stop</button>
  <button class="btn sm" data-act="theme" aria-label="Switch light or dark">Light / Dark</button>
</header>
<div id="app">
  <aside id="side"></aside>
  <section id="center">
    <div class="tabs" id="ctabs"></div>
    <div id="cbody" style="flex:1;min-height:0;display:flex;flex-direction:column"></div>
  </section>
  <aside id="right">
    <div class="tabs" id="rtabs"></div>
    <div class="pane" id="rbody"></div>
  </aside>
</div>
<div id="toasts"></div>
<div id="modal" hidden><div class="box"><header><b id="mTitle"></b><span class="sp"></span><button class="btn sm" data-act="modal-close">Close</button></header><div class="body" id="mBody"></div></div></div>
<script>
(function(){
"use strict";
const $=(s,r)=>(r||document).querySelector(s);
const url=u=>/^https:\/\//.test(String(u||""))?u:"#";
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let TOKEN=new URLSearchParams(location.search).get("t")||sessionStorage.getItem("ait")||"";
if(TOKEN){sessionStorage.setItem("ait",TOKEN);if(location.search)history.replaceState(null,"",location.pathname);}
if(localStorage.getItem("theme"))document.documentElement.dataset.theme=localStorage.getItem("theme");
async function api(path,body){
  const o={headers:{"X-AIT-Token":TOKEN}};
  if(body!==undefined){o.method="POST";o.headers["Content-Type"]="application/json";o.headers["X-Requested-With"]="ait";o.body=JSON.stringify(body);}
  let r;try{r=await fetch(path,o);}catch(e){throw new Error("The dashboard stopped answering. Run: harness open");}
  let j={};try{j=await r.json();}catch(e){}
  if(!r.ok)throw new Error(j.error||("error "+r.status));
  return j;
}
function toast(msg,kind){const d=document.createElement("div");d.className="toast "+(kind||"");d.textContent=msg;$("#toasts").appendChild(d);setTimeout(()=>d.remove(),kind==="bad"?9000:4500);}
const S={st:null,repo:"",ctab:"chat",rtab:"files",files:{tree:"main",path:"",entries:null,file:null},changes:null,chatKey:"",seenPr:{},logWhich:"router",prState:"open",prs:null,skillsPv:null};
const CT=[["chat","Chat"],["tasks","Tasks"],["ask","Ask the models"]];
const RT=[["files","Files"],["changes","Changes"],["prs","Pull requests"],["models","Models"],["connections","Connections"],["skills","Skills"],["logs","Logs"]];
function badge(s){const k={ok:"ok",skip:"",refused:"bad",offline:"warn",limit:"warn",blocked:"warn",warn:"warn",unknown:""}[s]||"";return `<span class="badge ${k}">${esc(s)}</span>`;}
function ago(ts){if(!ts)return"never";const s=Math.max(0,Date.now()/1000-ts);if(s<90)return"just now";if(s<5400)return Math.round(s/60)+" min ago";if(s<172800)return Math.round(s/3600)+" h ago";return Math.round(s/86400)+" days ago";}
function dot(c){return `<span class="dot ${c}"></span>`;}

/* ---------------- header / side ---------------- */
function renderHeader(){
  const st=S.st;if(!st)return;
  const sel=$("#repoSel");const cur=S.repo;
  sel.innerHTML=st.repos.length?st.repos.map(r=>`<option value="${esc(r.name)}"${r.name===cur?" selected":""}>${esc(r.name)}</option>`).join(""):`<option value="">No project yet</option>`;
  const picks=Object.values(st.picks||{}).some(v=>v&&v.length);
  const bad=st.services.filter(s=>s.status==="refused").length;
  $("#pills").innerHTML=
    `<span class="pill">${dot(st.router.up?"ok":"bad")}Router</span>`+
    `<span class="pill">${dot(st.daemon?"ok":"bad")}Agent team</span>`+
    `<span class="pill">${dot(st.github.ok?"ok":"warn")}GitHub${st.github.user?" · "+esc(st.github.user):""}</span>`+
    `<span class="pill">${dot(picks?(bad?"warn":"ok"):"bad")}Models</span>`;
}
function renderSide(){
  const st=S.st;if(!st)return;
  const projects=st.repos.map(r=>`<div class="item ${r.name===S.repo?"on":""}" data-act="repo:${esc(r.name)}"><span>${esc(r.name)}</span><span class="mut small">${esc(r.owner_repo)}</span></div>`).join("")||`<div class="mut small">Nothing yet.</div>`;
  const helpers=st.agents.filter(a=>a.type==="worker"||a.type==="review"||a.type==="verification").slice(0,8).map(a=>
    `<div class="item" data-act="helper:${esc(a.name)}"><span class="grow" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(a.task)}">${esc(a.name)}</span>${a.pr?`<span class="badge ok">PR #${esc(a.pr)}</span>`:`<span class="badge">${esc(a.type)}</span>`}</div>`).join("")||`<div class="mut small">No helpers working right now.</div>`;
  const hist=st.history.slice(0,5).map(h=>`<div class="small" style="padding:4px 9px"><span class="mut">${esc(h.status||"")}</span> ${esc((h.task||"").slice(0,60))}${h.pr_url?` <a href="${esc(url(h.pr_url))}" target="_blank" rel="noopener noreferrer">PR</a>`:""}</div>`).join("");
  $("#side").innerHTML=`<h4>Projects</h4>${projects}<div style="padding:6px 0"><button class="btn sm" data-act="add-repo">+ Add project</button></div>
  <h4>Helpers</h4>${helpers}${hist?`<h4>Recent work</h4>${hist}`:""}
  <h4>Quick actions</h4><div class="row wrap"><button class="btn sm" data-act="job:scout">Refresh models</button><button class="btn sm" data-act="job:check">Check keys</button><button class="btn sm" data-act="job:doctor">Doctor</button></div>
  <p class="mut small" style="margin-top:14px">Keys: ${st.services.map(s=>`${esc(s.service)} ${badge(s.status)}`).join(" ")}</p>`;
}

/* ---------------- centre ---------------- */
function renderTabs(){
  $("#ctabs").innerHTML=CT.map(([k,l])=>`<button class="tab ${S.ctab===k?"on":""}" data-act="ctab:${k}">${l}</button>`).join("");
  $("#rtabs").innerHTML=RT.map(([k,l])=>`<button class="tab ${S.rtab===k?"on":""}" data-act="rtab:${k}">${l}</button>`).join("");
}
function setupCard(){
  const st=S.st;if(!st)return"";const todo=st.setup.filter(s=>!s.ok);if(!todo.length)return"";
  return `<div class="card"><b>Let's get you set up</b><div class="mut small" style="margin-bottom:6px">Do these from the top. Each one has a button or a hint.</div>`+
    st.setup.map(s=>`<div class="check ${s.ok?"ok":""}"><span class="tick">${s.ok?"✓":""}</span><div class="grow"><div>${esc(s.label)}</div>${s.ok?"":`<div class="mut small">${esc(s.hint)}</div>`}</div>${s.ok?"":`<button class="btn sm" data-act="${esc(s.action)}">Do it</button>`}</div>`).join("")+`</div>`;
}
function renderCenter(){
  const b=$("#cbody");
  if(S.ctab==="chat"){
    if(!$("#msgs")){b.innerHTML=`<div id="msgs"></div><div class="composer"><textarea id="chatIn" rows="2" placeholder="Tell the helper what you want, like in a chat. Enter sends, Shift+Enter adds a line."></textarea><button class="btn pri" data-act="send-chat">Send</button></div>`;S.chatKey="";}
    loadChat();
  }else if(S.ctab==="tasks"){
    b.innerHTML=`<div class="pane">${setupCard()}<div class="card"><b>Give a task to a new helper</b><div class="mut small" style="margin:4px 0 8px">The helper works on its own copy of your code and opens a pull request for you to review.</div>
      <div class="row" style="margin-bottom:8px"><span class="mut small">Helper type</span><select id="taskRole" style="width:auto"><option value="implementer">implementer - writes code</option><option value="architect">architect - plans and researches</option><option value="reviewer">reviewer - checks work</option></select></div>
      <textarea id="taskIn" rows="5" placeholder="Describe the task. Example: Add a comment line at the top of README.md saying AI team test, then open a pull request."></textarea>
      <div class="row" style="margin-top:8px"><button class="btn pri" data-act="send-task">Start the task</button><span id="taskMsg" class="mut small"></span></div></div>
      <div class="card"><b>Handy tasks</b><div class="row wrap" style="margin-top:8px">
      <button class="btn sm" data-act="chat-prompt:Set up the project workflow files (handoff, worklist and improvement log) from the team-workflow skill and open a pull request.">Set up project workflow files</button>
      <button class="btn sm" data-act="chat-prompt:Read the handoff, worklist and improvement log, then tell me the top three things to do next and why.">What should we do next?</button>
      <button class="btn sm" data-act="chat-prompt:Using the self-extend skill, check which skills or tools you are missing for the current worklist, and propose them in a pull request.">Find missing skills</button></div></div></div>`;
  }else{
    b.innerHTML=`<div id="askMsgs" style="flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px"><div class="mut small">Ask the free models directly, like a normal chat. They cannot see your project files here. Use Chat for project work.</div></div>
      <div class="composer"><select id="askRole" style="width:auto"><option>architect</option><option selected>implementer</option><option>reviewer</option></select><textarea id="askIn" rows="2" placeholder="Ask anything"></textarea><button class="btn pri" data-act="ask-models">Ask</button></div>`;
  }
}
async function loadChat(){
  if(S.ctab!=="chat")return;
  const m=$("#msgs");if(!m)return;
  if(!S.repo){m.innerHTML=`<div class="mut" style="padding:8px">${setupCard()||"Add a project to start chatting."}</div>`;return;}
  try{
    const d=await api("/api/chat?repo="+encodeURIComponent(S.repo));
    const key=JSON.stringify(d.messages)+d.log_exists;if(key===S.chatKey)return;S.chatKey=key;
    const atBottom=m.scrollHeight-m.scrollTop-m.clientHeight<80;
    let h=setupCard();
    if(!d.messages.length)h+=`<div class="mut" style="padding:8px">${d.log_exists?"The helper has not said anything yet.":"No messages yet. Type below to talk to the workspace helper. It can look around the project and start other helpers for you."}</div>`;
    h+=d.messages.map(x=>`<div class="bub ${x.role}"><span class="who">${x.role==="user"?"You":"Helper"}</span>${esc(x.text)}</div>`).join("");
    m.innerHTML=h;if(atBottom||!S.chatKeyOnce){m.scrollTop=m.scrollHeight;S.chatKeyOnce=true;}
  }catch(e){m.innerHTML=`<div class="mut" style="padding:8px">${esc(e.message)}</div>`;}
}
async function sendChat(){
  const t=$("#chatIn");const text=t.value.trim();if(!text||!S.repo)return;
  try{await api("/api/chat/send",{repo:S.repo,text});t.value="";S.chatKey="";loadChat();}catch(e){toast(e.message,"bad");}
}

/* ---------------- right ---------------- */
function diffHtml(text){return text.split("\n").map(l=>{const c=l.startsWith("+++")||l.startsWith("---")||l.startsWith("diff ")||l.startsWith("index ")?"m":l.startsWith("@@")?"h":l.startsWith("+")?"a":l.startsWith("-")?"d":"";return `<span class="dl ${c}">${esc(l)||" "}</span>`;}).join("");}
function treeSelect(){const ws=(S.st.agents||[]).filter(a=>a.has_tree);if(S.files.tree!=="main"&&!ws.some(a=>a.name===S.files.tree)){S.files.tree="main";S.files.path="";S.files.file=null;}return `<select id="treeSel"><option value="main">Main copy of the project</option>${ws.map(a=>`<option value="${esc(a.name)}"${S.files.tree===a.name?" selected":""}>Helper: ${esc(a.name)}</option>`).join("")}</select>`;}
async function renderRight(){
  const b=$("#rbody");if(!b)return;const t=S.rtab;const repo=S.repo;
  const need=()=>{b.innerHTML=`<div class="mut">${repo?"":"Add a project first (left side, + Add project)."}</div>`;};
  try{
    if(t==="files"){
      if(!repo)return need();
      const f=S.files;
      if(f.file){b.innerHTML=`<div class="row"><button class="btn sm" data-act="file-back">Back</button><span class="mono small">${esc(f.file.path)}</span></div><div class="code" style="margin-top:8px"><pre>${f.file.binary?"(binary file, "+f.file.size+" bytes)":esc(f.file.text)+(f.file.truncated?"\n\n... (cut: the file is large)":"")}</pre></div>`;return;}
      const d=await api(`/api/files?repo=${encodeURIComponent(repo)}&tree=${encodeURIComponent(f.tree)}&path=${encodeURIComponent(f.path)}`);
      f.entries=d.entries;
      const up=f.path?`<div class="file" data-act="dir:${esc(f.path.split("/").slice(0,-1).join("/"))}"><span>..</span></div>`:"";
      b.innerHTML=`${treeSelect()}<div class="mono small mut" style="margin:8px 0">/${esc(f.path)}</div>${up}`+d.entries.map(e=>`<div class="file" data-act="${e.type==="dir"?"dir":"file"}:${esc((f.path?f.path+"/":"")+e.name)}"><span>${e.type==="dir"?"📁":"📄"} ${esc(e.name)}</span><span class="mut small">${e.type==="dir"?"":e.size+" B"}</span></div>`).join("");
    }else if(t==="changes"){
      if(!repo)return need();
      const d=await api(`/api/changes?repo=${encodeURIComponent(repo)}&tree=${encodeURIComponent(S.files.tree)}`);S.changes=d;
      b.innerHTML=`${treeSelect()}<div class="card" style="margin-top:8px"><div class="row"><b>Changes</b><span class="add">+${d.add}</span><span class="del">−${d.del}</span><span class="mut small">${d.files.length} file(s) · branch ${esc(d.branch)} · compared with ${esc(d.base||"?")}</span></div></div>`+
        (d.files.length?d.files.map(f=>`<div class="file" data-act="change-file:${esc(f.path)}"><span>${esc(f.path)}${f.new?` <span class="badge">new</span>`:""}</span><span><span class="add">+${f.add}</span> <span class="del">−${f.del}</span></span></div>`).join(""):`<div class="mut">No changes in this copy.${S.files.tree==="main"?" Pick a helper above to see what it changed.":""}</div>`)+
        (d.commits.length?`<h4>Recent commits</h4><pre class="mut">${esc(d.commits.join("\n"))}</pre>`:"");
    }else if(t==="prs"){
      if(!repo)return need();
      const d=await api(`/api/prs?repo=${encodeURIComponent(repo)}&state=${S.prState}`);S.prs=d;
      b.innerHTML=`<div class="row" style="margin-bottom:8px">${["open","merged","closed"].map(s=>`<button class="btn sm ${S.prState===s?"pri":""}" data-act="prstate:${s}">${s}</button>`).join("")}</div>`+
        (d.error?`<div class="card"><span class="del">${esc(d.error)}</span></div>`:"")+
        (d.prs.length?d.prs.map(p=>`<div class="card"><div class="row"><b class="grow">#${p.number} ${esc(p.title)}</b>${p.draft?`<span class="badge">draft</span>`:""}</div>
          <div class="mut small">${esc(p.branch)} · ${esc(p.author)} · ${p.files} file(s) · <span class="add">+${p.add}</span> <span class="del">−${p.del}</span></div>
          <div class="row wrap" style="margin-top:8px"><button class="btn sm" data-act="pr-diff:${p.number}">View changes</button><a class="btn sm" href="${esc(url(p.url))}" target="_blank" rel="noopener noreferrer">Open on GitHub</a>
          ${S.prState==="open"?`<button class="btn sm pri" data-act="pr-merge:${p.number}">Merge</button><button class="btn sm bad" data-act="pr-close:${p.number}">Close</button>`:""}</div></div>`).join(""):(d.error?"":`<div class="mut">No ${S.prState} pull requests.</div>`));
    }else if(t==="models"){
      const d=await api("/api/models");
      const roleName={architect:"architect · plans",implementer:"implementer · writes code",reviewer:"reviewer · checks work"};
      b.innerHTML=`<div class="row" style="margin-bottom:8px"><button class="btn pri sm" data-act="job:scout">Refresh models</button><button class="btn sm" data-act="job:check">Check keys</button><span class="mut small">Last refresh: ${ago(d.updated)}</span></div>`+
        Object.keys(roleName).map(r=>{const rs=d.role_status[r]||"";const list=(d.picks[r]||[]);return `<div class="card"><b>${roleName[r]}</b> ${rs==="borrowed"?`<span class="badge warn">using other roles' models</span>`:""}${rs==="unavailable"?`<span class="badge bad">no model right now</span>`:""}<ol style="margin:6px 0 0 18px;padding:0">${list.map(m=>`<li class="mono small">${esc(m)}</li>`).join("")||"<li class='mut'>none yet</li>"}</ol></div>`;}).join("")+
        `<h4>Services</h4>`+d.services.map(s=>`<div class="row" style="padding:3px 0"><span style="width:90px">${esc(s.service)}</span>${badge(s.status)}<span class="mut small grow">${esc(s.msg)}</span></div>`).join("")+
        `<h4>Last report</h4><div class="code"><pre>${esc(d.report||"No report yet. Press Refresh models.")}</pre></div>`;
    }else if(t==="connections"){
      const d=await api("/api/keys");const gh=S.st.github;
      b.innerHTML=`<div class="card"><div class="row"><b class="grow">GitHub</b>${gh.ok?`<span class="badge ok">signed in${gh.user?" as "+esc(gh.user):""}</span>`:`<span class="badge warn">not signed in</span>`}</div>
        <div class="mut small" style="margin:6px 0">Paste a fine-grained token that only reaches your project. It is handed to GitHub's own tool and not stored here.</div>
        <div class="row"><input type="password" id="ghTok" placeholder="github_pat_..." autocomplete="off"><button class="btn sm pri" data-act="gh-login">Sign in</button></div><div id="ghMsg" class="small mut"></div></div>`+
        `<h4>Free AI services</h4>`+d.services.map(s=>`<div class="card"><div class="row"><b class="grow">${esc(s.service)}</b>${badge(s.status)}<span class="mono small mut">${esc(s.masked)}</span></div><div class="mut small">${esc(s.msg)}</div>
          <div class="row" style="margin-top:8px"><input type="password" id="k-${esc(s.service)}" placeholder="${s.saved?"Paste a new key to replace":"Paste a key"}" autocomplete="off"><button class="btn sm pri" data-act="key-save:${esc(s.service)}">Test &amp; save</button>${s.saved?`<button class="btn sm bad" data-act="key-remove:${esc(s.service)}">Remove</button>`:""}</div><div id="km-${esc(s.service)}" class="small"></div></div>`).join("")+
        `<h4>Extras</h4>`+d.extras.map(x=>`<div class="card"><div class="row"><b class="grow">${esc(x.label)}</b>${x.saved?`<span class="badge ok">saved</span>`:`<span class="badge">not set</span>`}</div><div class="mut small">Lets helpers search the web. A free Tavily key works. Restart the agent team after changing it.</div>
          <div class="row" style="margin-top:8px"><input type="password" id="k-${esc(x.name)}" placeholder="tvly-..." autocomplete="off"><button class="btn sm pri" data-act="key-save:${esc(x.name)}">Save</button>${x.saved?`<button class="btn sm bad" data-act="key-remove:${esc(x.name)}">Remove</button>`:""}</div><div id="km-${esc(x.name)}" class="small"></div></div>`).join("")+
        `<div class="card mut small"><b>Plug-ins (MCP)</b><br>This agent team does not load MCP servers directly. Helpers get new abilities through skills and small scripts (see the Skills tab). If you need a specific MCP service, tell me which one.</div>`;
    }else if(t==="skills"){
      const d=await api("/api/skills");
      b.innerHTML=`<div class="card"><b>Add skills from a GitHub project</b><div class="mut small" style="margin:4px 0 8px">Any project that contains SKILL.md folders (a skills collection, a design kit, a SkillOpt output...). You see what is inside before anything is installed. Skills can contain scripts, so only add projects you trust.</div>
        <div class="row"><input type="text" id="skUrl" placeholder="https://github.com/owner/name"><button class="btn sm pri" data-act="skill-preview">Look inside</button></div><div id="skPv"></div></div>`+
        `<h4>Installed</h4>`+(d.skills.length?d.skills.map(s=>`<div class="card"><div class="row"><b class="grow">${esc(s.title)}</b><span class="badge">${esc(s.source)}</span>${s.removable?`<button class="btn sm bad" data-act="skill-remove:${esc(s.name)}">Remove</button>`:""}</div><div class="mut small">${esc(s.description)}</div></div>`).join(""):`<div class="mut">No skills yet. Run: harness install-skills</div>`);
      if(S.skillsPv)renderPv();
    }else if(t==="logs"){
      const w=S.logWhich;const d=await api(`/api/logs?which=${w}`);
      b.innerHTML=`<div class="row wrap" style="margin-bottom:8px">${[["router","Router"],["oat","Agent team"],["dashboard","Dashboard"],["scout","Model report"]].map(([k,l])=>`<button class="btn sm ${w===k?"pri":""}" data-act="logs:${k}">${l}</button>`).join("")}</div><div class="code"><pre>${esc(d.text)}</pre></div>`;
    }
  }catch(e){b.innerHTML=`<div class="card"><span class="del">${esc(e.message)}</span></div>`;}
}
function renderPv(){
  const pv=S.skillsPv,el=$("#skPv");if(!pv||!el)return;
  el.innerHTML=`<div class="small mut" style="margin:8px 0">${pv.licence?`Licence file: ${esc(pv.licence)}`:`<span class="del">No licence file found. Check you may use it.</span>`} · ${pv.skills.length} skill(s) found</div>`+
    pv.skills.map(s=>`<label class="row" style="padding:4px 0"><input type="checkbox" data-sk="${esc(s.name)}" ${s.valid?"":"disabled"}><span class="grow"><b>${esc(s.name)}</b> <span class="mut small">${esc(s.description).slice(0,120)}</span></span>${s.scripts?`<span class="badge warn">has scripts</span>`:""}${s.valid?"":`<span class="badge bad">not installable</span>`}</label>`).join("")+
    (pv.skills.length?`<div class="row" style="margin-top:8px"><button class="btn sm pri" data-act="skill-install">Install selected</button></div>`:"");
}

/* ---------------- actions ---------------- */
function openModal(title){$("#mTitle").textContent=title;$("#mBody").innerHTML="";$("#modal").hidden=false;}
async function watchJob(id,title){
  openModal(title);let done=false;
  while(!done){
    try{const j=await api("/api/job?id="+id);
      $("#mBody").innerHTML=`<div class="row" style="margin-bottom:8px">${j.status==="running"?`<span class="badge warn">working...</span>`:j.status==="done"?`<span class="badge ok">done</span>`:`<span class="badge bad">failed</span>`}</div><div class="code"><pre>${esc(j.lines.join("\n")||"(starting)")}</pre></div>`;
      const c=$("#mBody .code");if(c)c.scrollTop=c.scrollHeight;
      done=j.status!=="running";
    }catch(e){$("#mBody").textContent=e.message;done=true;}
    if(!done)await new Promise(r=>setTimeout(r,1200));
  }
  refreshState();if(S.rtab==="models"||S.rtab==="connections")renderRight();
}
async function startJob(action,extra){try{const j=await api("/api/job",Object.assign({action},extra||{}));watchJob(j.id,({start:"Starting",stop:"Stopping","add-repo":"Adding the project",scout:"Refreshing models",check:"Checking keys",doctor:"Checking every part"})[action]||action);}catch(e){toast(e.message,"bad");}}
async function act(a,el){
  const [k,...r]=a.split(":");const v=r.join(":");
  if(k==="ctab"){S.ctab=v;renderTabs();$("#cbody").innerHTML="";renderCenter();}
  else if(k==="rtab"){S.rtab=v;renderTabs();renderRight();}
  else if(k==="repo"){S.repo=v;S.files={tree:"main",path:"",entries:null,file:null};S.chatKey="";$("#repoSel").value=v;await refreshState();renderCenter();renderRight();try{await api("/api/repos/use",{name:v});}catch(e){}}
  else if(k==="helper"){S.files.tree=v;S.files.path="";S.files.file=null;S.rtab="changes";renderTabs();renderRight();}
  else if(k==="job")startJob(v);
  else if(k==="tab"){S.rtab=v;renderTabs();renderRight();}
  else if(k==="add-repo"){const url=prompt("Paste the GitHub address of the project, for example https://github.com/owner/name");if(url)startJob("add-repo",{url:url.trim()});}
  else if(k==="theme"){const t=document.documentElement.dataset.theme==="dark"?"light":"dark";document.documentElement.dataset.theme=t;localStorage.setItem("theme",t);}
  else if(k==="modal-close")$("#modal").hidden=true;
  else if(k==="send-chat")sendChat();
  else if(k==="chat-prompt"){S.ctab="chat";renderTabs();$("#cbody").innerHTML="";renderCenter();setTimeout(()=>{const t=$("#chatIn");if(t){t.value=v;t.focus();}},50);}
  else if(k==="send-task"){const text=$("#taskIn").value.trim();if(!text)return;try{const d=await api("/api/task",{repo:S.repo,text,role:$("#taskRole").value});$("#taskIn").value="";$("#taskMsg").textContent="Started. Watch the helper on the left.";toast("Task started","ok");refreshState();}catch(e){toast(e.message,"bad");}}
  else if(k==="ask-models"){const text=$("#askIn").value.trim();if(!text)return;const box=$("#askMsgs");box.insertAdjacentHTML("beforeend",`<div class="bub user"><span class="who">You</span>${esc(text)}</div><div class="bub agent" id="askWait"><span class="who">Thinking</span>...</div>`);$("#askIn").value="";box.scrollTop=box.scrollHeight;
    try{const d=await api("/api/ask",{role:$("#askRole").value,text});$("#askWait").outerHTML=`<div class="bub agent"><span class="who">${esc($("#askRole").value)}${d.answered_by?" · "+esc(d.answered_by):""}</span>${esc(d.text)}</div>`;}catch(e){$("#askWait").outerHTML=`<div class="bub agent"><span class="who">Problem</span>${esc(e.message)}</div>`;}box.scrollTop=box.scrollHeight;}
  else if(k==="dir"){S.files.path=v;S.files.file=null;renderRight();}
  else if(k==="file"){try{const d=await api(`/api/file?repo=${encodeURIComponent(S.repo)}&tree=${encodeURIComponent(S.files.tree)}&path=${encodeURIComponent(v)}`);d.path=v;S.files.file=d;renderRight();}catch(e){toast(e.message,"bad");}}
  else if(k==="file-back"){S.files.file=null;renderRight();}
  else if(k==="change-file"){try{const d=await api(`/api/diff?repo=${encodeURIComponent(S.repo)}&tree=${encodeURIComponent(S.files.tree)}&path=${encodeURIComponent(v)}`);openModal(v);$("#mBody").innerHTML=`<div class="code"><pre>${diffHtml(d.diff||"(no text changes)")}</pre></div>`;}catch(e){toast(e.message,"bad");}}
  else if(k==="prstate"){S.prState=v;renderRight();}
  else if(k==="pr-diff"){try{const d=await api(`/api/pr/diff?repo=${encodeURIComponent(S.repo)}&number=${v}`);openModal("Pull request #"+v);$("#mBody").innerHTML=`<div class="code"><pre>${diffHtml(d.diff)}</pre></div>`;}catch(e){toast(e.message,"bad");}}
  else if(k==="pr-merge"){if(confirm("Merge pull request #"+v+" into your main branch? Only do this after you have read the changes.")){try{const d=await api("/api/pr/merge",{repo:S.repo,number:v});toast(d.ok?"Merged":d.message,d.ok?"ok":"bad");renderRight();}catch(e){toast(e.message,"bad");}}}
  else if(k==="pr-close"){if(confirm("Close pull request #"+v+" without merging?")){try{const d=await api("/api/pr/close",{repo:S.repo,number:v});toast(d.ok?"Closed":d.message,d.ok?"ok":"bad");renderRight();}catch(e){toast(e.message,"bad");}}}
  else if(k==="logs"){S.logWhich=v;renderRight();}
  else if(k==="gh-login"){const t=$("#ghTok").value.trim();if(!t)return;try{const d=await api("/api/github/login",{token:t});$("#ghTok").value="";$("#ghMsg").textContent=d.message;await refreshState();renderRight();}catch(e){$("#ghMsg").textContent=e.message;}}
  else if(k==="key-save"){const inp=$("#k-"+v);const key=inp.value.trim();if(!key)return;$("#km-"+v).textContent="Testing...";try{const d=await api("/api/keys/set",{service:v,key});inp.value="";$("#km-"+v).innerHTML=`<span class="${d.saved?"add":"del"}">${d.saved?"Saved. ":"Not saved. "}${esc(d.message)}</span>`;await refreshState();if(d.saved)setTimeout(renderRight,1500);}catch(e){$("#km-"+v).textContent=e.message;}}
  else if(k==="key-remove"){if(confirm("Remove the saved "+v+" key? The old keys file is kept as a backup.")){try{await api("/api/keys/remove",{service:v});await refreshState();renderRight();}catch(e){toast(e.message,"bad");}}}
  else if(k==="skill-preview"){const url=$("#skUrl").value.trim();if(!url)return;$("#skPv").textContent="Downloading to look inside...";try{S.skillsPv=await api("/api/skills/preview",{url});renderPv();}catch(e){$("#skPv").innerHTML=`<span class="del">${esc(e.message)}</span>`;}}
  else if(k==="skill-install"){const names=[...document.querySelectorAll("[data-sk]:checked")].map(x=>x.dataset.sk);if(!names.length)return toast("Tick at least one skill","bad");try{const d=await api("/api/skills/install",{id:S.skillsPv.id,names});toast("Installed: "+(d.installed.join(", ")||"nothing")+(d.skipped.length?" | "+d.skipped.join("; "):""),d.installed.length?"ok":"bad");S.skillsPv=null;renderRight();}catch(e){toast(e.message,"bad");}}
  else if(k==="skill-remove"){if(confirm("Remove the skill "+v+"?")){try{await api("/api/skills/remove",{name:v});renderRight();}catch(e){toast(e.message,"bad");}}}
}
document.addEventListener("click",ev=>{const el=ev.target.closest("[data-act]");if(el){ev.preventDefault();act(el.dataset.act,el);}});
document.addEventListener("keydown",ev=>{if(ev.target.id==="chatIn"&&ev.key==="Enter"&&!ev.shiftKey){ev.preventDefault();sendChat();}});
document.addEventListener("change",ev=>{if(ev.target.id==="treeSel"){S.files.tree=ev.target.value;S.files.path="";S.files.file=null;renderRight();}if(ev.target.id==="repoSel"&&ev.target.value)act("repo:"+ev.target.value);});

/* ---------------- polling ---------------- */
async function refreshState(){
  try{
    const st=await api("/api/state"+(S.repo?"?repo="+encodeURIComponent(S.repo):""));
    const first=!S.st;S.st=st;if(!S.repo||!st.repos.some(r=>r.name===S.repo))S.repo=st.current||"";
    for(const a of st.agents){const prev=S.seenPr[a.name];if(prev===0&&a.pr)toast("Helper "+a.name+" opened pull request #"+a.pr,"ok");S.seenPr[a.name]=a.pr||0;}
    renderHeader();renderSide();
    if(first){renderTabs();renderCenter();renderRight();}

  }catch(e){const p=$("#pills");if(p)p.innerHTML=`<span class="pill">${dot("bad")}${esc(e.message)}</span>`;}
}
refreshState();
setInterval(refreshState,3000);
setInterval(()=>{if(S.ctab==="chat")loadChat();},2000);
setInterval(()=>{const a=document.activeElement;if(["changes","prs"].includes(S.rtab)&&!(a&&a.closest&&a.closest("#rbody")))renderRight();},12000);
})();
</script></body></html>"""


def main() -> int:
    token()
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        sys.stderr.write(f"Could not start the dashboard on port {PORT}: {e}\n(Is it already running? Try: harness ui-stop)\n")
        return 1
    srv.daemon_threads = True
    sys.stdout.write(f"AI Team dashboard on http://127.0.0.1:{PORT}\n")
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
