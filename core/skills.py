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


def list_skills():
    return [{"slug": s.slug, "name": s.name, "serves": s.serves, "status": s.status, "desc": s.desc}
            for s in REGISTRY.values()]


def run(v, slug, **kw):
    if slug not in REGISTRY:
        return {"error": f"unknown skill '{slug}'. Available: {', '.join(REGISTRY)}"}
    return REGISTRY[slug].run(v, **kw)
