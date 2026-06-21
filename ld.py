#!/usr/bin/env python3
"""
DailyLifeOS · `ld` — the command-line shell over the vault.

The 90% software, exposed as a tool you can drive today with zero AI:
  ld ask "when's my next podiatrist appointment?"
  ld ask "find my insurance card"
  ld ask "what was my last A1C?"
  ld ask "how many test strips do I have left?"
  ld ask "what do I need to refill?"
  ld seed            # load synthetic demo data (no real PHI)
  ld status          # record counts
  ld receipts        # verify the PHI-blind receipt chain
  ld add <type> k=v ...

Later, the on-box model (Layer 3) becomes the friendly natural-language front end that calls
the very same query functions. The answers never change — that's the point.
"""
import sys
from core.vault import Vault, TABLES
from core import query, receipts


def _fmt(intent, r):
    if not r.get("found"):
        return r.get("message", "Nothing found.")
    if intent == "next_appointment":
        when = r["when"].replace("T", " ").replace("Z", "")
        d = r["in_days"]
        rel = "today" if d == 0 else ("tomorrow" if d == 1 else f"in {d} days")
        return f"📅 {r['specialty']} with {r['provider']} — {when} ({rel}) · {r['location']}"
    if intent == "find_document":
        more = f"  (+{r['count']-1} more on file)" if r.get("count", 1) > 1 else ""
        return f"📄 {r['title']} (issuer: {r['issuer']}) → {r['file_path']}{more}"
    if intent == "last_lab":
        t = r.get("trend_vs_prev")
        arrow = "" if t is None else (f"  ({'↓' if t < 0 else '↑'}{abs(t)} vs prior)" if t else "  (flat vs prior)")
        return f"🩸 Last {r['test']}: {r['value']}{r['unit']} on {r['when'][:10]}{arrow}"
    if intent == "supply_remaining":
        low = "  ⚠️ running low" if r.get("low") else ""
        dl = f" (~{r['days_left']} days)" if r.get("days_left") is not None else ""
        return f"📦 {r['name']}: {int(r['count'])} {r['unit']}{dl}{low}"
    if intent == "refill_due":
        if not r["due"]:
            return "✅ Nothing due for refill."
        return "🔔 Due for refill:\n" + "\n".join(
            f"   · {d['name']} — ~{d['days_left']} days left ({d['kind']})" for d in r["due"])
    return str(r)


def main(argv):
    if not argv:
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    v = Vault()
    if cmd == "ask":
        if not rest:
            print("usage: ld ask \"<question>\"")
            return
        intent, r = query.ask(v, " ".join(rest))
        print(_fmt(intent, r))
    elif cmd == "seed":
        import seed_demo
        seed_demo.seed(v)
        print("✅ seeded synthetic demo data (no real PHI).")
    elif cmd == "status":
        print(f"vault: {v.db_path}")
        for t in TABLES:
            print(f"  {t}: {v.count(t)}")
    elif cmd == "board":
        from core import board
        out = rest[0] if rest else "lifeboard.html"
        name = rest[1] if len(rest) > 1 else "Don"
        html = board.generate(v, name)
        with open(out, "w") as f:
            f.write(html)
        print(f"🐝 LifeBoard written → {out}  ({len(html)} bytes, rendered from the vault)")
    elif cmd == "receipts":
        ok, n = receipts.verify()
        print(f"receipt chain: {'OK ✅' if ok else 'BROKEN ❌'} · {n} PHI-blind receipts")
    elif cmd == "add":
        if len(rest) < 2:
            print("usage: ld add <type> key=value ...")
            return
        table = rest[0]
        fields = {}
        for kv in rest[1:]:
            k, _, val = kv.partition("=")
            try:
                val = float(val) if val.replace(".", "", 1).isdigit() else val
            except Exception:
                pass
            fields[k] = val
        rid = v.add(table, **fields)
        print(f"✅ added {table} #{rid}")
    else:
        print(__doc__)
    v.close()


if __name__ == "__main__":
    main(sys.argv[1:])
