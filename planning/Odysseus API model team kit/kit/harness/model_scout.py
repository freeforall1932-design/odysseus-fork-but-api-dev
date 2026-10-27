#!/usr/bin/env python3
"""model_scout.py - keeps your AI router pointed at the best models that are free TODAY.

Free AI models change every few months. Instead of typing model names by hand, run this
script. It asks each AI service which models it offers, keeps the free ones that can use
tools, quick-tests the best-looking ones (one model at a time per service, with a pause
between models), ranks them for three roles (architect, implementer, reviewer) and writes
the list that the router (LiteLLM) reads.

Commands (run it with the router's Python so YAML support is available):
  --selftest        test this script itself. Needs no keys and no internet.
  --check           test your keys and show the free models it found. Uses at most
                    one tiny request per service.
  --probe           find, quick-test and rank models, then write the router list.
  --use-saved       rebuild the router list from saved test results (no new tests).
  --dry-run         show what would change. Writes nothing, spends nothing.
  --print-defaults  print every setting you can change (save it as scout.yaml, edit it,
                    then add --config scout.yaml)
  --keys-table      show which keys are saved and what the last test said
  --set-key NAME    test a new key (given in the SCOUT_NEW_KEY variable) and save it if it works
  --remove-key NAME remove a saved key
  --test-key NAME   test a key without saving it

Service status words: ok, skip (no key), refused (key rejected), offline (cannot reach it),
limit (free allowance used up for now), blocked (an account setting blocks free models).

Exit code: 0 = nothing changed, 10 = the list changed (this is NOT an error), 1 = problem.
Keys are read from environment variables or the keys file. They are never printed.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io as _io
import json
import math
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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional

try:
    import yaml  # type: ignore
except ImportError:  # JSON is valid YAML, so the output still loads in LiteLLM
    yaml = None

DAY = 86400.0
UA = "model-scout/1.2 (local config generator)"
HERE = os.path.dirname(os.path.abspath(__file__))
KEYS_DEFAULT = "~/.config/gifscythe-harness/keys.env"
LABELS = {"ok": "[OK]", "skip": "[skip]", "refused": "[refused]", "offline": "[offline]",
          "limit": "[limit]", "blocked": "[blocked]", "warn": "[warn]"}

DEFAULTS: dict[str, Any] = {
    # To add another OpenAI-style service, add an entry here (in scout.yaml) with
    # "catalog": "openai", "assume_free": true, "litellm_prefix": "openai" and "litellm_api_base".
    "providers": {
        "openrouter": {"key_env": "OPENROUTER_API_KEY", "base_url": "https://openrouter.ai/api/v1",
                       "litellm_prefix": "openrouter", "catalog": "openrouter", "rpm": 18},
        "nvidia": {"key_env": "NVIDIA_API_KEY", "base_url": "https://integrate.api.nvidia.com/v1",
                   "litellm_prefix": "nvidia_nim", "catalog": "openai", "assume_free": True, "rpm": 30},
        "mistral": {"key_env": "MISTRAL_API_KEY", "base_url": "https://api.mistral.ai/v1",
                    "litellm_prefix": "mistral", "catalog": "openai", "assume_free": True, "rpm": 30},
        "google": {"key_env": "GEMINI_API_KEY", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                   "litellm_prefix": "gemini", "catalog": "openai", "assume_free": True, "rpm": 10,
                   "id_strip": "models/", "include": "flash"},
    },
    # Never use things that are not chat/coding models, or OpenRouter's own "pick for me" routers.
    "exclude": (r"embed|rerank|tts|whisper|asr|parakeet|guard|safety|safeguard|moderation|reward|diffusion|flux|"
                r"sdxl|imagen|veo|lyria|video|speech|audio|transcribe|ocr|image|live|robotics|computer-use|"
                r"learnlm|translate|detect|^openrouter/(auto|free)$"),
    "block": [],        # "service:model" or a regex that is never used
    "pins": {},         # role -> ["service:model", ...] always included first (your explicit choice)
    "min_days_before_expiry": 3,
    "stealth_penalty": 0.15,        # OpenRouter stealth models log prompts; allowed but ranked lower
    "stickiness": 0.04,             # bonus for the current pick so ranks do not flap
    "independent_reviewer": True,   # reviewer #1 should be a different model from implementer #1
    "max_per_provider": 2,          # per role, so one service being down cannot empty a role
    "roles": {
        "architect":   {"top_n": 3, "min_context": 128000, "weights": {"format": 0.40, "trace": 0.35, "review": 0.25}},
        "implementer": {"top_n": 3, "min_context": 64000,  "weights": {"trace": 0.50, "format": 0.30, "review": 0.20}},
        "reviewer":    {"top_n": 3, "min_context": 128000, "weights": {"review": 0.50, "trace": 0.35, "format": 0.15}},
    },
    # Weak hints only (tie-breakers). The quick tests and release dates decide the rest. Edit freely.
    "priors": [
        {"pattern": r"glm-(5|4\.[5-9])", "bonus": 0.15},
        {"pattern": r"qwen3(\.\d)?-coder|qwen3\.[5-9]", "bonus": 0.15},
        {"pattern": r"devstral", "bonus": 0.15},
        {"pattern": r"nemotron-3-(ultra|super)", "bonus": 0.15},
        {"pattern": r"deepseek-v[3-9]|kimi-k2|minimax-m2|gpt-oss-120b|mistral-(large|medium)|gemini-3", "bonus": 0.10},
        {"pattern": r"coder", "bonus": 0.05},
        {"pattern": r"(?<![a-z])(nano|mini|tiny|small|lite)(?![a-z])|(?<![0-9.a-z])[1-9]b(?![a-z0-9])",
         "bonus": -0.10},
    ],
    "probe": {
        "ttl_days": 3, "dead_ttl_days": 7, "short_dead_ttl_days": 1, "max_candidates": 6,
        "max_tokens": 4096, "timeout": 180,
        "budget": {"default": 24, "openrouter": 12},   # requests per service per run
        "services_at_a_time": 4,       # 1 = test one service after another instead of side by side
        "models_at_a_time": 1,         # per service: 1 (gentlest) or 2
        "pause_between_models": 20,    # seconds to rest between two models of the same service
        # popular_then_big: most-used model of the week first (OpenRouter), otherwise the biggest.
        # balanced: newer and name-hinted models first.
        "test_order": "popular_then_big",
    },
    # Last-resort cross-role backups. Written as SEPARATE dicts (LiteLLM only reads the first key of each dict)
    # and kept acyclic on purpose: reviewer has none, so a reviewer outage never bounces between roles.
    "fallbacks": {"implementer": ["architect", "reviewer"], "architect": ["reviewer"]},
    "litellm": {"cooldown_time": 120, "allowed_fails": 2, "num_retries": 2, "request_timeout": 180},
}

# --------------------------------------------------------------------------- quick tests
TOOLS = [{"type": "function", "function": {
    "name": "get_weather", "description": "Get current weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]

TRACE = [
    ("def f(xs, acc=[]):\n    for x in xs:\n        acc.append(x * 2)\n    return acc\n\nf([1, 2])\nprint(f([3]))", "[2, 4, 6]"),
    ('s = "abcdef"\nprint(s[1:5][::-2])', "ec"),
]
TRACE_Q = "What exactly does this Python program print? Answer with only the printed output, no explanation.\n\n"

REVIEW = [
    ('1 def count_vowels(text):\n2     """Count how many of the characters a, e, i, o, u appear in text (lowercase only)."""\n'
     "3     count = 0\n4     for ch in text:\n5         if ch in \"aeiou\":\n6             count = 1\n7     return count", "6"),
    ('1 def average(nums):\n2     """Return the average of a non-empty list of numbers."""\n3     total = 0\n'
     "4     for n in nums:\n5         total += n * n\n6     return total / len(nums)", "5"),
]
REVIEW_Q = ("Exactly one line of this function has a bug that makes it return a wrong value. "
            "Reply with only that line number.\n\n")

FORMAT_Q = ('Return ONLY a JSON object of the form {"steps": ["...", "...", "..."]} with exactly 3 short steps '
            "for adding a unit test to a C++17 CMake project. No prose, no code fences.")
PING_Q = "Reply with the single word OK."


class ProbeError(Exception):
    def __init__(self, status: int, body: str = ""):
        super().__init__(f"HTTP {status}: {body[:160]}")
        self.status, self.body = status, body


class ProviderBlocked(Exception):
    """Temporary problem with a whole service: pause it for this run. `.state` is the status word."""
    state = "offline"


class KeyRefused(ProviderBlocked):
    state = "refused"


class RateLimited(ProviderBlocked):
    state = "limit"


class SettingsBlocked(ProviderBlocked):
    state = "blocked"


class ModelDead(Exception):
    """This one model cannot be used (gone, no free quota, forbidden). `short` = retry sooner."""

    def __init__(self, why: str, short: bool = False):
        super().__init__(why)
        self.short = short


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects only inside the same site, so a key is never sent to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        a, b = urllib.parse.urlparse(req.full_url), urllib.parse.urlparse(newurl)
        if (a.scheme, a.netloc) != (b.scheme, b.netloc):
            raise urllib.error.HTTPError(req.full_url, code, "redirect to another site refused", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SameHostRedirect)


class IO:
    """All network and clock access lives here, so --selftest can swap in a fake one."""

    def now(self) -> float:
        return time.time()

    def sleep(self, s: float) -> None:
        time.sleep(s)

    def get_json(self, url: str, headers: Optional[dict] = None, timeout: int = 30) -> Any:
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
        with _OPENER.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def chat(self, base_url: str, key: str, model: str, messages: list, tools: Optional[list] = None,
             max_tokens: int = 4096, timeout: int = 180) -> dict:
        body: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens}
        if tools:
            body["tools"], body["tool_choice"] = tools, "auto"
        t0, raw = time.time(), ""
        for attempt in (1, 2):
            req = urllib.request.Request(
                base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), method="POST",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": UA})
            try:
                with _OPENER.open(req, timeout=timeout) as r:
                    raw = r.read().decode("utf-8", "replace")
                break
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", "replace")
                if attempt == 1 and e.code == 400 and "temperature" in text.lower() and "temperature" in body:
                    body.pop("temperature")  # some models only accept their default
                    continue
                raise ProbeError(e.code, text) from None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                raise ProbeError(0, str(e)) from None
        try:
            data = json.loads(raw)
        except ValueError:
            raise ProbeError(0, "unreadable reply: " + raw[:80]) from None
        if not isinstance(data, dict):
            raise ProbeError(0, "unexpected reply")
        if data.get("error") and not data.get("choices"):  # some gateways answer 200 with an error body
            err = data["error"] if isinstance(data["error"], dict) else {"message": str(data["error"])}
            code = str(err.get("code", ""))
            raise ProbeError(int(code) if code.isdigit() else 0, json.dumps(err))
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") if isinstance(choice, dict) else None
        return {"message": msg if isinstance(msg, dict) else {}, "latency": time.time() - t0}


# --------------------------------------------------------------------------- data
@dataclass
class Cand:
    provider: str
    model: str
    free: Optional[bool] = None
    ctx: int = 0
    tools: Optional[bool] = None
    created: float = 0.0
    expires: Optional[float] = None
    stealth: bool = False
    pop: int = 0   # 1 = most tokens used this week (OpenRouter), 0 = unknown

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model}"


def deep_merge(a: dict, b: Optional[dict]) -> dict:
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def parse_date(v: Any) -> Optional[float]:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()


def fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def fetch_catalog(io: IO, name: str, p: dict, key: Optional[str] = None) -> list[Cand]:
    key = os.environ.get(p["key_env"], "") if key is None else key
    hdr = {"Authorization": f"Bearer {key}"} if key else {}
    url = p["base_url"].rstrip("/") + "/models"
    out: list[Cand] = []
    if p["catalog"] == "openrouter":
        try:  # most-used models of the week first (documented sort option)
            data = io.get_json(url + "?sort=top-weekly", hdr).get("data", [])
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise
            data = io.get_json(url, hdr).get("data", [])
        for idx, m in enumerate(data, 1):
            mid = m.get("id")
            if not mid:
                continue
            pr = m.get("pricing") or {}
            try:
                free = float(pr.get("prompt", "1")) == 0 and float(pr.get("completion", "1")) == 0
            except (TypeError, ValueError):
                free = False
            if "text" not in ((m.get("architecture") or {}).get("output_modalities") or ["text"]):
                continue
            out.append(Cand(name, mid, free, int(m.get("context_length") or 0),
                            "tools" in (m.get("supported_parameters") or []), float(m.get("created") or 0),
                            parse_date(m.get("expiration_date")), stealth=mid.startswith("openrouter/"), pop=idx))
        return out
    strip = p.get("id_strip", "")
    for d in io.get_json(url, hdr).get("data", []):
        mid = str(d.get("id", ""))
        if mid:
            out.append(Cand(name, mid[len(strip):] if strip and mid.startswith(strip) else mid,
                            True if p.get("assume_free") else None, 0, None, float(d.get("created") or 0)))
    return out


def base_name(model: str) -> str:
    m = model.split("/")[-1].lower()
    return re.sub(r":.*$|-instruct$|-latest$", "", m)


def enrich(cands: list[Cand]) -> None:
    """NVIDIA/Mistral/Google lists carry no context size, release date or popularity. If the same model shows
    up in a richer list (usually OpenRouter), borrow its details so those services are not ranked down unfairly."""
    ctx_ref: dict[str, int] = {}
    born_ref: dict[str, float] = {}
    pop_ref: dict[str, int] = {}
    for c in cands:
        n = base_name(c.model)
        if c.ctx:
            ctx_ref.setdefault(n, c.ctx)
        if c.created >= 1_000_000_000:
            born_ref.setdefault(n, c.created)
        if c.pop:
            pop_ref[n] = min(c.pop, pop_ref.get(n, c.pop))
    for c in cands:
        n = base_name(c.model)
        if not c.ctx and n in ctx_ref:
            c.ctx = ctx_ref[n]
        if c.created < 1_000_000_000 and n in born_ref:
            c.created = born_ref[n]
        if not c.pop and n in pop_ref:
            c.pop = pop_ref[n]


def static_reason(cfg: dict, p: dict, c: Cand, now: float) -> Optional[str]:
    """Why a candidate is rejected before any testing (None = keep)."""
    if re.search(cfg["exclude"], c.model, re.I):
        return "not a chat model"
    if p.get("include") and not re.search(p["include"], c.model, re.I):
        return "not in provider include list"
    for b in cfg["block"]:
        if b == c.key or re.search(b, c.key):
            return "blocked"
    if c.free is not True:
        return "not free" if c.free is False else "free status unknown"
    if c.tools is False:
        return "no tool calling"
    if c.expires and c.expires - now < cfg["min_days_before_expiry"] * DAY:
        return "expires soon"
    return None


# --------------------------------------------------------------------------- scoring
def size_b(model: str) -> Optional[float]:
    nums = [float(x) for x in re.findall(r"(?<![0-9.a-z])(\d{1,4}(?:\.\d)?)b(?![a-z0-9])", model.lower())]
    return max(nums) if nums else None


def prior(cfg: dict, c: Cand) -> float:
    s = 0.35
    for rule in cfg["priors"]:
        if re.search(rule["pattern"], c.model, re.I):
            s += rule["bonus"]
    sz = size_b(c.model)
    if sz:
        s += 0.25 * min(1.0, math.log10(max(sz, 1.0)) / 3) - 0.10
    return max(0.0, min(1.0, s))


def recency(c: Cand, now: float) -> float:
    if c.created < 1_000_000_000:  # missing or placeholder timestamps -> neutral
        return 0.5
    return max(0.0, 1.0 - (now - c.created) / (365 * DAY))


def ctx_score(c: Cand) -> float:
    if not c.ctx:
        return 0.5
    return max(0.0, min(1.0, math.log2(max(c.ctx, 8192) / 8192) / math.log2(1_048_576 / 8192)))


def mean(xs: list) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def order_for_testing(cfg: dict, cands: list[Cand], now: float) -> list[Cand]:
    """Which models to test first."""
    if cfg["probe"].get("test_order") == "balanced":
        return sorted(cands, key=lambda c: -(prior(cfg, c) + recency(c, now)))
    return sorted(cands, key=lambda c: (c.pop or 10**6, -(size_b(c.model) or 0.0), -(prior(cfg, c) + recency(c, now))))


def as_text(content: Any) -> str:
    if isinstance(content, list):  # some services return a list of content parts
        return "".join(str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in content)
    return content if isinstance(content, str) else ""


def clean(text: Any) -> str:
    t = re.sub(r"<think>.*?</think>", "", as_text(text), flags=re.S | re.I).strip()
    return re.sub(r"^```[a-zA-Z]*\n?|```$", "", t, flags=re.M).strip()


def check_answer(text: Any, expected: str) -> int:
    lines = [ln for ln in clean(text).splitlines() if ln.strip()]
    last = lines[-1].strip().strip("`'\"*. ") if lines else ""
    if expected.isdigit():
        m = re.fullmatch(r"(?:line\s*)?(\d+)", last, re.I)
        return int(bool(m and m.group(1) == expected))
    return int(last == expected)


def check_json(text: Any) -> int:
    try:
        d = json.loads(clean(text))
    except ValueError:
        return 0
    steps = d.get("steps") if isinstance(d, dict) else None
    return int(isinstance(steps, list) and len(steps) == 3 and all(isinstance(s, str) for s in steps))


def summarize(res: dict) -> str:
    if res.get("dead"):
        return f"unusable ({res['why']})"
    if not res.get("tools"):
        return "cannot use tools, skipped"
    return (f"tools ok, code {sum(res['trace'])}/{len(res['trace'])}, bugs {sum(res['review'])}/{len(res['review'])}, "
            f"json {'ok' if res['format'] else 'no'}, {res['lat']:.0f}s per answer")


def probe_candidate(io: IO, cfg: dict, p: dict, key: str, c: Cand) -> tuple[dict, int]:
    """Quick-test one model. Returns (result, requests_used). Raises ProviderBlocked for temporary problems."""
    gap, pc, used = 60.0 / p.get("rpm", 20), cfg["probe"], 0

    def ask(content: str, tools: Optional[list] = None) -> dict:
        nonlocal used
        used += 1
        try:
            r = io.chat(p["base_url"], key, c.model, [{"role": "user", "content": content}], tools,
                        pc["max_tokens"], pc["timeout"])
        except ProbeError as e:
            low = e.body.lower()
            if e.status == 429 and re.search(r'limit"?\s*:\s*"?0\b', e.body):
                raise ModelDead("no free quota (limit 0)") from None
            if e.status == 404 and "data policy" in low:
                raise SettingsBlocked("your account settings block free models "
                                      "(OpenRouter: turn on free endpoints at openrouter.ai/settings/privacy)") from None
            if e.status == 401:
                raise KeyRefused(str(e)) from None
            if e.status == 429:
                raise RateLimited(str(e)) from None
            if e.status == 0 or e.status >= 500:
                raise ProviderBlocked(str(e)) from None
            raise ModelDead(str(e), short=e.status in (402, 403)) from None
        io.sleep(gap)
        return r

    try:
        r = ask("What's the weather in Paris right now? Use the tool.", TOOLS)
        ok = 0
        for call in (r["message"].get("tool_calls") or []):
            fn = call.get("function") or {}
            if fn.get("name") == "get_weather":
                args = fn.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args or "{}")
                    except ValueError:
                        args = {}
                if isinstance(args, dict) and "paris" in str(args.get("city", "")).lower():
                    ok = 1
        res: dict[str, Any] = {"tools": ok, "trace": [], "review": [], "format": 0, "lat": r["latency"]}
        if not ok:
            return res, used
        lats = [r["latency"]]
        for prog, exp in TRACE:
            a = ask(TRACE_Q + prog)
            res["trace"].append(check_answer(a["message"].get("content"), exp))
            lats.append(a["latency"])
        for code, exp in REVIEW:
            a = ask(REVIEW_Q + code)
            res["review"].append(check_answer(a["message"].get("content"), exp))
            lats.append(a["latency"])
        a = ask(FORMAT_Q)
        res["format"] = check_json(a["message"].get("content"))
        lats.append(a["latency"])
        res["lat"] = mean(lats)
        return res, used
    except ModelDead as e:
        return {"dead": True, "why": str(e)[:160], "short": e.short}, used


# --------------------------------------------------------------------------- selection
def rank_role(cfg: dict, role: str, cands: list[Cand], probes: dict, incumbents: set, now: float) -> list:
    rc, rows = cfg["roles"][role], []
    w = rc["weights"]
    for c in cands:
        pr = probes.get(c.key)
        if not pr or pr.get("dead") or not pr.get("tools"):
            continue  # the agents need working tool calls for every role
        if c.ctx and c.ctx < rc["min_context"]:
            continue
        try:
            ps = (w["trace"] * mean(pr.get("trace", [])) + w["review"] * mean(pr.get("review", []))
                  + w["format"] * pr.get("format", 0))
        except (TypeError, ValueError):
            continue  # damaged saved result: ignore it
        lat = pr.get("lat", 0)
        score = (0.55 * ps + 0.20 * prior(cfg, c) + 0.15 * recency(c, now) + 0.10 * ctx_score(c)
                 - (0.0 if lat < 60 else 0.05 if lat < 120 else 0.15))
        if c.stealth:
            score -= cfg["stealth_penalty"]
        if c.key in incumbents:
            score += cfg["stickiness"]
        rows.append((score, c, {"probe": round(ps, 2), "prior": round(prior(cfg, c), 2),
                                "recency": round(recency(c, now), 2), "ctx": round(ctx_score(c), 2)}))
    rows.sort(key=lambda r: -r[0])
    return rows


def pick(rows: list, n: int, cap: int) -> list:
    if n <= 0:
        return []
    chosen: list = []
    skipped: list = []
    per: dict[str, int] = {}
    for r in rows:
        if per.get(r[1].provider, 0) < cap:
            chosen.append(r)
            per[r[1].provider] = per.get(r[1].provider, 0) + 1
        else:
            skipped.append(r)
        if len(chosen) == n:
            return chosen
    return chosen + skipped[: n - len(chosen)]


def select(cfg: dict, cands: list[Cand], probes: dict, prev: dict, now: float) -> tuple[dict, dict, dict]:
    """Returns (picks per role, details per role, status per role: ok | borrowed | unavailable)."""
    pool = {c.key: c for c in cands}
    selected: dict[str, list] = {}
    for role, rc in cfg["roles"].items():
        rows = rank_role(cfg, role, cands, probes, set(prev.get(role, [])), now)
        pins = []
        for k in cfg["pins"].get(role, []):
            c = pool.get(k) or Cand(*k.split(":", 1))
            pins.append((9.0, c, {"pinned": True}))
        rest = [r for r in rows if r[1].key not in {p[1].key for p in pins}]
        selected[role] = (pins + pick(rest, max(0, rc["top_n"] - len(pins)), cfg["max_per_provider"]))[: rc["top_n"]]
    if cfg["independent_reviewer"] and selected.get("reviewer") and selected.get("implementer"):
        top = base_name(selected["implementer"][0][1].model)
        rev = selected["reviewer"]
        if len(rev) > 1 and base_name(rev[0][1].model) == top and not rev[0][2].get("pinned"):
            i = next((j for j, r in enumerate(rev) if base_name(r[1].model) != top), None)
            if i:
                rev.insert(0, rev.pop(i))
    status: dict[str, str] = {}
    for role, rc in cfg["roles"].items():
        if selected[role]:
            status[role] = "ok"
            continue
        borrowed, seen_keys = [], set()
        for other, rows in selected.items():
            if other == role:
                continue
            for score, c, meta in rows:
                if c.key not in seen_keys and len(borrowed) < rc["top_n"]:
                    seen_keys.add(c.key)
                    borrowed.append((score, c, {**meta, "borrowed_from": other}))
        selected[role] = borrowed
        status[role] = "borrowed" if borrowed else "unavailable"
    detail = {role: [{"key": r[1].key, "score": round(r[0], 3), **r[2]} for r in rows] for role, rows in selected.items()}
    return {r: [x[1] for x in rows] for r, rows in selected.items()}, detail, status


def build_litellm(cfg: dict, selected: dict) -> dict:
    ml = []
    for role, lst in selected.items():
        for rank, c in enumerate(lst, 1):
            p = cfg["providers"][c.provider]
            params: dict[str, Any] = {"model": f"{p['litellm_prefix']}/{c.model}",
                                      "api_key": f"os.environ/{p['key_env']}", "order": rank}
            if p.get("litellm_api_base"):
                params["api_base"] = p["litellm_api_base"]
            ml.append({"model_name": role, "litellm_params": params, "model_info": {"id": f"{role}-{rank}"}})
    lit = cfg["litellm"]
    fallbacks = []
    for role, targets in cfg["fallbacks"].items():
        ok = [t for t in targets if selected.get(t)]
        if selected.get(role) and ok:
            fallbacks.append({role: ok})
    return {
        "model_list": ml,
        "general_settings": {"master_key": "os.environ/LITELLM_MASTER_KEY"},
        "litellm_settings": {"drop_params": True, "request_timeout": lit["request_timeout"]},
        "router_settings": {"routing_strategy": "simple-shuffle", "num_retries": lit["num_retries"],
                            "allowed_fails": lit["allowed_fails"], "cooldown_time": lit["cooldown_time"],
                            "fallbacks": fallbacks},
    }


def dump(obj: dict, header: str = "") -> str:
    if yaml is None:
        return json.dumps(obj, indent=2) + "\n"
    return header + yaml.safe_dump(obj, sort_keys=False, default_flow_style=False)


def atomic_write(path: str, text: str, mode: Optional[int] = None) -> None:
    path = os.path.abspath(os.path.expanduser(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode if mode is not None else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def load_state(path: str) -> dict:
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_cands(items: Any) -> list[Cand]:
    out = []
    for d in items or []:
        try:
            out.append(Cand(**d))
        except TypeError:
            continue
    return out


def validate(cfg: dict) -> Optional[str]:
    for role, keys in cfg["pins"].items():
        if role not in cfg["roles"]:
            return f"pins: unknown role '{role}' (use one of: {', '.join(cfg['roles'])})"
        if isinstance(keys, str):
            cfg["pins"][role] = keys = [keys]
        for k in keys:
            if ":" not in k or k.split(":", 1)[0] not in cfg["providers"]:
                return (f"pins: '{k}' must look like service:model, with a service from: "
                        f"{', '.join(cfg['providers'])}")
    return None


def insecure_urls(cfg: dict) -> list[str]:
    out = []
    for name, p in cfg["providers"].items():
        for field in ("base_url", "litellm_api_base"):
            u = p.get(field) or ""
            host = urllib.parse.urlparse(u).hostname or ""
            if u.startswith("http://") and host not in ("127.0.0.1", "localhost", "::1"):
                out.append(f"{name}: {field} uses plain http, so your key would travel unprotected")
    return out


_SAY_LOCK = threading.Lock()


def say(msg: str = "") -> None:
    with _SAY_LOCK:  # one write per line, so lines from different services never get glued together
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()


def load_config(path: Optional[str] = None) -> dict:
    user: dict = {}
    if path and os.path.exists(os.path.expanduser(path)):
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            user = (yaml.safe_load(f) if yaml else json.load(f)) or {}
    return deep_merge(DEFAULTS, user)


# --------------------------------------------------------------------------- keys
def normalize_key(s: str) -> str:
    return re.sub(r"[\s\"']", "", s or "")


def mask_key(v: str) -> str:
    if not v:
        return ""
    return (v[:3] + "..." + v[-4:]) if len(v) > 12 else "..." + v[-2:]


def read_keys(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            text = f.read().replace("\r", "")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def write_keys(cfg: dict, path: str, data: dict[str, str], backup: bool = True) -> None:
    path = os.path.abspath(os.path.expanduser(path))
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    if backup and os.path.exists(path):
        shutil.copy2(path, path + ".bak")
        os.chmod(path + ".bak", 0o600)
    order = [p["key_env"] for p in cfg["providers"].values()] + ["LITELLM_MASTER_KEY"]
    lines = [f"{k}={data.get(k, '')}" for k in order] + [f"{k}={v}" for k, v in data.items() if k not in order]
    atomic_write(path, "\n".join(lines) + "\n", 0o600)


def ensure_master(cfg: dict, path: str) -> bool:
    keys = read_keys(path)
    if keys.get("LITELLM_MASTER_KEY"):
        return False
    keys["LITELLM_MASTER_KEY"] = "sk-" + secrets.token_hex(16)
    write_keys(cfg, path, keys)
    return True


def record_status(state: dict, name: str, status: str, msg: str, now: float, key: str = "") -> None:
    state.setdefault("services", {})[name] = {"status": status, "msg": msg[:160], "ts": now}
    bad = state.setdefault("bad_keys", {})
    if status == "refused" and key:
        bad[name] = fingerprint(key)
    elif status in ("ok", "limit", "blocked", "warn"):
        bad.pop(name, None)


def test_service(cfg: dict, io: IO, name: str, p: dict, key: str, now: float) -> tuple[str, str, list, int]:
    """Check one service with an explicit key. Returns (status, message, usable models, models listed)."""
    try:
        got = fetch_catalog(io, name, p, key)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return "refused", f"the service answered {e.code}: the key was refused", [], 0
        return "offline", f"the service answered {e.code}", [], 0
    except Exception as e:  # noqa: BLE001
        return "offline", f"could not read the model list ({str(e)[:100]})", [], 0
    kept = [c for c in got if static_reason(cfg, p, c, now) is None]
    if not kept:
        return "warn", f"the list loaded ({len(got)} models) but none look free and usable right now", [], len(got)
    best = sorted(kept, key=lambda c: -(prior(cfg, c) + recency(c, now)))
    try:
        io.chat(p["base_url"], key, best[0].model, [{"role": "user", "content": PING_Q}], None, 30, 90)
    except ProbeError as e:
        if e.status in (401, 403):
            return "refused", f"the service answered {e.status}: the key was refused", best, len(got)
        if e.status == 404 and "data policy" in e.body.lower():
            return ("blocked", "your account settings block free models "
                    "(OpenRouter: openrouter.ai/settings/privacy)", best, len(got))
        if e.status == 429:
            return "limit", "key accepted, but the free allowance is used up right now", best, len(got)
        if e.status == 0:
            return "offline", f"could not reach the service ({e.body[:80]})", best, len(got)
        return "ok", f"key accepted (the test model answered {e.status})", best, len(got)
    return "ok", "key accepted", best, len(got)


def set_key(cfg: dict, io: IO, service: str, newkey: str, keys_path: str, state_path: str,
            force: bool = False) -> tuple[bool, str, str]:
    """Test a key and save it if it works. Returns (saved, status, message). The old key stays if the new one fails."""
    p = cfg["providers"].get(service)
    if not p:
        return False, "unknown", f"unknown service '{service}' (use one of: {', '.join(cfg['providers'])})"
    newkey = normalize_key(newkey)
    if not newkey:
        return False, "empty", "no key was entered"
    now = io.now()
    status, msg, _, _ = test_service(cfg, io, service, p, newkey, now)
    if status in ("refused", "offline") and not force:
        return False, status, msg
    keys = read_keys(keys_path)
    keys[p["key_env"]] = newkey
    write_keys(cfg, keys_path, keys)
    state = load_state(state_path)
    record_status(state, service, status if status not in ("refused", "offline") else "warn", msg, now)
    atomic_write(state_path, json.dumps(state, indent=1))
    return True, status, msg


def remove_key(cfg: dict, service: str, keys_path: str, state_path: str, now: float) -> tuple[bool, str]:
    p = cfg["providers"].get(service)
    if not p:
        return False, f"unknown service '{service}'"
    keys = read_keys(keys_path)
    keys[p["key_env"]] = ""
    write_keys(cfg, keys_path, keys)
    state = load_state(state_path)
    record_status(state, service, "skip", f"{p['key_env']} is not set", now)
    atomic_write(state_path, json.dumps(state, indent=1))
    return True, "removed"


def keys_table(cfg: dict, keys_path: str, state_path: str) -> list[dict]:
    keys, state = read_keys(keys_path), load_state(state_path)
    out = []
    for name, p in cfg["providers"].items():
        k = keys.get(p["key_env"], "")
        st = (state.get("services") or {}).get(name) or {}
        status = st.get("status", "skip" if not k else "unknown")
        if not k:
            status = "skip"
        out.append({"service": name, "env": p["key_env"], "saved": bool(k), "masked": mask_key(k),
                    "status": status, "msg": st.get("msg", ""), "ts": st.get("ts", 0)})
    return out


# --------------------------------------------------------------------------- check
def check(cfg: dict, io: IO, state_path: Optional[str] = None) -> int:
    now, ready = io.now(), 0
    state = load_state(state_path) if state_path else {}
    say("Checking your keys and the free-model lists (at most one tiny request per service).\n")
    for name, p in cfg["providers"].items():
        if not p.get("enabled", True):
            continue
        env = p["key_env"]
        key = os.environ.get(env, "")
        if not key:
            record_status(state, name, "skip", f"{env} is not set", now)
            say(f"{LABELS['skip']:<10}{name}: {env} is not set")
            continue
        status, msg, kept, listed = test_service(cfg, io, name, p, key, now)
        record_status(state, name, status, msg, now, key)
        extra = f"; {len(kept)} free models look usable (of {listed} listed)" if kept else ""
        say(f"{LABELS.get(status, '[?]'):<10}{name}: {msg}{extra}")
        if status in ("ok", "limit", "blocked"):
            ready += 1
        for c in kept[:5] if status == "ok" else []:
            say(f"             {c.model}")
    if state_path:
        atomic_write(state_path, json.dumps(state, indent=1))
    say("")
    if ready:
        say(f"{ready} service(s) ready. Next: run the model picker with --probe.")
        return 0
    say("No service is ready. Fix the keys or your connection and run --check again.")
    return 1


# --------------------------------------------------------------------------- run
def run(cfg: dict, io: IO, args: argparse.Namespace) -> int:
    now = io.now()
    problem = validate(cfg)
    if problem:
        say(f"Settings problem: {problem}")
        return 1
    state = load_state(args.state)
    probes, dead = state.setdefault("probes", {}), state.setdefault("dead", {})
    bad = state.setdefault("bad_keys", {})
    notes: list[str] = list(insecure_urls(cfg))
    cands: list[Cand] = []
    attempted: set[str] = set()
    fetched: set[str] = set()
    for name, p in cfg["providers"].items():
        if not p.get("enabled", True):
            continue
        key = os.environ.get(p["key_env"], "")
        if not key:
            record_status(state, name, "skip", f"{p['key_env']} is not set", now)
            notes.append(f"{name}: {p['key_env']} is not set, service skipped")
            continue
        if bad.get(name) == fingerprint(key):
            record_status(state, name, "refused", "this key was refused earlier - replace it", now)
            notes.append(f"{name}: the saved key was refused earlier, service skipped "
                         f"(replace it with: harness set-key {name})")
            continue
        attempted.add(name)
        cached = load_cands(state.get("catalog", {}).get(name))
        try:
            got = fetch_catalog(io, name, p, key)
            kept = [c for c in got if static_reason(cfg, p, c, now) is None]
            state.setdefault("catalog", {})[name] = [asdict(c) for c in kept]
            fetched.add(name)
            record_status(state, name, "ok", f"{len(kept)} free models look usable", now)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                record_status(state, name, "refused", f"the service answered {e.code}: the key was refused", now, key)
                notes.append(f"{name}: the key was refused ({e.code}), service skipped "
                             f"(replace it with: harness set-key {name})")
                continue
            kept = cached
            record_status(state, name, "offline", f"the service answered {e.code}", now)
            notes.append(f"{name}: the service answered {e.code}; using the last good list ({len(kept)} models)")
        except Exception as e:  # noqa: BLE001 - any network or format problem: use the last good list
            kept = cached
            record_status(state, name, "offline", f"could not reach it ({str(e)[:80]})", now)
            notes.append(f"{name}: could not read the model list ({str(e)[:80]}); using the last good list "
                         f"({len(kept)} models)")
        cands += kept
    if args.probe and not args.dry_run and attempted and not fetched:
        say("\n".join(f"note: {n}" for n in notes))
        say("Could not reach any AI service, so nothing was changed or saved. "
            "Check your internet connection and keys (run --check), then try again.")
        atomic_write(args.state, json.dumps(state, indent=1)) if not args.dry_run else None
        return 1
    enrich(cands)
    pool = {c.key: c for c in cands}

    seen = {c.key for c in cands}
    prev_seen = set(state.get("seen_free", []))
    new_free = sorted(seen - prev_seen) if prev_seen else []
    gone = sorted(k for k in prev_seen - seen if k.split(":", 1)[0] in fetched)
    soon = [c for c in cands if c.expires and c.expires - now < 14 * DAY]

    pc = cfg["probe"]
    if args.probe and args.dry_run:
        notes.append("dry run: no quick tests were run")
    elif args.probe:
        by_prov: dict[str, list[Cand]] = {}
        for c in order_for_testing(cfg, cands, now):
            if now < dead.get(c.key, 0):
                continue
            if c.key in probes and now - probes[c.key].get("ts", 0) < pc["ttl_days"] * DAY:
                continue
            by_prov.setdefault(c.provider, []).append(c)
        if by_prov:
            say("Quick-testing new models, one at a time per service, resting between models "
                "(this can take several minutes)...")

        def serve(prov: str) -> tuple[str, list, dict]:
            p, key = cfg["providers"][prov], os.environ[cfg["providers"][prov]["key_env"]]
            items = by_prov[prov][: pc["max_candidates"]]
            lanes = max(1, min(2, int(pc["models_at_a_time"])))
            lock, stop = threading.Lock(), threading.Event()
            budget = {"left": pc["budget"].get(prov, pc["budget"]["default"])}
            done: list = []
            halt: dict = {}

            def lane(idx: int, chunk: list) -> None:
                if idx:
                    io.sleep(pc["pause_between_models"] / 2)  # second lane starts half a pause later
                for n, c in enumerate(chunk):
                    if stop.is_set():
                        return
                    with lock:
                        if budget["left"] < 6:
                            return
                        budget["left"] -= 6  # reserve the most one model can use
                    try:
                        res, used = probe_candidate(io, cfg, p, key, c)
                    except ProviderBlocked as e:
                        with lock:
                            halt.update(state=e.state, msg=str(e))
                            stop.set()
                        return
                    except Exception as e:  # noqa: BLE001 - one odd reply must not crash the whole run
                        with lock:
                            notes.append(f"{c.key}: skipped, unexpected reply ({type(e).__name__}: {str(e)[:60]})")
                        continue
                    with lock:
                        budget["left"] += 6 - used
                        done.append((c.key, res))
                    say(f"  tested {c.key}: {summarize(res)}")
                    if n < len(chunk) - 1 and not stop.is_set():
                        io.sleep(pc["pause_between_models"])

            with ThreadPoolExecutor(max_workers=lanes) as lx:
                list(lx.map(lambda a: lane(a[0], a[1]), enumerate([items[i::lanes] for i in range(lanes)])))
            return prov, done, halt

        provs = list(by_prov)
        with ThreadPoolExecutor(max_workers=max(1, min(len(provs) or 1, int(pc["services_at_a_time"])))) as ex:
            for prov, done, halt in ex.map(serve, provs):
                for k, res in done:
                    if res.get("dead"):
                        ttl = pc["short_dead_ttl_days"] if res.get("short") else pc["dead_ttl_days"]
                        dead[k] = now + ttl * DAY
                        probes.pop(k, None)
                        notes.append(f"{k}: unusable ({res['why']})")
                    else:
                        probes[k] = {**res, "ts": now}
                if halt:
                    st, msg = halt["state"], halt["msg"]
                    record_status(state, prov, st, msg, now, os.environ.get(cfg["providers"][prov]["key_env"], ""))
                    notes.append(f"{prov}: quick tests paused ({msg[:90]}); will retry next run")
                    say(f"  {prov}: {LABELS.get(st, st)} pausing quick tests ({msg[:70]}). Will retry next run.")
    else:
        notes.append("no new quick tests (only saved results are used)")

    refused = {n for n, s in (state.get("services") or {}).items() if s.get("status") == "refused"}
    cands = [c for c in cands if c.provider not in refused]

    run_cfg = cfg
    pins = {}
    for role, keys in cfg["pins"].items():
        ok_keys = [k for k in keys if os.environ.get(cfg["providers"][k.split(":", 1)[0]]["key_env"])
                   and k.split(":", 1)[0] not in refused]
        for k in set(keys) - set(ok_keys):
            notes.append(f"pin {k} ignored: its key is not set or was refused")
        pins[role] = ok_keys
    if pins != cfg["pins"]:
        run_cfg = deep_merge(cfg, {})
        run_cfg["pins"] = pins

    prev_sel = state.get("selected", {})
    selected, detail, role_status = select(run_cfg, cands, probes, prev_sel, now)
    if not any(selected.values()):
        keep = {r: [pool.get(k) or Cand(*k.split(":", 1)) for k in prev_sel.get(r, [])
                    if k.split(":", 1)[0] in cfg["providers"] and k.split(":", 1)[0] not in refused]
                for r in cfg["roles"]}
        if any(keep.values()):
            selected, role_status = keep, {r: ("ok" if keep[r] else "unavailable") for r in keep}
            detail = {r: [{"key": c.key, "score": 0.0, "probe": 0, "prior": 0, "recency": 0, "ctx": 0} for c in keep[r]]
                      for r in keep}
            notes.append("WARNING: no model could be verified this run; kept the previous picks")
    if not any(selected.values()):
        say("\n".join(f"note: {n}" for n in notes))
        say("ERROR: no working free model was found for any role. Every service is offline, refused or has no "
            "usable free model right now. Run --check to see why. The existing router list was left untouched.")
        if not args.dry_run:
            atomic_write(args.state, json.dumps(state, indent=1))
        return 1
    new_sel = {r: [c.key for c in lst] for r, lst in selected.items()}
    changed = new_sel != prev_sel or not os.path.exists(os.path.expanduser(args.out))
    stamp = f"{datetime.fromtimestamp(now, timezone.utc):%Y-%m-%d %H:%M}"
    text = dump(build_litellm(cfg, selected), f"# generated by model_scout.py {stamp}Z - do not edit by hand\n")

    lines = [f"# Model picker report - {stamp} UTC", "", "## Services"]
    for name, s in (state.get("services") or {}).items():
        if name in cfg["providers"]:
            lines.append(f"{LABELS.get(s.get('status'), '[?]'):<10}{name} - {s.get('msg', '')}")
    lines.append("")
    for role, rows in detail.items():
        rs = role_status.get(role, "ok")
        tag = {"ok": "", "borrowed": " (no model of its own right now - using picks from other roles)",
               "unavailable": " (UNAVAILABLE - no working model right now)"}[rs]
        lines.append(f"## {role}{tag}")
        for i, d in enumerate(rows, 1):
            if d.get("pinned"):
                extra = "locked in by you"
            elif d.get("borrowed_from"):
                extra = f"borrowed from {d['borrowed_from']}"
            else:
                extra = f"score {d['score']} (tests {d['probe']}, hints {d['prior']}, newness {d['recency']}, size {d['ctx']})"
            lines.append(f"{i}. {d['key']} - {extra}")
        lines.append("")
    for role in cfg["roles"]:
        a, b = set(prev_sel.get(role, [])), set(new_sel.get(role, []))
        lines += [f"+ {role}: {k}" for k in sorted(b - a)] + [f"- {role}: {k}" for k in sorted(a - b)]
    lines += ["", "New free models since last run: " + (", ".join(new_free) or "none"),
              "No longer offered: " + (", ".join(gone) or "none"),
              "Expiring within 14 days: " + (", ".join(
                  f"{c.key} ({datetime.fromtimestamp(c.expires or 0, timezone.utc):%Y-%m-%d})" for c in soon) or "none"),
              ""] + [f"note: {n}" for n in notes]
    report = "\n".join(lines) + "\n"
    say("\n" + report)

    if args.dry_run:
        say("(dry run: nothing was written and no quick tests were run)")
        return 10 if changed else 0
    for k in [k for k, v in probes.items() if k not in seen and now - v.get("ts", 0) > 30 * DAY]:
        del probes[k]
    for k in [k for k, v in dead.items() if v < now]:
        del dead[k]
    state.update({"selected": new_sel, "role_status": role_status, "seen_free": sorted(seen), "updated": now})
    atomic_write(args.state, json.dumps(state, indent=1))
    atomic_write(args.report, report)
    if changed:
        atomic_write(args.out, text)
        say(f"Router list written to {args.out}")
        if args.on_change:
            subprocess.run(args.on_change, shell=True, check=False)  # nosec B602 - the command is the one you typed yourself
    else:
        say("No change in the picks.")
    return 10 if changed else 0


# --------------------------------------------------------------------------- selftest
DEFAULT_SKILLS = {"tools", "trace", "review", "format"}


def fake_answer(model: str, messages: list, tools: Optional[list], skills: dict) -> dict:
    """Pretend to be a model. `skills` says which quick tests each fake model passes."""
    sk = skills.get(model, DEFAULT_SKILLS)
    if "429" in sk:
        raise ProbeError(429, "rate limited")
    if "nofree" in sk:
        raise ProbeError(429, "Quota exceeded for metric x, limit: 0, model: y")
    if "403" in sk:
        raise ProbeError(403, "forbidden")
    if "401" in sk:
        raise ProbeError(401, "invalid api key")
    if "datapolicy" in sk:
        raise ProbeError(404, "No endpoints found matching your data policy (Free model publication)")
    u = messages[-1]["content"]
    if tools:
        if "tools" not in sk:
            return {"content": "I cannot call tools"}
        args: Any = {"city": "Paris"}
        return {"tool_calls": [{"function": {"name": "get_weather", "arguments": args if "argdict" in sk else json.dumps(args)}}]}
    if "acc=[]" in u:
        a = "[2, 4, 6]" if "trace" in sk else "[6]"
    elif "[1:5]" in u:
        a = "ec" if "trace" in sk else "ce"
    elif "count_vowels" in u:
        a = "6" if "review" in sk else "4"
    elif "def average" in u:
        a = "5" if "review" in sk else "2"
    elif "JSON object" in u:
        a = '<think>hmm</think>{"steps": ["a", "b", "c"]}' if "format" in sk else "Sure! Steps: 1) a 2) b"
    else:
        a = "OK"
    return {"content": a}


class FakeIO(IO):
    def __init__(self, t: float, catalogs: dict, skills: dict):
        self.t, self.catalogs, self.skills = t, catalogs, skills
        self.calls = 0
        self.by_host: dict[str, int] = {}
        self.order: list[tuple[str, str]] = []
        self.sleeps: list[float] = []
        self.active: dict[str, int] = {}
        self.peak: dict[str, int] = {}
        self.gactive = self.gpeak = 0
        self._lock = threading.Lock()

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)

    def get_json(self, url: str, headers: Optional[dict] = None, timeout: int = 30) -> Any:
        for host, payload in self.catalogs.items():
            if host in url:
                return payload
        raise ProbeError(404, url)

    def chat(self, base_url, key, model, messages, tools=None, max_tokens=4096, timeout=180) -> dict:  # noqa: ANN001
        with self._lock:
            self.calls += 1
            self.by_host[base_url] = self.by_host.get(base_url, 0) + 1
            self.order.append((base_url, model))
            self.active[base_url] = self.active.get(base_url, 0) + 1
            self.peak[base_url] = max(self.peak.get(base_url, 0), self.active[base_url])
            self.gactive += 1
            self.gpeak = max(self.gpeak, self.gactive)
        try:
            time.sleep(0.003)  # long enough for overlaps to show up
            return {"message": fake_answer(model, messages, tools, self.skills), "latency": 3.0}
        finally:
            with self._lock:
                self.active[base_url] -= 1
                self.gactive -= 1


class _FakeProvider(BaseHTTPRequestHandler):
    """A tiny local web server that behaves like an AI service, so the REAL network code can be tested."""

    def log_message(self, *a: Any) -> None:
        pass

    def _send(self, code: int, body: Any, ctype: str = "application/json", headers: Optional[dict] = None) -> None:
        raw = body if isinstance(body, bytes) else (body.encode() if isinstance(body, str) else json.dumps(body).encode())
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        srv = self.server
        if path.startswith("/redir/"):
            return self._send(302, b"", headers={"Location": f"http://127.0.0.1:{srv.other_port}/or/api/v1/models"})  # type: ignore[attr-defined]
        payload = srv.catalogs.get(path)  # type: ignore[attr-defined]
        self._send(200, payload) if payload is not None else self._send(404, {"error": "nope"})

    def do_POST(self) -> None:  # noqa: N802
        srv = self.server
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        srv.auth_seen.add(self.headers.get("Authorization"))  # type: ignore[attr-defined]
        srv.chat_calls += 1  # type: ignore[attr-defined]
        model = body.get("model")
        if "garbage" in srv.skills.get(model, ()):  # type: ignore[attr-defined]
            return self._send(200, b"<html>maintenance</html>", "text/html")
        if "badkey" in self.headers.get("Authorization", ""):
            return self._send(401, "invalid api key")
        try:
            msg = fake_answer(model, body.get("messages", []), body.get("tools"), srv.skills)  # type: ignore[attr-defined]
        except ProbeError as e:
            return self._send(e.status or 500, str(e.body))
        self._send(200, {"choices": [{"message": msg, "finish_reason": "stop"}]})


def _or(mid, ctx=262144, tools=True, age=100, price="0", exp=None, now=0.0):  # noqa: ANN001
    return {"id": mid, "context_length": ctx, "created": now - age * DAY, "expiration_date": exp,
            "pricing": {"prompt": price, "completion": price}, "supported_parameters": ["tools"] if tools else [],
            "architecture": {"output_modalities": ["text"]}}


def quiet(fn, *a, **k):  # noqa: ANN001, ANN002, ANN003
    """Run fn and swallow what it prints (returns (result, printed_text))."""
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = fn(*a, **k)
    return res, buf.getvalue()


def selftest() -> int:
    for p in DEFAULTS["providers"].values():
        os.environ[p["key_env"]] = "fake-" + p["key_env"].lower()
    now = 1_790_000_000.0
    iso = lambda d: datetime.fromtimestamp(now + d * DAY, timezone.utc).strftime("%Y-%m-%d")  # noqa: E731
    cat1 = {
        "openrouter.ai": {"data": [   # listed in 'top-weekly' order: most used first
            _or("z-ai/glm-5.3-flash:free", 1_000_000, age=20, now=now),
            _or("mistralai/devstral-2512:free", 262144, age=300, now=now),
            _or("nvidia/nemotron-3-ultra-550b-a55b:free", 1_000_000, age=120, now=now),
            _or("meta-llama/llama-3.3-70b-instruct:free", 131072, age=500, now=now),
            _or("google/gemma-3-4b-it:free", 32768, tools=False, age=400, now=now),
            _or("openai/gpt-5-mini", 400000, price="0.0000003", age=60, now=now),
            _or("nvidia/llama-nemotron-embed-1b-v2:free", 8192, age=90, now=now),
            _or("acme/promo-coder:free", 262144, age=5, exp=iso(2), now=now),
            _or("openrouter/aurora-alpha", 262144, age=3, now=now),
            _or("openrouter/free", 262144, age=3, now=now),
        ]},
        "integrate.api.nvidia.com": {"data": [{"id": "meta/llama-3.2-1b-instruct", "created": 735790403},
                                              {"id": "qwen/qwen3-coder-480b-a35b-instruct", "created": 735790403},
                                              {"id": "nvidia/nemotron-3-ultra-550b-a55b", "created": 735790403},
                                              {"id": "nvidia/nv-embedqa-e5-v5", "created": 735790403}]},
        "api.mistral.ai": {"data": [{"id": "devstral-2512", "created": now - 300 * DAY},
                                    {"id": "mistral-embed", "created": now - 300 * DAY}]},
        "generativelanguage.googleapis.com": {"data": [{"id": "models/gemini-3.7-flash", "created": 0},
                                                       {"id": "models/gemini-3.1-pro-preview", "created": 0},
                                                       {"id": "models/gemini-3.7-flash-image", "created": 0}]},
    }
    skills = {   # which quick tests each fake model passes (unlisted = passes everything)
        "meta-llama/llama-3.3-70b-instruct:free": {"tools", "format"},
        "meta/llama-3.2-1b-instruct": {"tools"},
        "devstral-2512": {"tools", "trace", "format"},
        "nvidia/nemotron-3-ultra-550b-a55b:free": {"tools", "trace", "review"},      # fails the JSON test
        "qwen/qwen3-coder-480b-a35b-instruct": {"tools", "trace", "format"},          # fails bug-finding
    }
    tmp = tempfile.mkdtemp()

    def check_(cond: bool, msg: str) -> None:
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            raise SystemExit(f"selftest failed: {msg}")

    def ns(tag: str, **kw: Any) -> argparse.Namespace:
        d = dict(state=f"{tmp}/{tag}-state.json", out=f"{tmp}/{tag}-litellm.yaml", report=f"{tmp}/{tag}-report.md",
                 probe=True, dry_run=False, on_change=None)
        d.update(kw)
        return argparse.Namespace(**d)

    big = {"probe": {"budget": {"default": 500, "openrouter": 500}, "max_candidates": 50}}
    try:
        print("== settings are validated")
        bad = deep_merge(DEFAULTS, {"pins": {"reviewer": ["no-colon-here"]}})
        _, out = quiet(run, bad, FakeIO(now, cat1, skills), ns("bad"))
        check_("pins:" in out, "a badly written pin gives a clear message instead of a crash")
        okpin = deep_merge(DEFAULTS, {"pins": {"reviewer": "nvidia:foo/bar"}})
        check_(validate(okpin) is None and okpin["pins"]["reviewer"] == ["nvidia:foo/bar"], "a single pin written as text is accepted")
        check_(bool(insecure_urls(deep_merge(DEFAULTS, {"providers": {"nvidia": {"base_url": "http://example.com/v1"}}}))),
               "a plain-http service address is flagged")

        print("== answers are read sensibly")
        check_(check_answer("<think>2+2</think>\n[2, 4, 6]", "[2, 4, 6]") == 1, "thinking text before the answer is ignored")
        check_(check_json([{"type": "text", "text": '{"steps": ["a","b","c"]}'}]) == 1, "answers sent as a list of parts are read")
        check_(check_answer("Line 6", "6") == 1 and check_answer("5", "6") == 0, "bug-line answers are checked strictly")

        print("== default test budget protects the scarce OpenRouter free quota")
        io0 = FakeIO(now, cat1, skills)
        quiet(run, deep_merge(DEFAULTS, {}), io0, ns("r0"))
        n_or = io0.by_host.get("https://openrouter.ai/api/v1", 0)
        check_(0 < n_or <= DEFAULTS["probe"]["budget"]["openrouter"], f"OpenRouter tests capped at the budget ({n_or} <= 12)")

        print("== --dry-run spends nothing and writes nothing")
        iod = FakeIO(now, cat1, skills)
        a = ns("dry", dry_run=True)
        quiet(run, deep_merge(DEFAULTS, {}), iod, a)
        check_(iod.calls == 0 and not any(os.path.exists(x) for x in (a.state, a.out, a.report)),
               "no requests sent, no files created")

        print("== gentle pacing: one model at a time per service, with a rest between models")
        cfg = deep_merge(DEFAULTS, big)
        a = ns("main")
        io = FakeIO(now, cat1, skills)
        rc, out = quiet(run, cfg, io, a)
        check_(rc == 10, "list written (exit code 10)")
        check_(all(v <= 1 for v in io.peak.values()), f"never two models at once on the same service (peak {io.peak})")
        check_(DEFAULTS["probe"]["pause_between_models"] in io.sleeps, "it rests between two models of the same service")
        nv = [m for h, m in io.order if "nvidia" in h]
        first_nv = list(dict.fromkeys(nv))
        check_(first_nv[:3] == ["nvidia/nemotron-3-ultra-550b-a55b", "qwen/qwen3-coder-480b-a35b-instruct",
                                 "meta/llama-3.2-1b-instruct"], "NVIDIA: the biggest model is tested first")
        orr = list(dict.fromkeys(m for h, m in io.order if "openrouter" in h))
        check_(orr[0] == "z-ai/glm-5.3-flash:free", "OpenRouter: the most-used model of the week is tested first")
        check_("tested nvidia:nvidia/nemotron-3-ultra-550b-a55b" in out, "progress lines are printed while testing")

        io_two = FakeIO(now, cat1, skills)
        quiet(run, deep_merge(cfg, {"probe": {"models_at_a_time": 2}}), io_two, ns("two"))
        check_(max(io_two.peak.values()) <= 2, "with models_at_a_time = 2 never more than two at once per service")
        io_seq = FakeIO(now, cat1, skills)
        quiet(run, deep_merge(cfg, {"probe": {"services_at_a_time": 1}}), io_seq, ns("seq"))
        check_(io_seq.gpeak <= 1, "with services_at_a_time = 1 only one test runs at any moment")

        print("== picks look right")
        sel = load_state(a.state)["selected"]
        allsel = {k for v in sel.values() for k in v}
        check_(not any(x in k for k in allsel for x in ("embed", "gpt-5-mini", "gemma-3-4b", "promo-coder", "image",
                                                         "pro-preview", "openrouter/free")),
               "embedding, paid, no-tools, expiring, image, non-flash and 'pick for me' models excluded")
        check_("llama-3.2-1b" not in " ".join(allsel), "tiny model that only passes the tool test is not selected")
        check_(all(len({k.split(':')[0] for k in v}) >= 2 for v in sel.values()), "every role spans at least 2 services")
        check_(base_name(sel["reviewer"][0].split(":", 1)[1]) != base_name(sel["implementer"][0].split(":", 1)[1]),
               "independent reviewer: reviewer #1 is a different model from implementer #1")
        check_(not any(i == 0 and k.startswith("openrouter:openrouter/") for v in sel.values() for i, k in enumerate(v)),
               "stealth model is never rank #1")
        first_calls = io.calls

        print("== no internet during a run: nothing is changed or saved")
        before_state, before_out = open(a.state, encoding="utf-8").read(), open(a.out, encoding="utf-8").read()
        rc, _ = quiet(run, cfg, FakeIO(now + 1 * DAY, {}, skills), a)
        st_after = load_state(a.state)
        check_(rc == 1 and open(a.out, encoding="utf-8").read() == before_out and st_after["selected"] == json.loads(before_state)["selected"],
               "run fails clearly (exit code 1); the router list and the picks stay as they were")
        check_(all(s["status"] == "offline" for s in st_after["services"].values()), "every service is shown as [offline]")

        print("== run 2: same day again -> saved results, nothing new")
        rc, _ = quiet(run, cfg, io, a)
        check_(rc == 0 and io.calls == first_calls, "exit code 0 and zero new test requests")

        print("== run 3: a strong new free model appears, another disappears")
        cat3 = copy.deepcopy(cat1)
        cat3["openrouter.ai"]["data"].insert(0, _or("newlab/coder-pro-2:free", 1_000_000, age=2, now=now))
        cat3["openrouter.ai"]["data"] = [m for m in cat3["openrouter.ai"]["data"] if "llama-3.3" not in m["id"]]
        quiet(run, cfg, FakeIO(now + 4 * DAY, cat3, skills), a)
        sel3 = load_state(a.state)["selected"]
        rep = open(a.report, encoding="utf-8").read()
        check_("openrouter:newlab/coder-pro-2:free" in {k for v in sel3.values() for k in v}, "new model was tested and promoted")
        check_("New free models since last run: openrouter:newlab/coder-pro-2:free" in rep, "report lists the new free model")
        check_("No longer offered: openrouter:meta-llama/llama-3.3-70b-instruct:free" in rep, "report lists the vanished model")
        check_("openrouter:meta-llama/llama-3.3-70b-instruct:free" not in {k for v in sel3.values() for k in v},
               "vanished model removed from the list")

        print("== run 4: a service rate-limits us during tests -> nothing marked unusable")
        cat4 = copy.deepcopy(cat3)
        cat4["openrouter.ai"]["data"].insert(0, _or("newlab/other:free", 262144, age=1, now=now))
        quiet(run, cfg, FakeIO(now + 8 * DAY, cat4, dict(skills, **{"newlab/other:free": {"429"}})), a)
        st4 = load_state(a.state)
        check_(not st4["dead"] and st4["services"]["openrouter"]["status"] == "limit", "a rate limit is temporary: shown as [limit], nothing marked unusable")

        print("== run 5: free quota is gone (limit 0) -> model dropped")
        quiet(run, cfg, FakeIO(now + 20 * DAY, cat4, dict(skills, **{"newlab/other:free": {"nofree"}})), a)
        st5 = load_state(a.state)
        check_("openrouter:newlab/other:free" in st5["dead"], "'limit 0' marks the model unusable")

        print("== a key that is refused is remembered until it is replaced")
        cat6 = copy.deepcopy(cat1)
        cat6["openrouter.ai"]["data"].insert(0, _or("newlab/zzz:free", 262144, age=1, now=now))
        a6 = ns("refuse")
        io6 = FakeIO(now, cat6, dict(skills, **{"newlab/zzz:free": {"401"}, "z-ai/glm-5.3-flash:free": {"401"}}))
        quiet(run, cfg, io6, a6)
        st6 = load_state(a6.state)
        check_(st6["services"]["openrouter"]["status"] == "refused" and "openrouter" in st6["bad_keys"], "401 marks the service [refused]")
        check_(not any(k.startswith("openrouter:") for v in st6["selected"].values() for k in v), "a refused service is not used in the picks")
        io6b = FakeIO(now + 1, cat6, skills)
        quiet(run, cfg, io6b, a6)
        check_(not any("openrouter" in h for h in io6b.by_host) and load_state(a6.state)["services"]["openrouter"]["status"] == "refused",
               "next run does not try the refused key again (it prints refused, like skip)")
        os.environ["OPENROUTER_API_KEY"] = "a-new-key"
        io6c = FakeIO(now + 2, cat6, skills)
        quiet(run, cfg, io6c, a6)
        check_(any("openrouter" in h for h in io6c.by_host) and load_state(a6.state)["services"]["openrouter"]["status"] == "ok",
               "after the key is replaced, the service is tried again and clears itself")
        os.environ["OPENROUTER_API_KEY"] = "fake-openrouter_api_key"

        print("== account setting blocks free models (OpenRouter privacy) -> clear message, nothing marked unusable")
        a7 = ns("policy")
        io7 = FakeIO(now, cat1, dict(skills, **{m["id"]: {"datapolicy"} for m in cat1["openrouter.ai"]["data"]}))
        _, out7 = quiet(run, cfg, io7, a7)
        st7 = load_state(a7.state)
        check_(st7["services"]["openrouter"]["status"] == "blocked" and not st7["dead"], "[blocked] is shown and no model is marked unusable")
        check_("settings/privacy" in out7, "the message tells you where to fix it")

        print("== a role with no model of its own borrows from the others instead of staying empty")
        a8 = ns("borrow")
        cfg8 = deep_merge(cfg, {"roles": {"reviewer": {"min_context": 50_000_000}},
                                "providers": {"nvidia": {"enabled": False}, "mistral": {"enabled": False},
                                              "google": {"enabled": False}}})
        quiet(run, cfg8, FakeIO(now, cat1, skills), a8)
        st8 = load_state(a8.state)
        check_(st8["role_status"]["reviewer"] == "borrowed" and st8["selected"]["reviewer"], "reviewer borrows picks from other roles")
        check_("using picks from other roles" in open(a8.report, encoding="utf-8").read(), "the report says so in plain words")
        conf8 = yaml.safe_load(open(a8.out, encoding="utf-8")) if yaml else json.load(open(a8.out, encoding="utf-8"))
        check_("reviewer" in {d["model_name"] for d in conf8["model_list"]}, "the router still has a reviewer group")

        print("== when nothing works anywhere, say so (not 'empty')")
        a9 = ns("none")
        io9 = FakeIO(now, cat1, {m["id"]: {"429"} for m in cat1["openrouter.ai"]["data"]})
        rc, out9 = quiet(run, deep_merge(cfg, {"providers": {"nvidia": {"enabled": False}, "mistral": {"enabled": False},
                                                              "google": {"enabled": False}}}), io9, a9)
        check_(rc == 1 and "no working free model" in out9.lower() and not os.path.exists(a9.out), "exit code 1, clear message, no router list written")

        print("== the REAL network code, against a local fake AI service")
        srv = HTTPServer(("127.0.0.1", 0), _FakeProvider)
        srv2 = HTTPServer(("127.0.0.1", 0), _FakeProvider)
        port = srv.server_address[1]
        srv.other_port = srv2.server_address[1]  # type: ignore[attr-defined]
        srv.catalogs = {  # type: ignore[attr-defined]
            "/or/api/v1/models": {"data": [_or("z-ai/glm-5.3-flash:free", 1_000_000, age=20, now=time.time()),
                                           _or("mistralai/devstral-2512:free", 262144, age=300, now=time.time()),
                                           _or("openai/gpt-5-mini", 400000, price="0.0000003", now=time.time())]},
            "/nv/v1/models": {"data": [{"id": "nvidia/nemotron-3-ultra-550b-a55b"},
                                       {"id": "qwen/qwen3-coder-480b-a35b-instruct"}, {"id": "meta/llama-3.2-1b-instruct"}]},
        }
        srv2.catalogs = srv.catalogs  # type: ignore[attr-defined]
        hskills = {"qwen/qwen3-coder-480b-a35b-instruct": {"tools", "trace", "format", "argdict"},
                   "meta/llama-3.2-1b-instruct": {"tools"}}
        for s in (srv, srv2):
            s.skills, s.auth_seen, s.chat_calls = hskills, set(), 0  # type: ignore[attr-defined]
            threading.Thread(target=s.serve_forever, daemon=True).start()
        os.environ["OPENROUTER_API_KEY"], os.environ["NVIDIA_API_KEY"] = "key-or", "key-nv"
        hcfg = deep_merge(DEFAULTS, {"providers": {
            "openrouter": {"base_url": f"http://127.0.0.1:{port}/or/api/v1", "rpm": 60000},
            "nvidia": {"base_url": f"http://127.0.0.1:{port}/nv/v1", "rpm": 60000,
                       "litellm_api_base": "https://example.invalid/v1"},
            "mistral": {"enabled": False}, "google": {"enabled": False}},
            "probe": {"pause_between_models": 0, "budget": {"default": 500, "openrouter": 500}, "max_candidates": 50}})
        try:
            sp = f"{tmp}/check-state.json"
            rc, out = quiet(check, hcfg, IO(), sp)
            check_(rc == 0 and "[OK]" in out and "openrouter" in out and "nvidia" in out, "--check reports both services as ready")
            check_("gpt-5-mini" not in out, "--check does not list paid models")
            check_(load_state(sp)["services"]["nvidia"]["status"] == "ok", "--check saves each service's status")
            h = ns("http")
            rc, _ = quiet(run, hcfg, IO(), h)
            hs = load_state(h.state)
            check_(rc == 10 and srv.auth_seen == {"Bearer key-or", "Bearer key-nv"},  # type: ignore[attr-defined]
                   "real requests carry the right key for each service")
            check_(hs["probes"].get("nvidia:qwen/qwen3-coder-480b-a35b-instruct", {}).get("tools") == 1,
                   "a model that sends tool arguments as an object (not text) still passes the tool test")
            conf = yaml.safe_load(open(h.out, encoding="utf-8")) if yaml else json.load(open(h.out, encoding="utf-8"))
            nvd = [d for d in conf["model_list"] if d["litellm_params"]["model"].startswith("nvidia_nim/")]
            check_(bool(nvd) and all(d["litellm_params"].get("api_base") == "https://example.invalid/v1" for d in nvd),
                   "a service with its own address gets api_base in the router list")
            calls = srv.chat_calls  # type: ignore[attr-defined]
            rc, _ = quiet(run, hcfg, IO(), h)
            check_(rc == 0 and srv.chat_calls == calls, "second real run: nothing changed, zero new requests")  # type: ignore[attr-defined]

            srv.catalogs["/or/api/v1/models"]["data"].append(_or("acme/forbidden:free", 262144, age=1, now=time.time()))  # type: ignore[attr-defined]
            srv.skills["acme/forbidden:free"] = {"403"}  # type: ignore[attr-defined]
            quiet(run, hcfg, IO(), h)
            left = load_state(h.state)["dead"].get("openrouter:acme/forbidden:free", 0) - time.time()
            check_(0 < left <= 1.01 * DAY, "a '403 forbidden' model is set aside for about a day, not a week")

            srv.catalogs["/or/api/v1/models"]["data"].append(_or("acme/garbage:free", 262144, age=1, now=time.time()))  # type: ignore[attr-defined]
            srv.skills["acme/garbage:free"] = {"garbage"}  # type: ignore[attr-defined]
            _, out = quiet(run, hcfg, IO(), h)
            check_("openrouter:acme/garbage:free" not in load_state(h.state)["dead"] and "paused" in out,
                   "an unreadable reply (maintenance page) pauses the service instead of marking the model unusable")

            redir = deep_merge(hcfg, {"providers": {"openrouter": {"base_url": f"http://127.0.0.1:{port}/redir/api/v1"}}})
            st, msg, _, _ = test_service(redir, IO(), "openrouter", redir["providers"]["openrouter"], "key-or", time.time())
            check_(st == "offline", "a redirect to another site is refused, so a key never leaves for another host")

            print("== keys: test, save, replace, remove")
            kp, sp2 = f"{tmp}/keys.env", f"{tmp}/ks.json"
            open(kp, "w", encoding="utf-8").write("OPENROUTER_API_KEY=old-or-key\r\nNVIDIA_API_KEY='old nv key'\r\nTAVILY_API_KEY=tvly-1\r\n")
            check_(read_keys(kp)["NVIDIA_API_KEY"] == "old nv key" and read_keys(kp)["OPENROUTER_API_KEY"] == "old-or-key",
                   "a keys file with quotes and Windows line endings is read correctly")
            saved, st, msg = set_key(hcfg, IO(), "nvidia", "  badkey-123 \n", kp, sp2)
            check_(not saved and st == "refused" and read_keys(kp)["NVIDIA_API_KEY"] == "old nv key",
                   "a refused new key is NOT saved: the old key stays")
            saved, st, msg = set_key(hcfg, IO(), "nvidia", " good-nv-key \n", kp, sp2)
            keys_now = read_keys(kp)
            check_(saved and st == "ok" and keys_now["NVIDIA_API_KEY"] == "good-nv-key", "a working new key is saved (spaces and newlines stripped)")
            check_(read_keys(kp + ".bak")["NVIDIA_API_KEY"] == "old nv key", "the previous keys file is kept as keys.env.bak")
            check_(keys_now["TAVILY_API_KEY"] == "tvly-1" and keys_now["OPENROUTER_API_KEY"] == "old-or-key", "other keys in the file are untouched")
            check_(oct(os.stat(kp).st_mode & 0o777) == "0o600", "the keys file is readable only by you")
            check_(load_state(sp2)["services"]["nvidia"]["status"] == "ok" and "nvidia" not in load_state(sp2)["bad_keys"],
                   "the saved status is updated and any old 'refused' flag is cleared")
            ok, _msg = remove_key(hcfg, "nvidia", kp, sp2, time.time())
            check_(ok and read_keys(kp)["NVIDIA_API_KEY"] == "" and load_state(sp2)["services"]["nvidia"]["status"] == "skip",
                   "removing a key leaves it blank and shows [skip]")
            tbl = {r["service"]: r for r in keys_table(hcfg, kp, sp2)}
            check_(tbl["nvidia"]["status"] == "skip" and tbl["openrouter"]["saved"] and "old-or-key" not in json.dumps(tbl),
                   "the keys table never shows a full key")
            check_(ensure_master(hcfg, kp) and read_keys(kp)["LITELLM_MASTER_KEY"].startswith("sk-") and not ensure_master(hcfg, kp),
                   "a router password is created once and then kept")
        finally:
            for s in (srv, srv2):
                s.shutdown()
                s.server_close()

        print("== router list is valid")
        conf = yaml.safe_load(open(a.out, encoding="utf-8")) if yaml else json.load(open(a.out, encoding="utf-8"))
        check_({d["model_name"] for d in conf["model_list"]} == set(cfg["roles"]), "all three role names are present")
        check_(all(isinstance(f, dict) and len(f) == 1 for f in conf["router_settings"]["fallbacks"]),
               "each backup rule is its own entry (LiteLLM reads only the first key of each)")
        try:
            from litellm import Router  # type: ignore
            from litellm.router_utils.fallback_event_handlers import get_fallback_model_group  # type: ignore
            rs = conf["router_settings"]
            r = Router(model_list=conf["model_list"], routing_strategy=rs["routing_strategy"], num_retries=rs["num_retries"],
                       allowed_fails=rs["allowed_fails"], cooldown_time=rs["cooldown_time"], fallbacks=rs["fallbacks"])
            for role in cfg["roles"]:
                orders = {r.get_available_deployment(model=role)["litellm_params"]["order"] for _ in range(8)}
                check_(orders == {1}, f"LiteLLM sends '{role}' to its first choice first")
                check_(get_fallback_model_group(rs["fallbacks"], role)[0] == cfg["fallbacks"].get(role),
                       f"backup for '{role}' resolves ({cfg['fallbacks'].get(role) or 'none, by design'})")
        except ImportError:
            print("  skip LiteLLM checks (litellm is not installed in this Python)")
        print("\nselftest passed")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(prog="model_scout.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="test this script (no keys, no internet)")
    ap.add_argument("--check", action="store_true", help="test your keys and show the free models found")
    ap.add_argument("--probe", action="store_true", help="find, quick-test and rank models, write the router list")
    ap.add_argument("--use-saved", action="store_true", help="rebuild the router list from saved results (no new tests)")
    ap.add_argument("--dry-run", action="store_true", help="show what would change; write nothing, spend nothing")
    ap.add_argument("--print-defaults", action="store_true", help="print all settings")
    ap.add_argument("--keys-table", action="store_true", help="show saved keys (masked) and the last test result")
    ap.add_argument("--set-key", metavar="NAME", help="test the key in SCOUT_NEW_KEY and save it if it works")
    ap.add_argument("--remove-key", metavar="NAME", help="remove a saved key")
    ap.add_argument("--test-key", metavar="NAME", help="test the key in SCOUT_NEW_KEY (or the saved one), save nothing")
    ap.add_argument("--ensure-master", action="store_true", help="create the router password if there is none")
    ap.add_argument("--force", action="store_true", help="with --set-key: save even if the key could not be verified")
    ap.add_argument("--keys-file", default=KEYS_DEFAULT)
    ap.add_argument("--config", help="settings file (YAML) that overrides the defaults")
    ap.add_argument("--out", default="~/.litellm/config.yaml", help="router list to write")
    ap.add_argument("--state", default=os.path.join(HERE, "scout_state.json"))
    ap.add_argument("--report", default=os.path.join(HERE, "scout_report.md"))
    ap.add_argument("--on-change", help="shell command to run when the list changed (e.g. restart the router)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.print_defaults:
        print(dump(DEFAULTS) if yaml else json.dumps(DEFAULTS, indent=2))
        return 0
    actions = (args.check, args.probe, args.use_saved, args.dry_run, args.keys_table, args.set_key, args.remove_key,
               args.test_key, args.ensure_master)
    if not any(actions):
        ap.print_help()
        return 0
    try:
        cfg = load_config(args.config)
    except (OSError, ValueError) as e:
        print(f"Could not read the settings file {args.config}: {e}")
        return 1
    args.out, args.keys_file = os.path.expanduser(args.out), os.path.expanduser(args.keys_file)
    args.state, args.report = os.path.expanduser(args.state), os.path.expanduser(args.report)
    if args.ensure_master:
        print("created" if ensure_master(cfg, args.keys_file) else "exists")
        return 0
    if args.keys_table:
        for r in keys_table(cfg, args.keys_file, args.state):
            print(f"{r['service']}\t{r['status']}\t{r['masked']}\t{r['msg']}")
        return 0
    if args.set_key or args.test_key:
        service = args.set_key or args.test_key
        newkey = os.environ.get("SCOUT_NEW_KEY", "")
        io = IO()
        if args.test_key:
            p = cfg["providers"].get(service)
            if not p:
                print(f"unknown\tunknown service '{service}'")
                return 1
            key = normalize_key(newkey) or read_keys(args.keys_file).get(p["key_env"], "")
            status, msg, _, _ = test_service(cfg, io, service, p, key, io.now()) if key else ("skip", "no key", [], 0)
            print(f"{status}\t{msg}")
            return {"ok": 0, "warn": 0, "refused": 2, "offline": 3, "limit": 4, "blocked": 4}.get(status, 1)
        saved, status, msg = set_key(cfg, io, service, newkey, args.keys_file, args.state, args.force)
        print(f"{status}\t{'saved' if saved else 'not-saved'}\t{msg}")
        return 0 if saved else {"refused": 2, "offline": 3}.get(status, 1)
    if args.remove_key:
        ok, msg = remove_key(cfg, args.remove_key, args.keys_file, args.state, time.time())
        print(msg)
        return 0 if ok else 1
    if args.check:
        return check(cfg, IO(), args.state)
    return run(cfg, IO(), args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
