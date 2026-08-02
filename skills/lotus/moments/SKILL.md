---
name: lotus-moments
description: Connect life events, open threads, and conversation data across sessions using the L.O.T.U.S. moments graph.
---

# Moments connection system

Any meaningful event can become a **moment**. Moments link to each other so L.O.T.U.S. can bring the right conversations and data together later — without cold restarts or forced recall.

## What a moment is

| Kind | Examples |
|------|----------|
| `life_event` | job change, breakup, move, wedding |
| `grief` | death, funeral, bereavement |
| `health` | diagnosis, hospital, chronic pain |
| `thread` | "we'll come back to this", unfinished topics |
| `checkin` | "remind me", "check in later" |
| `conversation` | "remember when", "last time we talked" |
| `anchor` | important people / pets / places |
| `affect` | deep depression / numbness clusters |

Stored under `$HERMES_HOME/memories/lotus-core/moments.json` with a human view in `MOMENTS.md`.

## How to use (agent behavior)

1. When `MOMENTS — connection system` context appears, **weave one natural bridge** if it fits the user's energy.
2. Never dump moment IDs or graph jargon at the user.
3. If they reopen a linked topic, bring the *feeling and unfinished thread*, not a transcript dump.
4. When a life fact stabilizes (name, loss, preference), promote via Hermes **memory tool** → `USER.md`. Do not auto-write USER.md from the graph.
5. If they say something is finished / behind them, treat related moments as resolved — do not keep poking.

## Relationship to other layers

- **Continuity** — session resume card + open threads (bridge feeds the graph)
- **Realtime living model** — `shared_moments`, `connection_anchors` (also bridged in)
- **Moments graph** — structured IDs, links, retrieval across conversations
- **USER.md / MEMORY.md** — durable confirmed facts only

## Kill switch

`LOTUS_MOMENTS_DISABLE=1`
