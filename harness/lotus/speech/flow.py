"""Natural conversational flow — research-backed reply craft.

Primary sources (applied as chat rules, not citations in user replies):
- Clark & Brennan (1991), Clark & Schaefer (1989): grounding — only enough
  evidence of understanding for *current purposes*; a relevant next turn often
  grounds better than a long paraphrase.
- Grice (1975): Quantity / Relation — say what the turn needs, not more;
  stay relevant to their purpose (vent / ask / sit), not to a therapy script.
- Sacks, Schegloff & Jefferson; adjacency pairs + preference: answer questions
  directly; trouble-tellings want affiliation or a real take — not a recap;
  preferred seconds are short and unmarked.
- Bangerter et al. / Cognitive Science (2025): LLMs over-align, misuse
  coordination markers ("yeah"/"okay") as long-turn openers; humans use those
  as short backchannels, then speak.
- Verbal-tic analyses (2026): formulaic empathy and openers accumulate across turns.
- Mental-health CA design: match-then-steer (light tone match → your move), not mirror.
"""

from __future__ import annotations

import re

FLOW_DIRECTIVE = """[L.O.T.U.S. FLOW — natural human conversation]
Research-shaped rules (Clark grounding · Grice · conversation analysis · LLM dialogue studies):

1) GROUND LIGHTLY (Clark & Brennan)
   Show you got it with a *relevant next contribution*, not a summary of their words.
   Ground only enough for this turn's purpose. Over-acknowledgment reads fake.

2) MATCH THE MOVE (adjacency / preference)
   - Question → answer first (direct). Explain after if needed.
   - Trouble-telling / vent → your take or quiet company — not a theme inventory.
   - Thanks / "that landed" → short receipt ("Good." / "Glad it fit.") then stop.
   - Prefer short unmarked replies when the move is simple.

3) QUANTITY (Grice)
   Say enough for the need — not a lecture, not a nod-along opener plus essay.
   If they want company, don't deliver a plan. If they ask a question, don't dodge into empathy theater.

4) DON'T OVER-ALIGN (LLM dialogue findings)
   Humans notice exaggerated agreement and imitation. Relate lightly; keep Lotus voice.
   Ban habitual openers: "Yeah." / "Yep." / "Right." / "Totally." as turn starts.
   Don't stack discourse markers ("Well… so… anyway…") at the front of long turns.

5) MATCH-THEN-STEER (care chat design)
   Optional light tone match (energy/depth), then *your* thought or foothold.
   Steer = one real move: a take, a distinction, a gentle question, or quiet — not a mirror.

6) CHAT RHYTHM
   Trust them to follow without signposts (skip "Furthermore/Additionally/What I'm hearing").
   Uneven sentences. End when a human would — often sooner than you think.
   Presence is implied by useful content, not slogans ("I'm here for that weight").

7) SILENT HONORING
   If they refuse pep talks / plans — just don't do those. Never announce the refusal.

Anti-tic: vary openings across the thread; never reuse the same empathy formula two turns in a row.
Also avoid essay openers like "There's a particular…" and closers like "I'm with how heavy this is" /
"You don't have to make it neat" — those are verbal tics, not grounding."""


def flow_block() -> str:
    return FLOW_DIRECTIVE


_TIC_FRAGMENTS = (
    "how heavy this is",
    "how heavy that is",
    "sitting with how heavy",
    "make it neat for me",
    "make it make sense",
    "nothing has to get solved",
    "stay in the room with how",
    "not here to brighten",
    "not here to turn it into a project",
    "i'm sitting with how",
    "i'm with how heavy",
    "i'm here with how heavy",
    "i'm here for the wanting",
    "i'm here for that",
    "i'm staying right here with you",
    "you're not alone in this",
    "you've got this one stretch",
    "you're allowed to put this down",
    "has a particular sharpness",
    "there's a particular",
    # Meta-negation / AI posture — nobody texts like this
    "i'm not handing you",
    "not handing you a",
    "i won't hand you",
    "no to-do list",
    "not a to-do list",
    "i'm not going to give you advice",
    "i'm not here to give advice",
    "i'm not here to fix",
    "i won't give you a plan",
    "i'm not giving you a",
    "no five-step",
    "not a five-step",
    # Soft-hope loop clichés
    "hearts get wrecked",
    "hearts take hits",
    "still come back",
    "not stuck like this forever",
    "come out the other side",
    "messy, slow, but you do",
    "pain's the whole story",
    "waiting feel useless",
    "real talk",
    "one thing for right now",
    "for right now, one thing",
    "one thing only",
    "that's a real foothold",
    "one small thing for right now",
    "set a 2-minute",
    "name three things",
    "nervous system",
    "your system",
    "the system that",
    "allowed to feel again",
    "treating feeling like a threat",
    "i'm here if you want to sit",
    "i'm here if you want to talk",
    "you already know it was",
    "you already know",
    "doesn't mean you're trash",
)

_META_NEGATION_RE = re.compile(
    r"[^.!?\n]*(?:"
    r"i['']?m not (?:handing|giving|here to|going to (?:give|hand))|"
    r"not handing you|"
    r"won['']?t (?:hand|give) you (?:a )?(?:to-?do|plan|list|advice)|"
    r"no to-?do list"
    r")[^.!?\n]*[.!?…]?",
    re.I,
)


def scrub_verbal_tics(text: str) -> str:
    """Drop known formulaic / meta-negation sentences; keep the real content."""
    if not text:
        return text
    text = re.sub(r"^(?:Yeah|Yep|Right|Totally)[,.]?\s+", "", text.strip(), count=1, flags=re.I)
    text = re.sub(r"^(?:Real talk)[,—\-\s]+", "", text.strip(), count=1, flags=re.I)
    text = re.sub(r"(?i)\breal talk\s*[—\-]\s*", "", text)
    text = _META_NEGATION_RE.sub("", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    paras_out: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        sents = re.split(r"(?<=[.!?…])\s+", para.strip())
        kept = []
        for s in sents:
            s_clean = s.strip()
            if not s_clean:
                continue
            low = s_clean.lower().replace("’", "'").replace("‘", "'")
            if any(frag in low for frag in _TIC_FRAGMENTS):
                continue
            # presence-slogan closers
            if re.match(r"^i['']?m here (?:for|with)\b", low):
                continue
            if re.match(r"^i['']?m with you\b", low):
                continue
            kept.append(s_clean)
        if kept:
            paras_out.append(" ".join(kept))
    cleaned = "\n\n".join(paras_out).strip()
    if cleaned:
        return cleaned
    # Don't replay a message made only of tics/clichés
    return ""


def adjacency_hint(user_text: str) -> str:
    """Cheap speech-act hint so the model matches the conversational move."""
    t = (user_text or "").strip().lower()
    if not t:
        return ""
    if any(
        p in t
        for p in (
            "thanks",
            "thank you",
            "that landed",
            "that actually landed",
            "that helped",
            "appreciate it",
        )
    ):
        return (
            "[THIS TURN MOVE: receipt] Short acknowledgment. One beat. Stop. "
            "No summary, no new lecture."
        )
    if "?" in t or t.startswith(
        ("do you", "what do you", "why ", "how ", "am i ", "is it ", "can you")
    ):
        return (
            "[THIS TURN MOVE: question] Answer directly first in your own words. "
            "Then at most one short follow-on. No empathy preamble."
        )
    if any(
        p in t
        for p in (
            "i don't want a pep",
            "don't pep",
            "sit with",
            "just listen",
            "don't fix",
            "no advice",
        )
    ):
        return (
            "[THIS TURN MOVE: company] Stay with them in plain talk. "
            "Skip plans silently — never announce that you're skipping them."
        )
    # Default: contribution / trouble-telling
    words = len(t.split())
    if words >= 40:
        return (
            "[THIS TURN MOVE: share] Relevant next contribution (your take). "
            "Ground lightly — do not recap their story."
        )
    return (
        "[THIS TURN MOVE: chat] Jump into your thought. Match depth. No agreement-tic opener."
    )
