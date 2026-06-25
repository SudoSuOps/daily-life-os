"""
DailyLifeOS · Layer 4 — the 10%: the on-box DiabeticDaily model client.

The cooked DiabeticDaily model runs LOCALLY (ollama on this box). Skills call it to draft artifacts
from the gathered on-box context.

THE FIREWALL — non-negotiable, enforced here in code:
  • the endpoint is 127.0.0.1 ONLY. There is no setting to point this at a remote host. PHI is drafted
    on the box and never leaves it. (The public ask.opendiabetic.com assistant is a SEPARATE, PHI-free
    surface — skills never call it.)
  • the model is told, every call, that it organizes and drafts but never diagnoses or changes treatment.
  • if no local model is available, draft() returns None and the skill falls back to its deterministic
    template — the 90% software keeps working without the 10%.
"""
import json, os, urllib.request

# on-box ONLY — host is hard-coded to loopback; only the model NAME is configurable.
_ENDPOINT = "http://127.0.0.1:11434/api/chat"
_TAGS = "http://127.0.0.1:11434/api/tags"
_FORCED = os.environ.get("LD_MODEL")                   # explicit override, e.g. LD_MODEL=diabetic-jr-9b
MODEL = _FORCED or "diabetic-daily"                    # default / back-compat
_resolved = None


def _installed_tags(timeout=2):
    """Model names installed in the LOCAL ollama, or None if ollama isn't reachable. (loopback only)"""
    try:
        o = json.loads(urllib.request.urlopen(_TAGS, timeout=timeout).read())
        return [m.get("name", "") for m in o.get("models", [])]
    except Exception:
        return None


def resolve_model(timeout=2):
    """Pick the on-box model NAME to use — loopback only, never a remote host.
    Order: an explicit LD_MODEL that's installed → any DiabeticDaily/diabetic model → the default.
    So whatever DiabeticDaily tag the user pulled (e.g. hf.co/SwarmandBee/DiabeticDaily-4B:Q4_K_M)
    just works with no configuration."""
    global _resolved
    if _resolved:
        return _resolved
    tags = _installed_tags(timeout)
    if not tags:
        return None
    if _FORCED:                                                       # honor an explicit, installed override
        for t in tags:
            if t == _FORCED or t.split(":")[0] == _FORCED:
                _resolved = t; return t
    for needle in ("diabeticdaily", "diabetic-daily", "diabetic"):    # auto-discover a diabetic model
        for t in tags:
            if needle in t.lower():
                _resolved = t; return t
    for t in tags:                                                    # last resort: the configured default
        if t == MODEL or t.split(":")[0] == MODEL:
            _resolved = t; return t
    return None

FIREWALL = (
    "You run ON the user's own box as part of DailyLifeOS, the operating system for a person living with "
    "diabetes. Your job is to ORGANIZE their records and DRAFT documents from the facts they provide. "
    "Hard rules: you never diagnose, never interpret a glucose or lab reading, never start/stop/adjust any "
    "medication or insulin dose, never give medical advice. Everything you produce is a DRAFT the person "
    "reviews and approves before anything is sent or acted on. If something sounds like an emergency, tell "
    "them to call 911. Be warm, plain-spoken, and exact — use the facts given, never invent specifics."
)


def available(timeout=2):
    """Is a usable on-box diabetic model serving (loopback)?"""
    return resolve_model(timeout) is not None


def draft(system, prompt, timeout=60, num_predict=600):
    """Draft on-box via the local DiabeticDaily model (think-off). Returns text, or None if unavailable."""
    body = json.dumps({
        "model": resolve_model() or MODEL, "think": False, "stream": False,
        "messages": [{"role": "system", "content": FIREWALL + "\n\n" + system},
                     {"role": "user", "content": prompt}],
        "options": {"temperature": 0.4, "num_predict": num_predict},
    }).encode()
    try:
        req = urllib.request.Request(_ENDPOINT, body, {"Content-Type": "application/json"})
        o = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        txt = (o.get("message") or {}).get("content", "").strip()
        # belt: strip any stray <think> the model emitted
        if txt.startswith("<think>") and "</think>" in txt:
            txt = txt.split("</think>", 1)[1].strip()
        return txt or None
    except Exception:
        return None
