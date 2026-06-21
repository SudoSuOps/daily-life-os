"""
DailyLifeOS · Layer 1 — deterministic retrieval (the disappearance-test queries).

These are the things you'd notice if they vanished tomorrow. Every answer is an exact lookup
or a piece of arithmetic — NO model, NO guessing. The model (Layer 3) will later sit on top as
a natural-language shell that routes to these; for now a deterministic keyword router proves the
whole loop with zero AI. Each call emits a PHI-blind receipt.
"""
import datetime as dt
from . import receipts
from .vault import Vault


def _now():
    return dt.datetime.utcnow().replace(microsecond=0)


def _parse(ts):
    if not ts:
        return None
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", ""))
    except Exception:
        return None


# ── the five disappearance-test queries ─────────────────────────────────────

def next_appointment(v, specialty=None):
    """'When is my next podiatrist appointment?'"""
    rows = v.all("appointment")
    now = _now()
    future = [(r, _parse(r["when_ts"])) for r in rows if _parse(r["when_ts"]) and _parse(r["when_ts"]) >= now]
    if specialty:
        future = [(r, w) for r, w in future if specialty.lower() in (r.get("specialty") or "").lower()
                  or specialty.lower() in (r.get("provider") or "").lower()]
    future.sort(key=lambda x: x[1])
    receipts.emit("next_appointment", len(future), meta={"specialty": (specialty or "any")})
    if not future:
        return {"found": False, "message": f"No upcoming {specialty or ''} appointment on file.".strip()}
    r, w = future[0]
    days = (w - now).days
    return {"found": True, "provider": r["provider"], "specialty": r["specialty"],
            "when": r["when_ts"], "in_days": days, "location": r["location"]}


def find_document(v, doc_type):
    """'Find my insurance card.'  Primary = first on file; report how many match."""
    rows = [r for r in v.all("document") if doc_type.lower() in (r.get("doc_type") or "").lower()
            or doc_type.lower() in (r.get("title") or "").lower()]
    receipts.emit("find_document", len(rows), meta={"doc_type": doc_type})
    if not rows:
        return {"found": False, "message": f"No '{doc_type}' document in the vault."}
    r = rows[0]
    return {"found": True, "title": r["title"], "issuer": r["issuer"], "file_path": r["file_path"],
            "count": len(rows), "others": [x["title"] for x in rows[1:]]}


def last_lab(v, test="A1C"):
    """'What was my last A1C?'"""
    rows = [r for r in v.all("lab_result") if test.lower() in (r.get("test") or "").lower()]
    rows.sort(key=lambda r: _parse(r["when_ts"]) or dt.datetime.min)
    receipts.emit("last_lab", len(rows), meta={"test": test})
    if not rows:
        return {"found": False, "message": f"No {test} result on file."}
    r = rows[-1]
    trend = None
    if len(rows) >= 2:
        prev = rows[-2]["value"]
        trend = round(r["value"] - prev, 2)
    return {"found": True, "test": r["test"], "value": r["value"], "unit": r["unit"],
            "when": r["when_ts"], "trend_vs_prev": trend}


def supply_remaining(v, name):
    """'How many test strips do I have left?'  (count + days-of-supply, re-derived)"""
    rows = [r for r in v.all("supply_item") if name.lower() in (r.get("name") or "").lower()]
    receipts.emit("supply_remaining", len(rows), meta={"item": name})
    if not rows:
        return {"found": False, "message": f"No supply '{name}' tracked."}
    r = rows[-1]
    per_day = r.get("per_day") or 0
    days_left = round(r["count"] / per_day, 1) if per_day else None
    return {"found": True, "name": r["name"], "count": r["count"], "unit": r["unit"],
            "days_left": days_left, "low": (days_left is not None and r.get("threshold") is not None
                                            and days_left <= r["threshold"])}


def refill_due(v):
    """'What do I need to refill?'  (meds + supplies below their threshold)"""
    due = []
    for r in v.all("medication"):
        per_day = r.get("per_day") or 0
        if per_day and r.get("supply_count") is not None:
            days_left = r["supply_count"] / per_day
            if r.get("refill_threshold_days") is not None and days_left <= r["refill_threshold_days"]:
                due.append({"name": r["name"], "days_left": round(days_left, 1), "kind": "medication"})
    for r in v.all("supply_item"):
        per_day = r.get("per_day") or 0
        if per_day and r.get("count") is not None:
            days_left = r["count"] / per_day
            if r.get("threshold") is not None and days_left <= r["threshold"]:
                due.append({"name": r["name"], "days_left": round(days_left, 1), "kind": "supply"})
    due.sort(key=lambda x: x["days_left"])
    receipts.emit("refill_due", len(due))
    return {"found": bool(due), "due": due}


# ── deterministic keyword intent router (the 90% — no model) ─────────────────

def ask(v, question):
    """Route a natural-ish question to the right deterministic query. Pure keyword rules —
    the Layer-3 model will replace THIS function later, but the answers below never change."""
    q = question.lower()
    SPECIALTIES = ["podiatr", "endocrin", "ophthalm", "primary", "dentist", "nephrolog", "cardiolog"]
    if "appoint" in q or "appt" in q or "see the" in q or "next visit" in q:
        spec = next((s for s in SPECIALTIES if s in q), None)
        return ("next_appointment", next_appointment(v, spec))
    if "insurance" in q or "card" in q or "find my" in q or "document" in q or "policy" in q:
        dtype = "insurance" if ("insurance" in q or "card" in q or "policy" in q) else q.split("find my")[-1].strip()
        return ("find_document", find_document(v, dtype or "insurance"))
    if "a1c" in q or "hba1c" in q or "last lab" in q or "blood sugar result" in q:
        return ("last_lab", last_lab(v, "A1C"))
    if "strip" in q or "how many" in q or "supply" in q or "left" in q or "supplies" in q:
        item = "test strip" if "strip" in q else ("insulin" if "insulin" in q else "test strip")
        return ("supply_remaining", supply_remaining(v, item))
    if "refill" in q or "reorder" in q or "running low" in q or "need to order" in q:
        return ("refill_due", refill_due(v))
    receipts.emit("unrouted", 0, phi_touched=False, meta={})
    return ("unrouted", {"found": False, "message": "I can answer: next appointment, find a document, "
                         "last A1C, supplies left, or what's due for refill."})
