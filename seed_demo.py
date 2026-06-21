"""
DailyLifeOS · synthetic demo data — NO real PHI.

Loads a plausible-but-fake diabetic's vault so the disappearance-test queries can be
demonstrated end-to-end. All names/values are invented. Real data only ever enters on
the user's own box, by the user.
"""
import datetime as dt
from core.vault import Vault


def _days(n):
    return (dt.datetime.utcnow() + dt.timedelta(days=n)).replace(microsecond=0).isoformat() + "Z"


def seed(v=None):
    v = v or Vault()
    # clear demo tables for idempotency
    for t in ["appointment", "medication", "lab_result", "document", "contact", "supply_item", "wound_photo"]:
        v.cx.execute(f"DELETE FROM {t}")
    v.cx.commit()

    v.add("appointment", provider="Dr. Greene", specialty="Podiatry", when_ts=_days(3),
          location="Jupiter Foot & Ankle", notes="post-op follow-up")
    v.add("appointment", provider="Dr. Patel", specialty="Endocrinology", when_ts=_days(21),
          location="Palm Beach Endocrine")
    v.add("appointment", provider="Dr. Lee", specialty="Ophthalmology", when_ts=_days(70),
          location="Retina Center")

    v.add("medication", name="Insulin (Lantus)", dose="20u", schedule="nightly",
          supply_count=12, supply_unit="days", per_day=1, refill_threshold_days=14, last_refill=_days(-18))
    v.add("medication", name="Metformin", dose="1000mg", schedule="2x daily",
          supply_count=40, supply_unit="tablets", per_day=2, refill_threshold_days=10, last_refill=_days(-25))

    v.add("lab_result", test="A1C", value=8.1, unit="%", when_ts=_days(-180), provider="Dr. Patel")
    v.add("lab_result", test="A1C", value=7.4, unit="%", when_ts=_days(-90), provider="Dr. Patel")
    v.add("lab_result", test="A1C", value=6.9, unit="%", when_ts=_days(-7), provider="Dr. Patel")

    v.add("document", title="BlueCross Insurance Card", doc_type="insurance",
          file_path="vault/03-insurance/bluecross-card.pdf", issuer="BlueCross BlueShield")
    v.add("document", title="Medicare Card", doc_type="insurance",
          file_path="vault/03-insurance/medicare-card.pdf", issuer="CMS")

    v.add("contact", name="Dr. Greene (Podiatry)", role="podiatrist", phone="555-0142", is_emergency=0)
    v.add("contact", name="Sarah (daughter)", role="family", phone="555-0199", is_emergency=1)

    v.add("supply_item", name="Test Strips", count=18, unit="strips", per_day=4, threshold=7)
    v.add("supply_item", name="Pen Needles", count=60, unit="needles", per_day=2, threshold=7)
    v.add("supply_item", name="CGM Sensors", count=2, unit="sensors", per_day=0.1, threshold=10)

    v.add("wound_photo", file_path="vault/09-wound/2026-06-14-left-toe.jpg", location="left great toe",
          when_ts=_days(-7), notes="healing, less redness")
    v.cx.commit()
    return v


if __name__ == "__main__":
    seed()
    print("seeded.")
