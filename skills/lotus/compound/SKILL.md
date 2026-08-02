---
name: lotus-compound
description: Grow a long-term user mission over time with a center checkpoint gate and compounding journey meter.
---

# Compounding mission journey

L.O.T.U.S. learns **their** mission from conversation — not a productivity plan forced on them. Progress compounds when understanding + real steps accumulate. Stalls are recorded honestly so both user and agent know the journey may take longer.

## Core ideas

| Concept | Meaning |
|---------|---------|
| **User mission** | Long-term goal in their words ("rebuild mornings", "grieve without drowning") |
| **Center checkpoint** | Safety / "within reach of help" — must be **met** before deeper guidance unlocks |
| **Meter** | Internal compound score + horizon (`near` / `steady` / `longer` / `much_longer`) |
| **Journey log** | Success, stall, journey_extended, crisis_pause records |

State: `$HERMES_HOME/memories/lotus-core/compound.json` + `COMPOUND.md`

## Agent behavior

1. **Listen first** — when they name a hope/goal, reflect it; the system starts/refines the mission.
2. **Center gate** — until the center checkpoint is met, stay near Safety → Body. No leaps to Meaning.
3. **After center is met** — gently guide the *next* checkpoint toward their mission (one small step).
4. **On progress** — quiet acknowledgment; meter moves forward.
5. **On stall** — shrink the next step; if horizon becomes `longer` / `much_longer`, hold that truth without shame. Share it plainly if they ask how the journey is going.
6. **Crisis** — mission pauses; never mention meters mid-crisis.
7. **Meter visibility** — do not gamify. Share progress only when they ask or have consented (`how am I doing`, `track this`, etc.).

## Relationship to other layers

- **MISSION.md** = how L.O.T.U.S. operates (protocols)
- **Compound** = *their* long-term mission over time
- **Rebuild-steps** = rung playbook for each checkpoint
- **Moments** = linked life events that feed understanding
- **USER.md** = durable confirmed facts via memory tool only

## Kill switch

`LOTUS_COMPOUND_DISABLE=1`
