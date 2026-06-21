"""
DailyLifeOS · the receipt log — PHI-blind, hash-chained.

Every query the system answers emits a receipt: WHAT kind of question was asked and WHEN,
never the answer's content. phi_touched is recorded but the PHI itself never enters a receipt,
so the chain can flow UP to the hive (or to an auditor) while the records stay home. Same
hash-chain discipline as DiabeticLedger: each receipt commits to the previous one.
"""
import os, json, hashlib, datetime as dt

DATA_DIR = os.environ.get("LD_DATA_DIR", os.path.expanduser("~/.localdiabetic"))
LOG_PATH = os.path.join(DATA_DIR, "receipts.jsonl")

# fields that may NEVER appear in a receipt (defense-in-depth against accidental PHI leak)
_BANNED = ("value", "provider", "name", "phone", "email", "location", "notes", "file_path", "title", "answer")


def _now():
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _last_hash():
    if not os.path.exists(LOG_PATH):
        return "0" * 64
    last = "0" * 64
    with open(LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)["receipt_hash"]
                except Exception:
                    pass
    return last


def emit(query_type, result_count, phi_touched=True, meta=None):
    """Append a PHI-blind receipt. meta must contain no PHI (checked)."""
    meta = meta or {}
    for k in meta:
        if k in _BANNED:
            raise ValueError(f"receipt meta field '{k}' could carry PHI — refused (firewall)")
    os.makedirs(DATA_DIR, exist_ok=True)
    body = {
        "ts": _now(),
        "query_type": query_type,
        "result_count": int(result_count),
        "phi_touched": bool(phi_touched),
        "diagnosis_given": False,
        "meta": meta,
        "prev": _last_hash(),
    }
    body["receipt_hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode()
    ).hexdigest()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(body) + "\n")
    return body["receipt_hash"]


def verify():
    """Re-walk the chain; return (ok, count)."""
    if not os.path.exists(LOG_PATH):
        return True, 0
    prev = "0" * 64
    n = 0
    with open(LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["prev"] != prev:
                return False, n
            h = r.pop("receipt_hash")
            if hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest() != h:
                return False, n
            prev = h
            n += 1
    return True, n


if __name__ == "__main__":
    ok, n = verify()
    print(f"receipt chain: {'OK' if ok else 'BROKEN'} · {n} receipts · {LOG_PATH}")
