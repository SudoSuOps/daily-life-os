"""
DailyLifeOS · the LifeBoard — the screen you wake up to.

A self-contained HTML dashboard RENDERED FROM THE VAULT. Nothing here is a mockup: every card is
the deterministic data (Layer 1+2) made visual. This is the 90% software you can see — the model
never touches it. Generated on the box, served on the box; raw data never leaves.
"""
import datetime as dt
from . import query, receipts

HONEY = "#F2B441"; HONEY6 = "#D99A2B"; GREEN = "#2FB67A"; RED = "#E2524F"
INK = "#0B0F14"; INK7 = "#121922"; LINE = "#1F2A36"; PAPER = "#FBF7EF"; COCOA = "#2B2118"; MUT = "#9fb1c2"


def _now():
    return dt.datetime.utcnow().replace(microsecond=0)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _spark(vals, w=120, h=34):
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = " ".join(f"{int(i*(w/(len(vals)-1)))},{int(h-(v-lo)/rng*(h-6)-3)}" for i, v in enumerate(vals))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline fill="none" stroke="{HONEY}" stroke-width="2.5" points="{pts}"/></svg>')


def _card(title, body, accent=LINE):
    return (f'<div class="card" style="border-top:3px solid {accent}">'
            f'<h3>{title}</h3>{body}</div>')


def generate(v, name="Don"):
    now = _now()
    hour = now.hour
    greet = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")
    today = now.strftime("%A, %B %-d")

    # appointments
    appts = sorted(
        [(r, dt.datetime.fromisoformat(r["when_ts"].replace("Z", ""))) for r in v.all("appointment")
         if r.get("when_ts")], key=lambda x: x[1])
    upcoming = [(r, w) for r, w in appts if w >= now][:3]
    appt_rows = "".join(
        f'<div class="row"><span><b>{_esc(r["specialty"])}</b> · {_esc(r["provider"])}</span>'
        f'<span class="when">{w.strftime("%b %-d")} · {("today" if (w-now).days==0 else "tomorrow" if (w-now).days==1 else f"in {(w-now).days}d")}</span></div>'
        for r, w in upcoming) or '<p class="empty">No upcoming appointments.</p>'

    # A1C
    labs = sorted([r for r in v.all("lab_result") if r["test"].upper() == "A1C"],
                  key=lambda r: r["when_ts"])
    if labs:
        last = labs[-1]
        trend = round(last["value"] - labs[-2]["value"], 1) if len(labs) >= 2 else None
        arrow = "" if trend is None else (f'<span style="color:{GREEN}">↓{abs(trend)}</span>' if trend < 0
                                          else f'<span style="color:{RED}">↑{trend}</span>' if trend > 0 else "→")
        a1c_body = (f'<div class="big">{last["value"]}<small>%</small> {arrow}</div>'
                    f'{_spark([l["value"] for l in labs])}'
                    f'<p class="sub">last drawn {last["when_ts"][:10]}</p>')
    else:
        a1c_body = '<p class="empty">No A1C on file.</p>'

    # supplies
    sup_rows = ""
    for r in v.all("supply_item"):
        per_day = r.get("per_day") or 0
        days = r["count"] / per_day if per_day else None
        low = days is not None and r.get("threshold") and days <= r["threshold"]
        pct = min(100, int((days or 0) / 30 * 100)) if days else 0
        bar = f'<div class="bar"><i style="width:{pct}%;background:{RED if low else GREEN}"></i></div>'
        warn = ' <span class="warn">⚠️ low</span>' if low else ""
        sup_rows += (f'<div class="row"><span>{_esc(r["name"])}{warn}</span>'
                     f'<span class="when">{int(r["count"])} · ~{round(days,1) if days else "–"}d</span></div>{bar}')

    # refills
    rd = query.refill_due(v)
    refill_body = ("".join(f'<div class="row"><span>🔔 {_esc(d["name"])}</span>'
                           f'<span class="when">~{d["days_left"]}d left</span></div>' for d in rd["due"])
                   or f'<p class="empty" style="color:{GREEN}">✓ Nothing due.</p>')

    # meds (today's nudges)
    med_rows = "".join(
        f'<div class="row"><span>💊 {_esc(r["name"])}</span><span class="when">{_esc(r["schedule"])}</span></div>'
        for r in v.all("medication")) or '<p class="empty">No medications.</p>'

    # documents
    docs = v.all("document")
    doc_rows = "".join(f'<div class="row"><span>📄 {_esc(r["title"])}</span>'
                       f'<span class="when">{_esc(r["doc_type"])}</span></div>' for r in docs[:4]) \
        or '<p class="empty">No documents.</p>'

    # emergency contact
    emerg = [r for r in v.all("contact") if r.get("is_emergency")]
    emerg_body = "".join(f'<div class="row"><span>🆘 {_esc(r["name"])}</span>'
                         f'<span class="when">{_esc(r["phone"])}</span></div>' for r in emerg) \
        or '<p class="empty">No emergency contact set.</p>'

    # skills (the apps on the OS) — Layer 3, human-in-the-loop
    from . import skills
    skill_rows = "".join(
        f'<div class="row"><span>🐝 {_esc(s["name"])}</span>'
        f'<span class="when">{_esc(s["status"].lower())}</span></div>' for s in skills.list_skills()) \
        or '<p class="empty">No skills installed.</p>'

    # food — today's meals + carbs (the diet/menu skill writes here)
    meals = sorted(v.all("meal"), key=lambda r: r.get("when_ts") or "")
    meal_rows = "".join(
        f'<div class="row"><span>{"✓" if r.get("logged") else "○"} <b>{_esc(r["slot"])}</b> · {_esc(r["name"])}</span>'
        f'<span class="when">{int(r["carbs_g"])}g carbs</span></div>' for r in meals) \
        or '<p class="empty">No meals planned.</p>'
    carbs = sum(int(r.get("carbs_g") or 0) for r in meals)
    if meals:
        meal_rows += f'<div class="row"><span>🍽️ Carbs today</span><span class="when">{carbs}g</span></div>'

    # fitness — today's movement (the fitness/exercise skill writes here)
    acts = v.all("activity")
    act_rows = "".join(
        f'<div class="row"><span>🏃 {_esc(r["name"])}</span>'
        f'<span class="when">{int(r.get("done_min") or 0)}/{int(r.get("target_min") or 0)} min</span></div>'
        for r in acts) or '<p class="empty">No activity logged.</p>'
    steps = sum(int(r.get("steps") or 0) for r in acts)
    if steps:
        act_rows += f'<div class="row"><span>👟 Steps today</span><span class="when">{steps:,}</span></div>'

    # notifications — recent + scheduled nudges (delivered to phone & watch)
    notes = sorted(v.all("notification"), key=lambda r: r.get("when_ts") or "")
    note_rows = "".join(
        f'<div class="row"><span>{"🔔" if r.get("status") == "scheduled" else "✓"} {_esc(r["text"])}</span>'
        f'<span class="when">{_esc(r.get("channel") or "")}</span></div>' for r in notes[:5]) \
        or '<p class="empty">No notifications.</p>'

    # synced devices — the phone + watch the nudges land on (generic only; no PHI leaves)
    devs = v.all("device")
    kind_icon = {"phone": "📱", "watch": "⌚", "tablet": "📲"}
    dev_rows = "".join(
        f'<div class="row"><span>{kind_icon.get(r.get("kind"), "📟")} {_esc(r["name"])}</span>'
        f'<span class="when">{_esc(r.get("last_sync") or "synced")}</span></div>' for r in devs) \
        or '<p class="empty">No devices paired.</p>'

    ok, nrec = receipts.verify()

    cards = "".join([
        _card("📅 Next appointments", appt_rows, HONEY),
        _card("💊 Today's medications", med_rows, GREEN),
        _card("🍎 Food today", meal_rows, GREEN),
        _card("🏃 Move today", act_rows, "#3D9BE9"),
        _card("🩸 A1C trend", a1c_body, HONEY),
        _card("🔔 Notifications", note_rows, HONEY6),
        _card("📱 Synced devices", dev_rows, GREEN),
        _card("📦 Supplies", sup_rows, GREEN),
        _card("🔁 Due for refill", refill_body, HONEY6),
        _card("📄 Documents", doc_rows, "#3D9BE9"),
        _card("🆘 Emergency", emerg_body, RED),
        _card("🧩 Your apps · draft &amp; approve", skill_rows, HONEY),
    ])

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LifeBoard · {_esc(name)} · DailyLifeOS</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:{INK};color:#E8EEF5;font:16px/1.5 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}}
.top{{padding:26px 24px 6px;max-width:1080px;margin:0 auto}}
.brand{{color:{HONEY};font-weight:800;letter-spacing:.3px;font-size:15px}}
h1{{margin:6px 0 2px;font-size:clamp(26px,5vw,40px);font-weight:800;letter-spacing:-.5px}}
h1 span{{color:{HONEY}}}
.date{{color:{MUT};margin:0 0 14px}}
.grid{{max-width:1080px;margin:0 auto;padding:8px 24px 30px;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
.card{{background:{INK7};border:1px solid {LINE};border-radius:16px;padding:18px 20px}}
.card h3{{margin:0 0 12px;font-size:16px;letter-spacing:-.2px}}
.row{{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:6px 0;font-size:15px}}
.row .when{{color:{MUT};font-size:13px;white-space:nowrap}}
.warn{{color:{RED};font-size:12px;font-weight:700}}
.big{{font-size:44px;font-weight:800;color:{HONEY};line-height:1}}
.big small{{font-size:18px;color:{MUT};font-weight:600}}
.sub{{color:{MUT};font-size:13px;margin:6px 0 0}}
.empty{{color:{MUT};font-size:14px;margin:4px 0}}
.bar{{height:6px;background:{INK};border-radius:6px;overflow:hidden;margin:2px 0 8px}}
.bar i{{display:block;height:100%}}
.foot{{max-width:1080px;margin:0 auto;padding:6px 24px 40px;color:{MUT};font-size:13px;text-align:center;line-height:1.6}}
.foot b{{color:{GREEN}}}
.lock{{display:inline-block;background:{INK7};border:1px solid {LINE};border-radius:999px;padding:6px 14px;margin:8px 0}}
</style></head><body>
<div class="top">
  <div class="brand">🐝 LifeBoard · DailyLifeOS</div>
  <h1>{greet}, <span>{_esc(name)}</span>.</h1>
  <p class="date">{today} · your life, organized.</p>
</div>
<div class="grid">{cards}</div>
<div class="foot">
  <div class="lock">🔒 Your records never left this box · {nrec} PHI-blind receipt{"s" if nrec != 1 else ""} · chain {"✓ verified" if ok else "✗ broken"}</div>
  <p>DailyLifeOS · powered by the LocalDiabetic vault · the model is one service, not the star.<br>
  © 2026 Swarm and Bee LLC · build@opendiabetic.com</p>
</div>
</body></html>"""
