# Research: Moment context + health containment

**Date:** 2026-08-02  
**Purpose:** Fix two related failures — (1) context lock treated as “never use drunk/high,” and (2) health paths false-triggering clinical Q&A on non-health moments.

## Layer findings

### Context lock (speech)

- **Intended:** never *invent* scene details.
- **Drift:** bans listed `drunk/high/crying` so models avoided using those words even when the user said them.
- **Fix principle:** USE stated facts; NEVER invent unstated ones. Stay inside the active moment.

### Protocol / health false positives

- Bare token `hospital` classified `P2_health` — so “mom’s in the hospital” pulled health profiles, clinician-question traps, and organize-symptoms mission moves.
- `_CHARGED_RE` matched `2am` alone — “texted at 2am” looked charged/acute without panic language.
- Health skill/MISSION defaulted to “list questions for your doctor” every turn.

### Moment focus

- Talk Plan / gateway had anti-invent rules but no **active facts** channel from this turn/history.
- Without that, models either invent (to sound vivid) or ignore real situational context and digress.

## External research (operationalized)

| Source | Takeaway for Lotus |
|--------|-------------------|
| WHO Psychological First Aid (Look / Listen / Link) | Stay with present needs; listen without pressure; practical calm — not digressive counseling |
| MHFA substance-use / alcohol guidelines | If intoxicated: simple clear language; stay present; don’t force a serious “your drinking” confrontation in that moment; safety first |
| Health-anxiety chatbot literature (Otis/BETSY reviews) | Avoid clinical interrogation loops; everyday language; support anxiety without medicalizing every turn |
| AAEP / de-escalation (already in moment_route) | Short sentences in heat; don’t pile clinical paragraphs |

## Combined pattern

1. **Stated ≠ invented** — extract what they said; inject as USE-list.
2. **Role sensitivity** — third-party hospital ≠ personal health stress.
3. **Containment before organization** — health anxiety: stay with fear tonight; clinician questions only if they ask / pasted jargon.
4. **One moment** — don’t spiral to unrelated topics or “helpful” side quests.

## Code landing zones

- `speech/stated_facts.py` — extract + moment containment directive
- `speech/context_lock.py` — USE / invent rewrite
- `speech/gateway.py` — inject facts + health containment
- `protocols.py` / `guardrails.py` / `moments/engine.py` — health false-positive fix
- `moment_route.py` — drop bare `2am` charged trigger
- `MISSION.md` + health skill/profile + plain_language — containment-first
