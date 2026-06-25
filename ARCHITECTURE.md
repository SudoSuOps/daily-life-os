# DailyLifeOS — Architecture

> *The digital life operating system for diabetics.* Not an AI company, not a NAS company, not a
> healthcare company. The center of gravity is **the workflow and ownership** — the model is one
> subsystem. Powered by the LocalDiabetic vault, fed by the OpenDiabetic hive.
> **2026-06-21 · canonical spec.**

---

## The doctrine (three laws)

1. **90% software, 10% AI.** The system KNOWS (deterministic, exact, receipted); the model is the
   natural-language INTERFACE. Value is a data + workflow + retrieval problem, not a model-intelligence problem.
2. **Integration over invention.** The hardware is commodity, the OSS organs already exist. The opportunity
   is connecting them into ONE coherent experience — *"my life is organized."* The moat is the experience +
   the trust layer + the give-network, not any one box.
3. **The disappearance test.** Build only what someone would *notice if it vanished tomorrow* (refill reminder,
   insurance docs, appointment calendar, family emergency access, medical records). Skip the novelty (a 10%-smarter
   chatbot — nobody would notice). The feature gate for the whole OS.

---

## The 4-layer stack (every layer mapped to a LIVE asset)

### Layer 1 — Math & Code (the foundation)
Deterministic software. **No frontier AI.** Rules · schedules · reminders · supply tracking · escalations ·
audit trails · notifications · document indexing · data synchronization.
- **Live in the LocalDiabetic *deployment* (separate repo `LocalDiabetic-Home-Vault`, not this repo):**
  `ld_remind.py` — the reminder/nudge scheduler (daily/weekly/interval/once, ack + family-escalation,
  generic-off-box) on the Synology NAS via cron + self-hosted ntfy + Resend email.
- **Live in THIS repo:** the typed vault, the deterministic query engine, the LifeBoard, the skill framework,
  and hash-chained receipts — the reference implementation of the thesis you can run today. (This repo does
  not itself ship that NAS reminder engine; the two share the doctrine, not the code.)
- **Discipline:** `/math-and-code` (re-derive every number — days-of-supply, appeal deadlines), deterministic
  gates, the hash-chained ledger (`dl.py`).
- **Status:** reminder engine **LIVE**; supply/escalation/indexing **FRAMEWORK**.

### Layer 2 — Data (the vault)
Storage + retrieval. Medical records · insurance documents · contacts · appointments · lab results · imaging
reports · medication history.
- **Live today:** the 15-folder LocalDiabetic Home Vault on the NAS (HARD-INVARIANT: raw PHI never auto-leaves
  the box) + fill-in templates.
- **Next:** promote folders → **typed records** (appointment, med, lab/A1C, document, contact, supply-item,
  wound-photo) so retrieval is a query, not a file hunt.
- **Status:** vault (filesystem) **LIVE**; typed schema + indexed retrieval **FRAMEWORK**.

### Layer 3 — Specialized Models (domain knowledge > parameter count)
Purpose-built diabetic models that understand CGM data, insurance terminology, wound-care workflows, supply
management, daily diabetic life — vs a generic "tell me about diabetes" model.
- **Cooking now:** **DiabeticAnchor-27B** (clinician-grade, the foundation the edge tiers distill from) — on
  swarmrails, ~35%, eval 0.77, converging.
- **Proven:** footcare-edge-4b (beats base v1), CreditSniper-edge-4B (ledger-verified beat-base).
- **Status:** anchor **IN BUILD**; edge tiers **proven / in build**.

### Layer 4 — Edge Deployment (train once, distribute everywhere)
The same knowledge propagates down the network as distilled tiers:
```
  Foundation      27B master      (the hive — DiabeticAnchor-27B)
  Community Node  14B distilled   (DiabeticNode)
  Home Appliance   9B distilled   (NAS / ZimaCube / UGREEN)
  Jetson         4B–7B distilled  (the edge brain — on-box, private)
```
- **Live in the LocalDiabetic *deployment* (separate repo `localdiabetic-edge`, not this repo):** the Edge Brain
  on the Jetson @ .79 — `/infer` (organize/summarize/nudge, **diagnose→422**) + a firewall proxy, now backed by
  **DiabeticJr-9B** on a dedicated GPU; the only file-write is a non-PHI hash-chained receipt.
- **Live in THIS repo:** `core/model.py` — the same idea, loopback-only by design (PHI drafted on-box, never
  sent off): it **auto-discovers a DiabeticDaily model in your local Ollama** and the skills draft with it.
- **Why it scales:** most users **never need the 27B locally** — they need "when's my appointment / find my
  insurance card / how many strips left / show my last foot photo / remind me to refill." Software problems
  first; the model is there when language understanding helps.
- **Status:** edge brain **LIVE**; the full 27B→14B→9B distillation ladder **FRAMEWORK** (anchor must land first).

---

## The integration map (the 90% is mostly *wiring*, not reinventing)

| Daily reality | Proven OSS organ | DailyLifeOS adds (the diabetic layer) |
|---|---|---|
| Records / documents | Paperless-ngx / Nextcloud | typed diabetic taxonomy · 10-sec retrieval |
| Wound tracking | Immich | wound-progression timeline · clinician-share |
| Lab results (A1C) | OCR (tesseract) | structured A1C history + trend |
| Meds / refills | ntfy + `ld_remind` ✅ | med schedule · days-of-supply math |
| Appointments | CalDAV / Radicale | prep packets · podiatry cadence |
| Supplies / inventory | Grocy | reorder-before-zero |
| Sensors / automation | Home Assistant | CGM / scale ingest · alerts |
| Food planning | Mealie / Grocy | plate-method + grocery list |
| Family / emergency | *(thin custom)* | emergency access · escalation ladder |
| Transportation | *(give-network)* | ride coordination |

We make proven tools **speak diabetes**, behind the firewall, with receipts, under one conversational shell.

---

## The trust layer (the real moat)

- **THE FIREWALL (the one law):** raw PHI never leaves the box. Models flow DOWN, receipts flow UP, PHI crosses
  NEVER. The hive refuses PHI in (`assert_non_phi`, typed `open:`/`synthetic:`/`model:` prefixes); the edge brain
  refuses diagnosis out (422) and never persists PHI.
- **Receipts:** every action emits a hash-chained, PHI-blind receipt (`phi_touched:false`) — recomputable in a
  browser at diabeticledger.com. Full-service ≠ black box.
- **Agent-0 + human-in-the-loop:** every DiabeticAgent is born with zero authority + zero PHI, can only *propose*;
  committing/PHI actions stop at a human approval gate.

---

## The hardware is commodity; the experience is the product

A 2-bay NAS · Synology · UGREEN · ZimaCube · a Jetson — any is enough, because most value is **math, code,
storage, and execution.** The model just makes the interface friendlier. We do not sell hardware; we deliver the
coherent experience that runs on whatever box the member owns.

## The house

```
🐝 OpenDiabetic Hive   — training · datasets · compute · research        (cloud)
        │  models down ▼   ▲ receipts up   ·   PHI crosses NEVER
🐝 LocalDiabetic Node  — DailyLifeOS: vault · automation · notifications ·
                          family support · local inference               (the box)
                            └─ the model is ONE service among many
```
**Center of gravity: workflow + ownership.** The thing people feel working for them every morning is the system
helping them stay on top of life — *"my life is organized."*

---

## Honest status board (no vaporware)

| Layer | LIVE | FRAMEWORK / IN BUILD |
|---|---|---|
| L1 Math & Code | reminder/nudge engine (NAS cron + ntfy + Resend) | supply tracking · escalations · indexing |
| L2 Data | 15-folder vault + HARD-INVARIANT | typed records + indexed retrieval |
| L3 Models | footcare-edge-4b, CreditSniper-edge-4B (proven) | DiabeticAnchor-27B (cooking ~35%) |
| L4 Edge | edge brain (`ld_edge.py` + DiabeticJr-9B, diagnose→422) | 27B→14B→9B→4B distillation ladder |

**First build (per the disappearance test):** typed vault + retrieval (L2) so "find my insurance card" and
"what was my last A1C?" return in 10 seconds — the highest "you'd notice if it vanished" value, and pure L1+L2
software (no model required). The model becomes the friendly shell on top once the system underneath is solid.
