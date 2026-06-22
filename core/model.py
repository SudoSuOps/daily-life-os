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
MODEL = os.environ.get("LD_MODEL", "diabetic-daily")   # DiabeticDaily-4B (edge) / -9B (home) in local ollama

FIREWALL = (
    "You run ON the user's own box as part of DailyLifeOS, the operating system for a person living with "
    "diabetes. Your job is to ORGANIZE their records and DRAFT documents from the facts they provide. "
    "Hard rules: you never diagnose, never interpret a glucose or lab reading, never start/stop/adjust any "
    "medication or insulin dose, never give medical advice. Everything you produce is a DRAFT the person "
    "reviews and approves before anything is sent or acted on. If something sounds like an emergency, tell "
    "them to call 911. Be warm, plain-spoken, and exact — use the facts given, never invent specifics."
)


def available(timeout=2):
    """Is a local model serving on this box?"""
    try:
        urllib.request.urlopen(_TAGS, timeout=timeout)
        return True
    except Exception:
        return False


def draft(system, prompt, timeout=60, num_predict=600):
    """Draft on-box via the local DiabeticDaily model (think-off). Returns text, or None if unavailable."""
    body = json.dumps({
        "model": MODEL, "think": False, "stream": False,
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
