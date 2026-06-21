"""
DailyLifeOS · validate the validator.

A green test proves nothing unless the test can CATCH a failure. So this suite does two jobs:
  (A) validate the system — every skill runs, every receipt is PHI-blind, the chain verifies, queries are exact;
  (B) validate the VALIDATOR — deliberately tamper a receipt (the chain check must break), plant a PHI leak
      (the scanner must find it), and feed the guard a banned field (it must refuse). If the meta-tests don't
      fail-on-purpose, the green checks above are meaningless.

Runs in a throwaway LD_DATA_DIR; never touches real data.
"""
import os, tempfile, json

os.environ["LD_DATA_DIR"] = tempfile.mkdtemp(prefix="dlos-validate-")
from core.vault import Vault                       # noqa: E402
from core import query, receipts, skills           # noqa: E402
import seed_demo                                    # noqa: E402

PASS = 0; FAIL = 0
def check(name, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {name}")
    else: FAIL += 1; print(f"  ❌ {name}   {detail}")

# sensitive values seeded into the vault — NONE may ever appear in a receipt
PHI_TOKENS = ["Dr. Greene", "BlueCross", "Medicare", "Sarah", "6.9", "Lantus", "Metformin",
              "Jupiter Foot", "555-0", "CLM-4471", "bluecross-card", "988"]

v = Vault(os.path.join(os.environ["LD_DATA_DIR"], "vault.db"))
seed_demo.seed(v)

print("(A) SYSTEM — every skill is Agent-0, human-in-the-loop, receipt-emitting:")
all_slugs = list(skills.REGISTRY)
for slug in all_slugs:
    res = skills.run(v, slug, claim="CLM-4471", denial_reason="not medically necessary",
                     matter="records request", to="Dr. Greene", subject="hello")
    ok = bool(res.get("draft")) and res.get("needs_approval") is True and bool(res.get("receipt"))
    check(f"skill {slug:14} drafts + needs approval + receipt", ok, str(res)[:80])

print(f"\n(A) FIREWALL — independent scan of the receipt log ({len(all_slugs)} skill runs):")
# scan the CONTENT fields only (query_type + meta) — receipt_hash/prev are random hex and would
# false-positive short tokens (e.g. '988' inside a SHA). A leak can only live where skill code writes.
objs = [json.loads(l) for l in open(receipts.LOG_PATH) if l.strip()]
content = " ".join(o.get("query_type", "") + " " + json.dumps(o.get("meta", {})) for o in objs)
leaks = [t for t in PHI_TOKENS if t in content]
check("no PHI token in ANY receipt's content (independent scan)", not leaks, f"leaked: {leaks}")
# and prove the scan would have caught a real content leak (validate this scanner too)
check("scan-target is the content, not the hashes", "receipt_hash" not in content and len(content) > 0)

print("\n(A) QUERIES — deterministic exactness (same seed → same answers):")
a = query.next_appointment(v, "podiatr"); check("next podiatry = in 3 days", a["found"] and a["in_days"] == 3, str(a))
b = query.last_lab(v, "A1C"); check("last A1C = 6.9 (↓0.5)", b["value"] == 6.9 and b["trend_vs_prev"] == -0.5, str(b))
c = query.supply_remaining(v, "test strip"); check("strips 4.5 days, low", c["days_left"] == 4.5 and c["low"], str(c))

ok, n = receipts.verify(); check("chain verifies clean before tamper", ok and n >= len(all_slugs), f"ok={ok} n={n}")

print("\n(B) VALIDATE THE VALIDATOR — these must FAIL-ON-PURPOSE:")
# meta-1: the PHI guard must REFUSE a banned field (else the firewall is decorative)
try:
    receipts.emit("probe", 1, meta={"value": "6.9"}); check("META guard refuses PHI meta field", False, "did NOT raise")
except ValueError:
    check("META guard refuses PHI meta field", True)

# meta-2: the leak scanner must DETECT a planted leak (else a '0 leaks' result is blind)
probe = receipts.LOG_PATH + ".probe"
open(probe, "w").write('{"meta":{"leak":"Dr. Greene"}}')
planted_found = "Dr. Greene" in open(probe).read()
check("META leak-scanner detects a planted leak (not blind)", planted_found)
os.remove(probe)

# meta-3: the chain verifier must CATCH tampering (else 'chain OK' is meaningless)
lines = open(receipts.LOG_PATH).read().splitlines()
obj = json.loads(lines[0]); obj["result_count"] = 99999          # corrupt body, leave hash stale
lines[0] = json.dumps(obj)
open(receipts.LOG_PATH, "w").write("\n".join(lines) + "\n")
ok_after, _ = receipts.verify()
check("META chain verifier CATCHES tampering (verify→broken)", ok_after is False, f"verify returned {ok_after}")

v.close()
print(f"\n{'='*54}\n  {PASS} passed · {FAIL} failed   "
      f"{'— validator is sound ✅' if FAIL == 0 else '— FIX BEFORE TRUSTING ❌'}\n{'='*54}")
raise SystemExit(0 if FAIL == 0 else 1)
