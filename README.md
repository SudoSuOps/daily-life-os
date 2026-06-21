# DailyLifeOS 🐝

**The digital life operating system for diabetics.**

Not an AI company. Not a NAS company. Not a healthcare company. A coherent, owned system that helps a person
living with diabetes stay on top of daily life — medications, supplies, insurance paperwork, appointments, lab
results, family coordination, wound tracking, records, transportation, food planning.

> *"My life is organized."* — the whole product, felt every morning.

Powered by the **LocalDiabetic** vault, fed by the **OpenDiabetic** hive. Part of the OpenDiabetic ecosystem.

---

## The three laws

1. **90% software, 10% AI.** The system *knows* (deterministic, exact, receipted); the model is the
   natural-language *interface*. Value is a data + workflow + retrieval problem, not a model-intelligence problem.
2. **Integration over invention.** The hardware is commodity and the open-source organs already exist
   (Nextcloud, Immich, Home Assistant, Paperless-ngx, ntfy, CalDAV, OCR). The opportunity is connecting them into
   one coherent diabetic-life experience.
3. **The disappearance test.** Build only what someone would *notice if it vanished tomorrow* — the refill
   reminder, the insurance documents, the appointment calendar, the family emergency access, the medical records.

## The stack

| Layer | What | Status |
|---|---|---|
| **1 · Math & Code** | rules · schedules · reminders · supply tracking · escalations · audit trails · notifications | reminder engine **LIVE** |
| **2 · Data (the vault)** | records · insurance · contacts · appointments · labs · imaging · meds — storage + retrieval | vault **LIVE**, typed schema next |
| **3 · Specialized Models** | purpose-built diabetic models (CGM, insurance terms, wound-care, supply, daily life) | DiabeticAnchor-27B **IN BUILD** |
| **4 · Edge Deployment** | train once in the hive → distill 27B → 14B → 9B → 4B–7B → on-box | edge brain **LIVE** |

## The one law: the firewall

Raw PHI never leaves the box. **Models flow down, receipts flow up, PHI crosses never.** Every action emits a
hash-chained, PHI-blind receipt you can recompute yourself. Full-service ≠ black box.

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the full blueprint.

---

## The house

- 🐝 [OpenDiabetic](https://opendiabetic.com) — the hive (compute · datasets · models · community)
- 🐝 [LocalDiabetic](https://localdiabetic.com) — the box (vault · automation · care coordination)
- 🐝 [DiabeticDatasets](https://diabeticdatasets.com) · [DiabeticModels](https://diabeticmodels.com) · [DiabeticLedger](https://diabeticledger.com)

---

© 2026 **Swarm and Bee LLC** (DBA Swarm & Bee AI) · DefendableOS · Proof of Execution · Jupiter, FL ·
build@opendiabetic.com · [@opendiabetics](https://x.com/opendiabetics). Released under the [MIT License](LICENSE).
