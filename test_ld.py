"""
DailyLifeOS · end-to-end proof — the disappearance-test five + the receipt chain.

Runs against a throwaway vault in a temp dir (LD_DATA_DIR), so it never touches real data.
Deterministic: same seed → same answers. No model involved.
"""
import os, tempfile, sys

# isolate to a temp data dir BEFORE importing the modules that read LD_DATA_DIR
_TMP = tempfile.mkdtemp(prefix="dlos-test-")
os.environ["LD_DATA_DIR"] = _TMP

from core.vault import Vault, DB_PATH  # noqa: E402
from core import query, receipts       # noqa: E402
import seed_demo                        # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


def run():
    v = Vault(os.path.join(_TMP, "vault.db"))
    seed_demo.seed(v)

    print("Disappearance-test queries:")
    # 1 — next podiatrist appointment
    intent, r = query.ask(v, "when's my next podiatrist appointment?")
    check("next podiatrist appointment", r["found"] and r["specialty"] == "Podiatry"
          and r["in_days"] == 3, str(r))

    # 2 — find insurance card
    intent, r = query.ask(v, "find my insurance card")
    check("find insurance card (BlueCross primary, +1 more)", r["found"]
          and "insurance" in r["title"].lower() and r["file_path"].endswith(".pdf")
          and r["count"] == 2, str(r))

    # 3 — last A1C + trend
    intent, r = query.ask(v, "what was my last A1C?")
    check("last A1C = 6.9 (down from 7.4)", r["found"] and r["value"] == 6.9
          and r["trend_vs_prev"] == -0.5, str(r))

    # 4 — test strips left + days-of-supply (18 strips / 4 per day = 4.5 days, low)
    intent, r = query.ask(v, "how many test strips do I have left?")
    check("test strips: 18 left, 4.5 days, LOW", r["found"] and r["count"] == 18
          and r["days_left"] == 4.5 and r["low"] is True, str(r))

    # 5 — refill due (insulin 12 days < 14 threshold; strips 4.5 < 7)
    intent, r = query.ask(v, "what do I need to refill?")
    names = {d["name"] for d in r["due"]}
    check("refill due includes insulin + strips", r["found"]
          and any("Insulin" in n for n in names) and "Test Strips" in names, str(r))

    print("Firewall / receipts:")
    ok, n = receipts.verify()
    check("receipt chain intact", ok and n >= 5, f"ok={ok} n={n}")

    # no PHI in receipts (scan the raw log for seeded PHI values)
    raw = open(os.path.join(_TMP, "receipts.jsonl")).read()
    leaks = [tok for tok in ["Dr. Greene", "BlueCross", "6.9", "555-0", "bluecross-card"] if tok in raw]
    check("receipts are PHI-blind (no answer content leaked)", not leaks, f"leaked: {leaks}")

    # banned-field guard actually refuses PHI in meta
    try:
        receipts.emit("test", 1, meta={"value": "6.9"})
        check("receipt refuses PHI meta field", False, "did not raise")
    except ValueError:
        check("receipt refuses PHI meta field", True)

    v.close()
    print(f"\n{'='*48}\n  {PASS} passed · {FAIL} failed\n{'='*48}")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
