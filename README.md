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

## Run it — Layer 1 + 2 are live (no model required)

The typed vault + deterministic retrieval work today, stdlib-only:

```bash
export LD_DATA_DIR=~/.localdiabetic     # your data, your box (default ~/.localdiabetic)
python3 ld.py seed                      # synthetic demo data (no real PHI)

python3 ld.py ask "when's my next podiatrist appointment?"
#  📅 Podiatry with Dr. Greene — 2026-06-24 (in 3 days) · Jupiter Foot & Ankle
python3 ld.py ask "find my insurance card"
#  📄 BlueCross Insurance Card → vault/03-insurance/bluecross-card.pdf  (+1 more on file)
python3 ld.py ask "what was my last A1C?"
#  🩸 Last A1C: 6.9% on 2026-06-14  (↓0.5 vs prior)
python3 ld.py ask "how many test strips do I have left?"
#  📦 Test Strips: 18 strips (~4.5 days)  ⚠️ running low
python3 ld.py ask "what do I need to refill?"
#  🔔 Test Strips (~4.5 days) · Insulin (~12 days)

python3 ld.py receipts                  # verify the PHI-blind hash-chain
python3 test_ld.py                      # end-to-end proof (8/8)
```

Every answer is an exact lookup or a piece of arithmetic — **no model, no guessing**. The on-box
model (Layer 3) becomes the friendly natural-language shell *later*; it calls these same functions,
and the answers never change. That's the point.


## Skills — the apps on the OS (Layer 3)

```bash
python3 ld.py skills                              # list installed apps
python3 ld.py skill credit-sniper claim=CLM-4471 denial_reason="not medically necessary"
python3 ld.py skill grant-writer                 # match assistance + draft application
python3 ld.py skill letter-drop to="Dr. Greene" subject="Records request"
```

Each skill is **Agent-0 + human-in-the-loop**: it gathers your on-box data, drafts an artifact, and waits for
your approval — nothing sends on its own, every run a PHI-blind receipt. `letter-drop`, `credit-sniper`
(model: CreditSniper-edge-4B, ledger-proven), `grant-writer` (corpus: SwarmGrant 280K). Plug a new app in by
subclassing `Skill` and calling `register()`.

## Deploy — hardware-agnostic (the durable part)

Target is **Ubuntu + Docker + local storage**; Synology, UGREEN, ZimaCube, mini-PCs, and Jetsons are
just interchangeable shells. If a vendor changes direction, you keep running. Own the hardware, the data,
the OS, the backups.

```bash
docker compose up --build         # your vault persists in ./data, on your box, never leaves
docker compose run --rm dailylifeos ask "what do I need to refill?"
```

Three paths, same core container:
- **Appliance Mode** — ZimaOS + the container. Simple install. *Patients & families.*
- **Power-User Mode** — Ubuntu + Docker + DailyLifeOS + Home Assistant / Immich / Nextcloud / Tailscale. *Tech-savvy diabetics & chapter operators.*
- **OpenDiabetic Node** — Proxmox + LocalDiabetic VM + local AI + backup vault + Jetson. *Research, clinics, community orgs.*

---

## The house

- 🐝 [OpenDiabetic](https://opendiabetic.com) — the hive (compute · datasets · models · community)
- 🐝 [LocalDiabetic](https://localdiabetic.com) — the box (vault · automation · care coordination)
- 🐝 [DiabeticDatasets](https://diabeticdatasets.com) · [DiabeticModels](https://diabeticmodels.com) · [DiabeticLedger](https://diabeticledger.com)

---

© 2026 **Swarm and Bee LLC** (DBA Swarm & Bee AI) · DefendableOS · Proof of Execution · Jupiter, FL ·
build@opendiabetic.com · [@opendiabetics](https://x.com/opendiabetics). Released under the [MIT License](LICENSE).
