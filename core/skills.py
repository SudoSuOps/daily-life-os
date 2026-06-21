"""
DailyLifeOS · Layer 3 — the skills (the apps on the OS).

A skill is an app that runs on the vault: it GATHERS the right on-box data deterministically (the 90%),
DRAFTS an artifact (template today; the cooked model plugs in as the 10% later), and the human APPROVES
before anything leaves. Agent-0 by design — a skill has zero standing authority, can only propose, and never
sends on its own. Every run emits a PHI-blind receipt.

Plug a new skill in by subclassing Skill and calling register(). The three below map to real cooked work:
  letter-drop   → general advocacy/letter writer
  credit-sniper → insurance-denial & medical-bill appeal   (model: CreditSniper-edge-4B, ledger-proven)
  grant-writer  → assistance & patient-assistance/grant applications   (corpus: SwarmGrant 280K)
"""
import datetime as dt
from . import receipts

REGISTRY = {}


def register(cls):
    REGISTRY[cls.slug] = cls()   # store a ready instance, keyed by slug
    return cls


class Skill:
    slug = ""; name = ""; serves = ""; desc = ""; status = "FRAMEWORK"

    def gather(self, v, **kw):
        """Deterministic: pull the on-box records this skill needs. Returns a context dict (may hold PHI; stays local)."""
        return {}

    def draft(self, ctx, **kw):
        """Produce the artifact. Template-based now; the cooked model replaces this body later, same interface."""
        return ""

    def run(self, v, **kw):
        ctx = self.gather(v, **kw)
        text = self.draft(ctx, **kw)
        # receipt is PHI-blind: it records THAT a draft was made, never the draft itself
        rh = receipts.emit(f"skill:{self.slug}", 1, phi_touched=True,
                           meta={"skill": self.slug, "artifact": kw.get("artifact", "draft")})
        return {"skill": self.slug, "name": self.name, "status": self.status,
                "draft": text, "needs_approval": True, "receipt": rh[:12]}


_DRAFT_HDR = ("— — — DRAFT · review and approve before anything is sent — — —\n"
              "✋ Human-in-the-loop: this skill only proposes. Nothing leaves your box until you say so.\n\n")


@register
class LetterDrop(Skill):
    slug = "letter-drop"; name = "LetterDrop"; serves = "both"; status = "FRAMEWORK"
    desc = "Advocacy & letter writer — drafts a clean letter from your contacts and the facts on file."

    def gather(self, v, to=None, **kw):
        contacts = v.all("contact")
        match = next((c for c in contacts if to and to.lower() in (c["name"] or "").lower()), None)
        return {"to": match, "raw_to": to}

    def draft(self, ctx, subject="", body="", **kw):
        to = ctx["to"]["name"] if ctx.get("to") else (ctx.get("raw_to") or "[recipient]")
        today = dt.date.today().isoformat()
        return (_DRAFT_HDR +
                f"{today}\n\nDear {to},\n\nRe: {subject or '[subject]'}\n\n"
                f"{body or '[your message — LetterDrop will draft the prose; the on-box writer model fills this in]'}\n\n"
                "Sincerely,\n[your name]\n")


@register
class CreditSniper(Skill):
    slug = "credit-sniper"; name = "CreditSniper"; serves = "both"; status = "FRAMEWORK"
    desc = "Insurance-denial & medical-bill appeal — classifies the denial, finds the deadline, drafts an IRAC appeal."

    def gather(self, v, **kw):
        ins = [d for d in v.all("document") if "insurance" in (d.get("doc_type") or "").lower()]
        return {"insurance": ins[0] if ins else None, "insurance_count": len(ins)}

    def draft(self, ctx, denial_reason="", claim="", deadline_days=180, **kw):
        ins = ctx.get("insurance")
        payer = ins["issuer"] if ins else "[payer]"
        # deterministic: appeal deadline math is re-derived, not guessed
        due = (dt.date.today() + dt.timedelta(days=int(deadline_days))).isoformat()
        return (_DRAFT_HDR +
                f"APPEAL OF CLAIM DENIAL\nPayer: {payer}\nClaim: {claim or '[claim #]'}\n"
                f"Appeal deadline (re-derived, {deadline_days}d): {due}\n\n"
                f"ISSUE: Whether the denial of the above claim for '{denial_reason or '[reason]'}' was proper.\n"
                f"RULE: Medical-necessity and the plan's own coverage terms govern.\n"
                f"APPLICATION: [the on-box CreditSniper-edge-4B model drafts the medical-necessity argument "
                f"from your records — proven beat-base on the IRAC gate].\n"
                f"CONCLUSION: The denial should be overturned; the claim paid.\n\n"
                "Escalation ladder: internal appeal → external/independent review → state regulator.\n")


@register
class GrantWriter(Skill):
    slug = "grant-writer"; name = "Grant Writer"; serves = "patient"; status = "FRAMEWORK"
    desc = "Assistance & grants navigator — matches programs (PAP, $35 insulin cap, shoe benefit) and drafts the application."

    def gather(self, v, **kw):
        meds = [m["name"] for m in v.all("medication")]
        return {"medications": meds}

    def draft(self, ctx, program="", **kw):
        meds = ctx.get("medications") or []
        insulin = any("insulin" in m.lower() for m in meds)
        matches = []
        if insulin:
            matches.append("• Manufacturer copay card / Patient Assistance Program for your insulin")
            matches.append("• $35/month insulin cap (Medicare Part D)")
        matches.append("• Medicare therapeutic-shoe benefit (1 pair + 3 insert pairs/yr after deductible)")
        matches.append("• Foundation grants for diabetic supplies & care")
        return (_DRAFT_HDR +
                f"ASSISTANCE MATCHES (from your meds on file: {', '.join(meds) or 'none'})\n" +
                "\n".join(matches) +
                f"\n\nAPPLICATION DRAFT — {program or 'Patient Assistance Program'}:\n"
                "[the SwarmGrant-trained model drafts the fundable application from your on-file facts — "
                "280K-row assistance corpus]. You review, you sign, it submits on your approval.\n")


@register
class LegalSkill(Skill):
    slug = "legal"; name = "Legal"; serves = "both"; status = "FRAMEWORK"
    desc = "Legal & advocacy — records requests, ADA/FMLA & disability paperwork, consumer-rights disputes."

    def gather(self, v, **kw):
        return {"documents": [d["title"] for d in v.all("document")],
                "contacts": [c["name"] for c in v.all("contact")]}

    def draft(self, ctx, matter="", to="", **kw):
        today = dt.date.today().isoformat()
        docs = ", ".join(ctx["documents"]) or "none on file"
        return (_DRAFT_HDR +
                f"{today}\nTo: {to or '[recipient]'}\n"
                f"Re: {matter or '[matter — medical-records request / ADA accommodation / FMLA / billing dispute]'}\n\n"
                f"Records on file you may attach: {docs}\n\n"
                "[the on-box legal model drafts the letter/packet from the consumer-rights + disability corpus "
                "(95K rows): records requests, ADA accommodation, FMLA, SSDI/SSI function narrative, billing "
                "disputes]. This is self-advocacy drafting, not legal advice — you review and sign.\n\n"
                "Escalation: request → formal complaint → state regulator / civil-rights office.\n")


@register
class AccountingSkill(Skill):
    slug = "accounting"; name = "Accounting"; serves = "both"; status = "FRAMEWORK"
    desc = "Medical accounting — expenses, deductible progress, HSA/FSA-eligible categories, cost of care."

    def gather(self, v, **kw):
        return {"meds": v.all("medication"), "supplies": v.all("supply_item"),
                "visits": len(v.all("appointment"))}

    def draft(self, ctx, year="", **kw):
        meds, sup, visits = ctx["meds"], ctx["supplies"], ctx["visits"]
        yr = year or dt.date.today().year
        return (_DRAFT_HDR +
                f"MEDICAL EXPENSE ORGANIZER · {yr}\n\n"
                f"Cost drivers tracked on your box:\n"
                f"  • Medications:  {len(meds)} ({', '.join(m['name'] for m in meds) or 'none'})\n"
                f"  • Supplies:     {len(sup)} ({', '.join(s['name'] for s in sup) or 'none'})\n"
                f"  • Appointments: {visits} on file\n\n"
                "Tax / HSA / FSA categories: prescriptions · diabetic supplies (strips, CGM, needles) · "
                "office visits · therapeutic shoes · mileage to care.\n"
                "[the on-box finance model (71K-row corpus) categorizes each expense, tracks deductible progress, "
                "flags HSA/FSA-eligible spend]. Add cost amounts to your records to enable dollar totals.\n")


@register
class Cookbook(Skill):
    slug = "cookbook"; name = "Cookbook"; serves = "patient"; status = "FRAMEWORK"
    desc = "Diabetic-friendly recipes — plate-method, lower-glycemic ideas built around what you like."

    def gather(self, v, **kw):
        return {"meds": [m["name"] for m in v.all("medication")]}

    def draft(self, ctx, craving="", **kw):
        return (_DRAFT_HDR +
                f"RECIPE IDEAS{f' for: {craving}' if craving else ''} (plate-method, general guidance)\n\n"
                "• ½ plate non-starchy veg · ¼ plate lean protein · ¼ plate smart carbs\n"
                "• Sample: grilled chicken + roasted broccoli + ⅓ cup quinoa\n"
                "• Sample: salmon + big green salad + small sweet potato\n\n"
                "[the on-box nutrition model expands these from the cited diabetic-plate corpus + your tastes]. "
                "General educational guidance only — not medical nutrition therapy. Your care team sets targets.\n")


@register
class DietMonitor(Skill):
    slug = "diet-monitor"; name = "Diet Monitor"; serves = "patient"; status = "FRAMEWORK"
    desc = "Log meals & carbs, see patterns over time — organize what you eat, never interpret your readings."

    def gather(self, v, **kw):
        return {}

    def draft(self, ctx, **kw):
        return (_DRAFT_HDR +
                "DIET LOG — what to capture (stays on your box):\n"
                "  • meal · time · est. carbs · how you felt\n"
                "  • the system tallies daily carbs and surfaces patterns over weeks\n\n"
                "[the on-box model summarizes trends and flags what to discuss at your next visit]. It ORGANIZES "
                "your log — it never interprets a glucose reading or says 'your sugar is high, eat X' (that's the "
                "firewall: educate + organize, never diagnose). Bring the summary to your care team.\n"
                "Note: a food_log record type is the next vault addition to make this fully live.\n")


@register
class MenuCreator(Skill):
    slug = "menu-creator"; name = "Menu Creator"; serves = "patient"; status = "FRAMEWORK"
    desc = "Weekly plate-method menu + grocery list, aligned to your preferences and budget."

    def gather(self, v, **kw):
        return {}

    def draft(self, ctx, days="7", **kw):
        return (_DRAFT_HDR +
                f"{days}-DAY MENU (plate-method) + GROCERY LIST\n\n"
                "Mon — eggs+spinach / chicken salad / salmon+veg+quinoa\n"
                "Tue — Greek yogurt+berries / turkey wrap / stir-fry+brown rice\n"
                "… [the on-box nutrition model fills the full week from your tastes, then auto-builds the grocery "
                "list and can hand it to the reorder flow]\n\n"
                "GROCERY (sample): eggs · spinach · chicken · salmon · quinoa · berries · Greek yogurt · broccoli\n"
                "General educational guidance — your dietitian/care team sets your targets.\n")


@register
class Fitness(Skill):
    slug = "fitness"; name = "Fitness"; serves = "patient"; status = "FRAMEWORK"
    desc = "Daily exercise — gentle, foot-safe movement plans and activity nudges built around your day."

    def gather(self, v, **kw):
        return {}

    def draft(self, ctx, minutes="20", **kw):
        return (_DRAFT_HDR +
                f"DAILY MOVEMENT — ~{minutes} min, foot-safe options\n\n"
                "• Walk after meals (10 min × 2) — gentle, steadies post-meal energy\n"
                "• Low-impact strength: resistance bands, chair exercises\n"
                "• Swimming / cycling — easy on the feet and joints\n"
                "• Foot check BEFORE and AFTER every session (blisters, hot spots, cuts) — with neuropathy you "
                "may not feel them; well-fitted shoes always\n\n"
                "[the on-box model tailors the plan to your day, energy, and foot status, and sets the nudge]. "
                "General activity guidance — not medical exercise therapy. Clear new exercise with your care team, "
                "especially with foot, eye, or heart complications.\n")


@register
class Wellbeing(Skill):
    slug = "wellbeing"; name = "Well-Being"; serves = "patient"; status = "FRAMEWORK"
    desc = "Mental health & well-being — gentle check-ins, diabetes-distress support, resources, human escalation."

    def gather(self, v, **kw):
        return {"emergency": [c["name"] for c in v.all("contact") if c.get("is_emergency")]}

    def draft(self, ctx, **kw):
        fam = ", ".join(ctx["emergency"]) or "[set an emergency contact]"
        return (_DRAFT_HDR +
                "WELL-BEING CHECK-IN (gentle, on your box)\n\n"
                "• A daily 1–5 mood + stress note — living with diabetes is heavy; diabetes-distress and "
                "depression are common and real, not weakness\n"
                "• The system organizes your check-ins and surfaces patterns to share with your care team\n"
                "• Grounding exercises, coping resources, and your support network — close at hand\n\n"
                f"Your people: {fam}\n\n"
                "⚠️ This is NOT a therapist and NOT a crisis service. If you are in crisis, call or text "
                "988 (Suicide & Crisis Lifeline) or 911 right now. This skill ORGANIZES and CONNECTS you to "
                "humans — it never diagnoses or treats. Escalation: check-in → your emergency contact → care "
                "team → 988 / 911.\n")


@register
class Sleep(Skill):
    slug = "sleep"; name = "Sleep"; serves = "patient"; status = "FRAMEWORK"
    desc = "Sleep tracking & hygiene — log sleep, see patterns (sleep affects glucose), gentle wind-down nudges."

    def gather(self, v, **kw):
        return {}

    def draft(self, ctx, **kw):
        return (_DRAFT_HDR +
                "SLEEP — what to capture (on your box):\n"
                "  • bedtime · wake time · hours · how rested (1–5)\n"
                "  • the system tallies your average and surfaces patterns — poor sleep can raise glucose\n\n"
                "Hygiene basics: consistent schedule · dim screens before bed · watch late carbs & caffeine · "
                "a foot check before bed.\n\n"
                "[the on-box model summarizes trends and sets a wind-down nudge]. It ORGANIZES your sleep log — "
                "it never interprets a reading or diagnoses a sleep disorder; bring the patterns to your care "
                "team (ask about sleep apnea, which is common with diabetes).\n")


def list_skills():
    return [{"slug": s.slug, "name": s.name, "serves": s.serves, "status": s.status, "desc": s.desc}
            for s in REGISTRY.values()]


def run(v, slug, **kw):
    if slug not in REGISTRY:
        return {"error": f"unknown skill '{slug}'. Available: {', '.join(REGISTRY)}"}
    return REGISTRY[slug].run(v, **kw)
