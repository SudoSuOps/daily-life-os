"""
DailyLifeOS · Layer 3 — the skills (the apps on the OS).

A skill is an app that runs on the vault: it GATHERS the right on-box data deterministically (the 90%),
DRAFTS an artifact (the on-box DiabeticDaily model — the 10% — via core.model, with a deterministic
template as the guaranteed fallback), and the human APPROVES before anything leaves. Agent-0 by design —
a skill has zero standing authority, can only propose, and never sends on its own. Every run emits a
PHI-blind receipt that records WHICH engine drafted (model vs template), never the draft.

THE 10% IS WIRED: each skill provides a `system` (its role) and `prompt(ctx)` (the task built from the
gathered on-box facts). run() calls the LOCAL model (core.model → 127.0.0.1 only; PHI never leaves the
box) and falls back to draft() if no model is serving. diet-monitor and wellbeing stay template-only by
design (the safest path for logging + mental-health wording). The firewall lives in core.model.FIREWALL.

Plug a new skill in by subclassing Skill and calling register(). Examples mapping to real cooked work:
  letter-drop   → general advocacy/letter writer
  credit-sniper → insurance-denial & medical-bill appeal   (IRAC gate, ledger-proven)
  grant-writer  → assistance & patient-assistance/grant applications   (corpus: SwarmGrant 280K)
"""
import datetime as dt
from . import receipts

REGISTRY = {}


def register(cls):
    REGISTRY[cls.slug] = cls()   # store a ready instance, keyed by slug
    return cls


class Skill:
    slug = ""; name = ""; serves = ""; desc = ""; status = "LIVE"
    system = "You are a DailyLifeOS skill that organizes records and drafts documents."  # the skill's role for the model

    def gather(self, v, **kw):
        """Deterministic: pull the on-box records this skill needs. Returns a context dict (may hold PHI; stays local)."""
        return {}

    def prompt(self, ctx, **kw):
        """Build the task prompt for the on-box model from the gathered context.
        Return None to skip the model and use the template (e.g. nothing to draft yet)."""
        return None

    def draft(self, ctx, **kw):
        """Deterministic template — the guaranteed fallback when no on-box model is available."""
        return ""

    def run(self, v, **kw):
        from . import model
        ctx = self.gather(v, **kw)
        text, engine = None, "template"
        p = self.prompt(ctx, **kw)
        if p and model.available():
            text = model.draft(self.system, p)           # the 10% — DiabeticDaily, on-box
            if text:
                engine = "diabetic-daily · on-box"
        if not text:
            text = self.draft(ctx, **kw)                 # the 90% — deterministic template
        # receipt is PHI-blind: it records THAT a draft was made + which engine, never the draft itself
        rh = receipts.emit(f"skill:{self.slug}", 1, phi_touched=True,
                           meta={"skill": self.slug, "engine": engine, "artifact": kw.get("artifact", "draft")})
        return {"skill": self.slug, "name": self.name, "status": self.status,
                "draft": text, "engine": engine, "needs_approval": True, "receipt": rh[:12]}


_DRAFT_HDR = ("— — — DRAFT · review and approve before anything is sent — — —\n"
              "✋ Human-in-the-loop: this skill only proposes. Nothing leaves your box until you say so.\n\n")


@register
class LetterDrop(Skill):
    slug = "letter-drop"; name = "LetterDrop"; serves = "both"; status = "LIVE"
    desc = "Advocacy & letter writer — drafts a clean letter from your contacts and the facts on file."
    system = ("You are LetterDrop, a careful advocacy letter writer. You draft a clear, respectful, "
              "one-page letter using only the recipient and facts the user provides. You write the prose; "
              "you never invent names, dates, claim numbers, or medical facts that weren't given.")

    def gather(self, v, to=None, **kw):
        contacts = v.all("contact")
        match = next((c for c in contacts if to and to.lower() in (c["name"] or "").lower()), None)
        return {"to": match, "raw_to": to}

    def prompt(self, ctx, subject="", body="", **kw):
        to = ctx["to"]["name"] if ctx.get("to") else (ctx.get("raw_to") or "the recipient")
        if not (subject or body):
            return None
        return (f"Write a letter to {to}.\nSubject: {subject or '(infer a fitting subject)'}\n"
                f"What the person wants to say (their words/notes): {body or '(none given)'}\n"
                "Produce a complete, ready-to-send letter: date line, greeting, 2–4 tight paragraphs, "
                "a clear ask, and a sign-off placeholder. Respectful and firm. Use only the facts above.")

    def draft(self, ctx, subject="", body="", **kw):
        to = ctx["to"]["name"] if ctx.get("to") else (ctx.get("raw_to") or "[recipient]")
        today = dt.date.today().isoformat()
        return (_DRAFT_HDR +
                f"{today}\n\nDear {to},\n\nRe: {subject or '[subject]'}\n\n"
                f"{body or '[your message — LetterDrop will draft the prose; the on-box writer model fills this in]'}\n\n"
                "Sincerely,\n[your name]\n")


@register
class CreditSniper(Skill):
    slug = "credit-sniper"; name = "CreditSniper"; serves = "both"; status = "LIVE"
    desc = "Insurance-denial & medical-bill appeal — classifies the denial, finds the deadline, drafts an IRAC appeal."
    system = ("You are CreditSniper, an insurance-appeal drafter. You write a firm, well-structured appeal of a "
              "claim denial using the IRAC frame (Issue, Rule, Application, Conclusion). Argue medical necessity "
              "and the plan's own coverage terms. Cite only facts the user provides. This is self-advocacy "
              "drafting, not legal advice. Never invent policy language, claim numbers, or clinical facts.")

    def gather(self, v, **kw):
        ins = [d for d in v.all("document") if "insurance" in (d.get("doc_type") or "").lower()]
        return {"insurance": ins[0] if ins else None, "insurance_count": len(ins)}

    def prompt(self, ctx, denial_reason="", claim="", deadline_days=180, **kw):
        if not denial_reason:
            return None
        ins = ctx.get("insurance"); payer = ins["issuer"] if ins else "the payer"
        due = (dt.date.today() + dt.timedelta(days=int(deadline_days))).isoformat()
        return (f"Draft an appeal of a claim denial.\nPayer: {payer}\nClaim: {claim or '(number not given)'}\n"
                f"Stated denial reason: {denial_reason}\nAppeal deadline (already computed, {deadline_days} days): {due}\n"
                "Write it in IRAC structure with those exact headings. Make the medical-necessity argument from "
                "the facts given, request the denial be overturned and the claim paid, and end with the escalation "
                "ladder (internal appeal → external/independent review → state regulator).")

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
    slug = "grant-writer"; name = "Grant Writer"; serves = "patient"; status = "LIVE"
    desc = "Assistance & grants navigator — matches programs (PAP, $35 insulin cap, shoe benefit) and drafts the application."
    system = 'You are an assistance and grants navigator. From the medications and facts on file you match REAL programs (manufacturer copay/Patient-Assistance Programs, the $35 Medicare insulin cap, the Medicare therapeutic-shoe benefit, diabetic-supply foundation grants) and draft the application. Only suggest programs that plausibly fit the facts; never invent program names, amounts, or eligibility.'

    def gather(self, v, **kw):
        meds = [m["name"] for m in v.all("medication")]
        return {"medications": meds}

    def prompt(self, ctx, program="", **kw):
        meds = ctx.get("medications") or []
        return ("Medications on file: " + (", ".join(meds) or "none") + ".\n"
                "1) List the assistance programs that plausibly fit (insulin copay/PAP and the $35 cap only if they "
                "take insulin; the Medicare therapeutic-shoe benefit; diabetic-supply foundation grants). "
                "2) Then draft a short, fundable application for " + (program or "the best-fit program") + " from the "
                "facts on file. Use only what is given; mark anything the person still needs to provide.")

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
    slug = "legal"; name = "Legal"; serves = "both"; status = "LIVE"
    desc = "Legal & advocacy — records requests, ADA/FMLA & disability paperwork, consumer-rights disputes."
    system = ("You are a self-advocacy drafter for everyday legal paperwork: medical-records requests, ADA "
              "accommodation letters, FMLA forms, SSDI/SSI function narratives, and billing disputes. You draft "
              "the letter or packet from the facts given. This is self-advocacy drafting, NOT legal advice — the "
              "person reviews and signs. Never invent statutes, case law, dates, or facts not provided.")

    def gather(self, v, **kw):
        return {"documents": [d["title"] for d in v.all("document")],
                "contacts": [c["name"] for c in v.all("contact")]}

    def prompt(self, ctx, matter="", to="", **kw):
        if not matter:
            return None
        docs = ", ".join(ctx["documents"]) or "none on file"
        return (f"Draft a self-advocacy letter.\nRecipient: {to or '(infer the right office)'}\n"
                f"Matter: {matter}\nRecords the person has on file they could attach: {docs}\n"
                "Write a complete, respectful, firm letter with a clear request and a reasonable response "
                "deadline. End with the escalation path (request → formal complaint → state regulator / "
                "civil-rights office). Add one line that this is self-advocacy drafting, not legal advice.")

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
    slug = "accounting"; name = "Accounting"; serves = "both"; status = "LIVE"
    desc = "Medical accounting — expenses, deductible progress, HSA/FSA-eligible categories, cost of care."
    system = 'You organize medical expenses for tax, HSA, and FSA. You categorize spend, note which categories are typically eligible, and track what to capture. You never give tax or financial advice; you organize. Use only the records given and never invent dollar amounts.'

    def gather(self, v, **kw):
        return {"meds": v.all("medication"), "supplies": v.all("supply_item"),
                "visits": len(v.all("appointment"))}

    def prompt(self, ctx, year="", **kw):
        meds, sup, visits = ctx["meds"], ctx["supplies"], ctx["visits"]
        yr = year or dt.date.today().year
        return ("Build a medical-expense organizer for " + str(yr) + ".\n"
                "Medications on file: " + (", ".join(m["name"] for m in meds) or "none") + "\n"
                "Supplies on file: " + (", ".join(s["name"] for s in sup) or "none") + "\n"
                "Appointments on file: " + str(visits) + "\n"
                "Group the likely cost categories (prescriptions, diabetic supplies, office visits, therapeutic "
                "shoes, mileage to care), note which are typically HSA/FSA-eligible, and list what to add to enable "
                "dollar totals. Organize only and state explicitly that this is not tax advice.")

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
    slug = "cookbook"; name = "Cookbook"; serves = "patient"; status = "LIVE"
    desc = "Diabetic-friendly recipes — plate-method, lower-glycemic ideas built around what you like."
    system = ("You are a diabetic-friendly cook. You suggest plate-method, lower-glycemic meal ideas built "
              "around what the person likes and has. Give rough carb estimates per idea. This is general "
              "educational guidance, not medical nutrition therapy — the person's care team sets their targets.")

    def gather(self, v, **kw):
        return {"meds": [m["name"] for m in v.all("medication")]}

    def prompt(self, ctx, craving="", **kw):
        return (f"Suggest 3 diabetic-friendly meal ideas{f' for: {craving}' if craving else ''}. "
                "For each: a one-line description following the plate method (½ non-starchy veg · ¼ lean protein "
                "· ¼ smart carbs) and a rough total-carb estimate. Keep it short, practical, and encouraging. "
                "Close with one line reminding this is general guidance, not medical nutrition therapy.")

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
    slug = "diet-monitor"; name = "Diet Monitor"; serves = "patient"; status = "LIVE"
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
    slug = "menu-creator"; name = "Menu Creator"; serves = "patient"; status = "LIVE"
    desc = "Weekly plate-method menu + grocery list, aligned to your preferences and budget."
    system = 'You build a plate-method weekly menu and a matching grocery list around the tastes and budget given. General educational guidance, not medical nutrition therapy; the care team sets targets.'

    def gather(self, v, **kw):
        return {}

    def prompt(self, ctx, days="7", **kw):
        return ("Build a " + str(days) + "-day diabetic-friendly menu using the plate method (half non-starchy veg, "
                "quarter lean protein, quarter smart carbs). Give breakfast, lunch, and dinner per day in one short "
                "line each, then a consolidated grocery list grouped by aisle. Keep it affordable and simple. End "
                "with one line that this is general guidance, not medical nutrition therapy.")

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
    slug = "fitness"; name = "Fitness"; serves = "patient"; status = "LIVE"
    desc = "Daily exercise — gentle, foot-safe movement plans and activity nudges built around your day."
    system = 'You suggest gentle, FOOT-SAFE movement for a person with diabetes (walking after meals, low-impact strength, swimming or cycling), always with a before and after foot-check reminder and well-fitted shoes. General activity guidance, not medical exercise therapy.'

    def gather(self, v, **kw):
        return {}

    def prompt(self, ctx, minutes="20", **kw):
        return ("Suggest a roughly " + str(minutes) + "-minute foot-safe daily movement plan for someone with "
                "diabetes. Include specific gentle options, a foot check BEFORE and AFTER (neuropathy can hide "
                "blisters and sores), and well-fitted shoes. Warm and encouraging. End with the note to clear new "
                "exercise with their care team, especially with foot, eye, or heart complications.")

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
    slug = "wellbeing"; name = "Well-Being"; serves = "patient"; status = "LIVE"
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
    slug = "sleep"; name = "Sleep"; serves = "patient"; status = "LIVE"
    desc = "Sleep tracking & hygiene — log sleep, see patterns (sleep affects glucose), gentle wind-down nudges."
    system = 'You organize a sleep log and give general sleep-hygiene basics. You never interpret a reading or diagnose a sleep disorder; you organize and suggest discussing patterns such as sleep apnea with the care team.'

    def gather(self, v, **kw):
        return {}

    def prompt(self, ctx, **kw):
        return ("Give a short, friendly sleep-hygiene checklist for a person with diabetes (consistent schedule, dim "
                "screens, watch late carbs and caffeine, a foot check before bed) and say what to capture in a sleep "
                "log (bedtime, wake, hours, rested 1 to 5). Note that poor sleep can raise glucose and to bring "
                "patterns to the care team. Organize and educate only; never interpret a reading or diagnose.")

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


@register
class AskDoctor(Skill):
    slug = "ask-doctor"; name = "Ask the Doctor"; serves = "patient"; status = "LIVE"
    desc = "Visit prep — turns your records into the right questions to ASK your doctor (it never answers them)."
    system = 'You turn the records into a clear, prioritized list of questions for the PERSON to ASK their doctor. You never answer medical questions; you only prepare the questions so nothing important is forgotten.'

    def gather(self, v, **kw):
        from . import query
        return {"appt": query.next_appointment(v), "a1c": query.last_lab(v, "A1C"),
                "refill": query.refill_due(v)}

    def prompt(self, ctx, **kw):
        appt, a1c, refill = ctx["appt"], ctx["a1c"], ctx["refill"]
        bits = []
        if appt.get("found"): bits.append("Visit: " + str(appt["specialty"]) + " with " + str(appt["provider"]) + " in " + str(appt["in_days"]) + " days.")
        if a1c.get("found"):
            t = a1c.get("trend_vs_prev"); d = " (down)" if t and t < 0 else (" (up)" if t and t > 0 else "")
            bits.append("Last A1C: " + str(a1c["value"]) + "%" + d + ".")
        if refill.get("due"): bits.append("Low on: " + ", ".join(x["name"] for x in refill["due"]) + ".")
        return ("From these facts, write a short prioritized list of questions for the PERSON to ask their doctor "
                "(about the A1C and plan, medications and doses, feet, upcoming A1C/eye/foot screenings, and recent "
                "labs). Questions only; never answer them.\nFacts: " + (" ".join(bits) or "general visit prep."))

    def draft(self, ctx, **kw):
        appt, a1c, refill = ctx["appt"], ctx["a1c"], ctx["refill"]
        lines = [_DRAFT_HDR, "QUESTIONS TO BRING TO YOUR VISIT\n"]
        if appt.get("found"):
            lines.append(f"Visit: {appt['specialty']} with {appt['provider']} (in {appt['in_days']} days)\n")
        if a1c.get("found"):
            t = a1c.get("trend_vs_prev")
            dirn = " (down from prior)" if t and t < 0 else (" (up from prior)" if t and t > 0 else "")
            lines.append(f"• My last A1C was {a1c['value']}%{dirn} — are we on track, or should we adjust the plan?")
        if refill.get("due"):
            lines.append("• I'm low on " + ", ".join(d["name"] for d in refill["due"])
                         + " — can we handle refills today?")
        lines += [
            "• Any changes to my medications or doses?",
            "• How do my feet look — anything to watch? (mention any numbness, sores, or hot spots)",
            "• When are my next A1C, eye exam, and foot exam due?",
            "• Is there anything in my recent labs I should understand?",
        ]
        lines.append("\nThis prepares questions for YOU to ask — it does not answer medical questions or give "
                     "advice. Your doctor answers; this just makes sure nothing important gets forgotten.")
        return "\n".join(lines)


def list_skills():
    return [{"slug": s.slug, "name": s.name, "serves": s.serves, "status": s.status, "desc": s.desc}
            for s in REGISTRY.values()]


def run(v, slug, **kw):
    if slug not in REGISTRY:
        return {"error": f"unknown skill '{slug}'. Available: {', '.join(REGISTRY)}"}
    return REGISTRY[slug].run(v, **kw)
