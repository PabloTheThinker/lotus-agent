---
name: lotus-medical-plain-language
description: Transform medical jargon into calm, everyday natural language using OpenMed-aware entity awareness and CDC plain-language rules — without diagnosing.
version: 0.1.0
author: L.O.T.U.S. Project
license: MIT
metadata:
  hermes:
    tags: [Lotus, Health, PlainLanguage, OpenMed, HealthLiteracy]
    related_skills: [lotus-health-stress, lotus-research-core, lotus-realtime-core]
---

# Medical → Natural Language Bridge

## Mission refocus

When health language becomes a wall, L.O.T.U.S. turns it into light people can walk with — clear words, steady pace, no chaos.

## When to use

- User pastes discharge notes, portal messages, lab blurbs, medication lists, or clinician phrases they do not understand  
- User says “what does this mean?” about medical wording  
- Health-stress protocol (P2) with jargon-heavy text  

## Research foundations

1. **OpenMed** (https://github.com/maziyarpanahi/openmed, https://x.com/openmed_ai)  
   - Local clinical NER via `openmed.analyze_text`  
   - PII/de-ID via `openmed.deidentify` before any logging/research  
   - Entities (disease, meds, anatomy, …) become an explanation checklist — not a diagnosis  
2. **CDC Everyday Words / plain language** — short sentences, everyday words, define terms once  
3. Live lookup — reputable pages (CDC, NIH/MedlinePlus, hospital .edu/.gov) when a term needs a careful definition  

## Procedure

1. **Safety first** — emergency red flags → emergency care; do not bury that under vocabulary help.  
2. **Privacy** — if text may contain names/DOB/MRNs, warn the user; prefer local de-ID (OpenMed) before storing or web-pasting. Use synthetic placeholders in cloud prompts.  
3. **Structure (optional OpenMed)** — if `openmed` is installed:
   ```bash
   python - <<'PY'
   from openmed import analyze_text
   # Prefer disease/pharma models for notes the user pasted
   r = analyze_text(TEXT, model_name="disease_detection_superclinical")
   print([(e.text, e.label) for e in r.entities[:20]])
   PY
   ```
   If OpenMed is not installed, skip to linguistic plain-language translation — still valuable.  
4. **Translate** each important term or phrase:
   - Everyday meaning in one short sentence  
   - Keep the medical term once in parentheses if useful  
   - Say what it is *not* claiming (no new diagnosis)  
5. **Emotional wrap** — name that medical paperwork often feels scary; offer one grounding or one question to ask their clinician.  
6. **Clinician bridge** — 1–3 plain questions they can take to their care team.  
7. **Learn** — if a wording style helped, remember it in the living model / memory.

## Output shape (preferred)

```text
In everyday words:
- …

Words that showed up:
- MedicalTerm → plain meaning

What this does NOT mean:
- I’m not diagnosing or changing your treatment.

One gentle next step:
- …

Optional questions for your clinician:
1. …
```

## Examples

| Medical | Everyday |
|---------|----------|
| hypertension | high blood pressure |
| myocardial infarction | heart attack |
| dyspnea | shortness of breath |
| PRN | as needed |
| NPO | nothing by mouth |
| benign | not cancer (in that context — confirm with clinician) |
| idiopathic | cause not known yet |
| prophylaxis | something done to help prevent a problem |

Always check context; some terms have multiple meanings.

## Avoid

- Entity dump without translation  
- Scare-statistics unprompted  
- Dosing / stop-start medication advice  
- Sounding like a charting robot  

## Verification

User can restate the meaning in their own words; fear is lower or clearer; care decisions stay with their clinician.
