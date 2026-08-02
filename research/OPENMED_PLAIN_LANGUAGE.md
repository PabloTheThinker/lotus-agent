# Research: OpenMed + Plain Medical Language for L.O.T.U.S.

**Purpose:** Refocus part of the mission so medical language becomes *understandable* — never colder, never more chaotic — using public OpenMed capabilities and plain-language science.

## OpenMed (open repo)

- **Repo:** https://github.com/maziyarpanahi/openmed  
- **Site:** https://openmed.life/  
- **X:** https://x.com/openmed_ai  
- **License:** Apache-2.0  
- **Posture:** Local-first clinical AI — patient text stays on-device

### Abilities that help L.O.T.U.S.

| Capability | Why it matters for users in distress |
|------------|--------------------------------------|
| `analyze_text(...)` clinical NER | Spot diseases, meds, anatomy, conditions in notes/lab blurbs the user pastes |
| Disease / pharma / anatomy / oncology / gene detectors | Name *what* is in the text so we can explain each piece in everyday words |
| `deidentify()` / PII (55+ types, HIPAA Safe Harbor set) | Reduce accidental exposure of names, dates, IDs when researching or logging |
| 2,000+ biomedical models, multilingual | Wider coverage of clinical vocabulary than a generic LLM alone |
| Agent Skills catalog in the OpenMed repo | Portable `SKILL.md` workflows for NER → de-ID pipelines |
| On-device (CPU/CUDA/MLX/mobile/browser) | Aligns with privacy for health-anxious users |

OpenMed does **not** by itself write bedside plain language — it **structures** medical text. L.O.T.U.S. then translates structured entities + original wording into calm, native natural language.

### Reference pipeline (mission-aligned)

```text
User pastes clinical / lab / portal text
        │
        ▼
[Optional OpenMed] deidentify → analyze_text (entities)
        │
        ▼
[L.O.T.U.S. plain-language bridge]
  • everyday words (CDC Everyday Words / Clear Communication)
  • keep medical term once, define it
  • one meaning per sentence
  • questions to ask their clinician
        │
        ▼
User hears human language — not a wall of jargon
```

Pattern also used publicly by patient-advocacy stacks (e.g. OpenMed NER → local LLM plain explanation). L.O.T.U.S. stays a **companion**, not a diagnostician.

## Plain-language science (public)

- CDC **Everyday Words for Public Health Communication** — jargon → everyday alternatives  
  https://www.cdc.gov/ccindex/everydaywords/  
- CDC **Plain Language** / Clear Communication Index  
- Federal Plain Language Guidelines (short sentences, active voice, define terms)

Rules L.O.T.U.S. adopts:
1. Prefer everyday words (`high blood pressure` over `hypertension` when teaching).  
2. If a medical term must stay, define it the first time in one short clause.  
3. ~one idea per sentence; active voice; “you” when caring.  
4. Never invent diagnoses from jargon translation.  
5. Emergencies → emergency care, not vocabulary lessons.

## X / open research pulse

Track and research (via Hermes `web_search` / `x_search` when available):

- `@openmed_ai` — model releases, NER/PII demos, on-device workflows  
- Nous Research / Hermes public posts — agent memory, skills, tool use for research loops  
- Public health literacy accounts & CDC releases — fresh plain-language guidance  

Research subroutine should queue topics like:
- “OpenMed analyze_text disease_detection plain language companion pattern”
- “CDC everyday words medical jargon patient distress”
- “health literacy explain lab results without diagnosing”

## What L.O.T.U.S. must **not** do with this stack

- Diagnose, dose, or override a clinician from NER labels  
- Send real PHI to cloud tools when local de-ID is available  
- Research self-harm / violence methods under a “medical” pretext  
- Overwhelm a numb or grieving user with entity dumps — **translate, then soothe**

## Integration map (this repo)

| Piece | Role |
|-------|------|
| `skills/lotus/medical-plain-language/` | Procedural skill for jargon → natural language |
| `MISSION.md` P2 + plain-language bridge | Mission refocus |
| `SOUL.md` | Voice: medical clarity without coldness |
| Realtime research queue (P2) | Keeps learning better explanations |
| Optional: `pip install openmed[hf]` in profile env | Local NER when hardware allows |
