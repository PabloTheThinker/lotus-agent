---
name: lotus-pattern-talk
description: Pattern recognition + Talk Plan wired into living model and Hermes memory
---

# Pattern Talk

Lotus uses a Python pattern recognizer (`harness/lotus/speech/patterns.py`) to decide
how to talk each turn. The Talk Plan feeds the **Speech Gateway** — not a stack of
competing Voice OS / EI / Flow essays.

## What it does

1. **Recognize** needs: friend_shock, way_out, hard_path, reassure, company, answer, receipt, sit, acute…
2. **Domain**: mental health overall, grief, anxiety, shock, acute
3. **Reply shape**: sms_burst (shock) / sms_short / sms_medium
4. **Moves**:
   - friend_shock → best-friend bursts ("ok ok — what happened?")
   - way_out → honest talk-through path (from compound/mission)
   - hard_path → escalate when soft hope is looping
5. **Anti-repeat**: bans recycled clichés + recent phrases
6. **Learn** → `$HERMES_HOME/memories/lotus-core/talk_patterns.json`
7. **Sync** → LivingUserModel (`sync_pattern_memory_to_model`) so adaptive/living injects see prefs
8. **Bridge** → Hermes memory tool nudge when prefs are durable

## Inject order (companion)

Speech Gateway (character + Talk Plan + pattern memory) → living model → adaptive →
Hermes memory bridge → continuity / compound / moments.

Moment-route only for true acute / crisis / medical emergency.

## Human texting rules

- Best friend on iMessage — not essay mode
- Shock → short bursts; stuck loop → hard truth + one path
- Never recycle hearts/wrecked/forever lines
- Never meta-negation
