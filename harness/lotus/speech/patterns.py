"""Pattern recognition + unified Talk Plan for Lotus companion speech.

One workflow owns the turn:
  recognize → pick need → (optional hard-truth / way-out) → SMS shape → ONE move

Learns per person in talk_patterns.json (anti-repeat phrases, loop count, prefs).
Compound / mission feed a single foothold line when the need is way_out — not a
separate competing essay from Voice/EI/Flow.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Pattern library
# ---------------------------------------------------------------------------

_PATTERN_RULES: list[tuple[str, float, re.Pattern[str]]] = [
    (
        "friend_shock",
        1.9,
        re.compile(
            r"\b(?:oh+ ?my ?god|omg|oh no|holy shit|what the (?:fuck|hell)|"
            r"my (?:mom|dad|mum|sister|brother|wife|husband|kid|friend).{0,40}"
            r"(?:hospital|er\b|icu|ambulance|emergency)|"
            r"(?:just )?(?:got|found|heard).{0,30}(?:bad|terrible|awful)|"
            r"something (?:bad|terrible|awful) happened|"
            r"in the hospital)\b",
            re.I,
        ),
    ),
    (
        "need_way_out",
        1.7,
        re.compile(
            r"\b(?:don'?t know how (?:people )?get out|how (?:do|does|can) (?:people|i|anyone).{0,20}get out|"
            r"way out|get out of (?:this|it|the dark)|what'?s even the point|"
            r"point of waiting|how do i (?:fix|change|move)|"
            r"stuck in (?:a |this )?loop|keep (?:ending|coming) back|"
            r"give me something|what (?:do i|should i) do|"
            r"help me (?:out|through)|need (?:a )?(?:plan|path|way))\b",
            re.I,
        ),
    ),
    (
        "need_reassurance",
        1.4,
        re.compile(
            r"\b(?:am i (?:just )?broken|is (?:that|this) (?:normal|wrong)|"
            r"never (?:feel|be) (?:okay|better|myself)|won'?t get (?:better|through)|"
            r"don'?t (?:want to )?feel anymore|can'?t feel|"
            r"what'?s wrong with me|i'?m broken)\b",
            re.I,
        ),
    ),
    (
        "need_company",
        1.3,
        re.compile(
            r"\b(?:don'?t want advice|no advice|just listen|don'?t fix|"
            r"don'?t (?:turn|make) (?:it|this) into|not a five.?step|"
            r"talk to me like a person|just talk|stay with)\b",
            re.I,
        ),
    ),
    (
        "need_answer",
        1.2,
        re.compile(r"\?", re.I),
    ),
    (
        "need_receipt",
        1.5,
        re.compile(
            r"\b(?:that (?:kinda |actually )?landed|that helped|thank(?:s| you)|"
            r"appreciate (?:it|that))\b",
            re.I,
        ),
    ),
    (
        "closed_off",
        1.1,
        re.compile(
            r"\b(?:idk|i don'?t know|whatever|nvm|never ?mind|fine\.|"
            r"doesn'?t matter|leave me alone)\b",
            re.I,
        ),
    ),
    (
        "numb_dark",
        1.2,
        re.compile(
            r"\b(?:numb|empty|flat|hollow|hallway|in the dark|"
            r"watching (?:my|myself)|dissociat|checked out|shut down|"
            r"closed off|don'?t feel)\b",
            re.I,
        ),
    ),
    (
        "heartbreak_storm",
        1.2,
        re.compile(
            r"\b(?:heart'?s? broken|broken heart|storm inside|falling apart|"
            r"can'?t stop (?:crying|thinking)|miss (?:him|her|them)|"
            r"they left|dumped|grief|died|funeral)\b",
            re.I,
        ),
    ),
    (
        "anxiety_spiral",
        1.1,
        re.compile(
            r"\b(?:panic|anxious|spiral|can'?t (?:calm|breathe|sleep)|"
            r"racing thoughts|worried sick|overthinking)\b",
            re.I,
        ),
    ),
    (
        "bad_choice",
        1.55,
        re.compile(
            r"\b(?:fucked up|texted my ex|left (?:me )?on read|shouldn'?t have|"
            r"did it anyway|feel so stupid|so stupid|replaying every word)\b",
            re.I,
        ),
    ),
    (
        "intoxicated",
        1.6,
        re.compile(
            r"\b(?:i(?:'m| am| was| got)|i've been)\s+"
            r"(?:drunk|wasted|hammered|tipsy|high|stoned|blacked out)\b|"
            r"\b(?:drank too much|too many drinks)\b",
            re.I,
        ),
    ),
    (
        "shame",
        1.0,
        re.compile(
            r"\b(?:ashamed|embarrass|pathetic|worthless|everyone (?:saw|thinks)|"
            r"lying by existing|fake|what'?s wrong with me)\b",
            re.I,
        ),
    ),
    (
        "acute_heat",
        2.0,
        re.compile(
            r"\b(?:want to (?:hit|smash|hurt)|losing it|about to|"
            r"kill myself|suicid|911|unresponsive|overdose)\b",
            re.I,
        ),
    ),
]

# Phrases that became a soft-hope / script loop — ban recycling
_CLICHE_BANK: tuple[str, ...] = (
    "hearts get wrecked",
    "hearts take hits",
    "still come back",
    "not stuck like this forever",
    "doesn't mean you stay",
    "you stay there forever",
    "come out the other side",
    "messy, slow, but you do",
    "it gets lighter",
    "slow and ugly",
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
)


@dataclass
class PatternHit:
    name: str
    weight: float
    evidence: str = ""


@dataclass
class TalkPlan:
    need: str
    domain: str
    reply_shape: str
    max_sentences: int
    include_ei_detail: bool
    hits: List[str] = field(default_factory=list)
    learned: List[str] = field(default_factory=list)
    move: str = ""
    banned: List[str] = field(default_factory=list)
    way_out_line: str = ""
    intensity: str = "steady"  # soft | steady | hard | shock


@dataclass
class TalkPatternMemory:
    version: int = 1
    updated_at: float = 0.0
    turn_count: int = 0
    need_counts: Dict[str, int] = field(default_factory=dict)
    domain_counts: Dict[str, int] = field(default_factory=dict)
    move_success: Dict[str, int] = field(default_factory=dict)
    move_fail: Dict[str, int] = field(default_factory=dict)
    prefers_short: bool = False
    hates_meta: bool = True
    hates_worksheets: bool = False  # five-step dumps — ONE way-out still OK
    hates_lecture: bool = False  # don't lecture / no interrogation
    soft_company: bool = False  # this thread asked for company recently
    likes_reassurance_path: bool = True
    soft_loop_count: int = 0
    last_need: str = ""
    last_move: str = ""
    recent_phrases: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def bump(self, bucket: Dict[str, int], key: str, n: int = 1) -> None:
        bucket[key] = int(bucket.get(key, 0)) + n

    def remember_note(self, note: str, *, limit: int = 24) -> None:
        note = (note or "").strip()
        if not note:
            return
        if note in self.notes:
            self.notes.remove(note)
        self.notes.append(note)
        if len(self.notes) > limit:
            self.notes = self.notes[-limit:]

    def remember_phrases(self, phrases: List[str], *, limit: int = 30) -> None:
        for p in phrases:
            p = p.strip().lower()
            if len(p) < 12:
                continue
            if p in self.recent_phrases:
                self.recent_phrases.remove(p)
            self.recent_phrases.append(p)
        if len(self.recent_phrases) > limit:
            self.recent_phrases = self.recent_phrases[-limit:]


def _memory_path() -> Path:
    try:
        from lotus.realtime.paths import hermes_home

        return Path(hermes_home()) / "memories" / "lotus-core" / "talk_patterns.json"
    except Exception:
        return Path.home() / ".hermes" / "memories" / "lotus-core" / "talk_patterns.json"


def load_pattern_memory() -> TalkPatternMemory:
    path = _memory_path()
    if not path.is_file():
        return TalkPatternMemory(updated_at=time.time())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return TalkPatternMemory(
            version=int(data.get("version", 1)),
            updated_at=float(data.get("updated_at") or 0),
            turn_count=int(data.get("turn_count") or 0),
            need_counts=dict(data.get("need_counts") or {}),
            domain_counts=dict(data.get("domain_counts") or {}),
            move_success=dict(data.get("move_success") or {}),
            move_fail=dict(data.get("move_fail") or {}),
            prefers_short=bool(data.get("prefers_short", False)),
            hates_meta=bool(data.get("hates_meta", True)),
            hates_worksheets=bool(
                data.get("hates_worksheets", data.get("hates_plans", False))
            ),
            hates_lecture=bool(data.get("hates_lecture", False)),
            soft_company=bool(data.get("soft_company", False)),
            likes_reassurance_path=bool(data.get("likes_reassurance_path", True)),
            soft_loop_count=int(data.get("soft_loop_count") or 0),
            last_need=str(data.get("last_need") or ""),
            last_move=str(data.get("last_move") or ""),
            recent_phrases=list(data.get("recent_phrases") or []),
            notes=list(data.get("notes") or []),
        )
    except Exception:
        return TalkPatternMemory(updated_at=time.time())


def save_pattern_memory(mem: TalkPatternMemory) -> None:
    path = _memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    mem.updated_at = time.time()
    path.write_text(json.dumps(asdict(mem), indent=2) + "\n", encoding="utf-8")


def recognize_hits(user_text: str) -> List[PatternHit]:
    text = user_text or ""
    hits: List[PatternHit] = []
    for name, weight, pat in _PATTERN_RULES:
        m = pat.search(text)
        if m:
            hits.append(PatternHit(name=name, weight=weight, evidence=m.group(0)[:48]))
    n = len(text.split())
    if n <= 12:
        hits.append(PatternHit("len_short", 0.8, f"{n}w"))
    elif n >= 55:
        hits.append(PatternHit("len_long", 0.8, f"{n}w"))
    else:
        hits.append(PatternHit("len_medium", 0.5, f"{n}w"))
    return hits


def compound_way_out_line() -> str:
    """Path angle to talk through — not a homework assignment."""
    try:
        from lotus.compound import get_compound

        mission = get_compound().state.active()
        if mission:
            meter = mission.meter
            rung = mission.current_ladder_rung or "body"
            return (
                f"Talk through a way out in plain life-language "
                f"(long arc, rung≈{rung}, horizon≈{meter.estimated_horizon}): "
                "how people actually get less stuck — someone safe to be honest with, "
                "days that get a little less heavy, not a flip switch. "
                "No nervous-system lecture. No homework."
            )
    except Exception:
        pass
    return (
        "Talk through how people leave this dark in ordinary words: slow, uneven, "
        "honest moments, someone who stays. Example + reason. No body-science. No homework."
    )


def _pick_need(hits: List[PatternHit], mem: TalkPatternMemory) -> tuple[str, str]:
    """Return (need, intensity)."""
    names = {h.name for h in hits}
    scores: Dict[str, float] = {}

    map_need = {
        "friend_shock": "friend_shock",
        "need_way_out": "way_out",
        "need_reassurance": "reassure",
        "need_company": "company",
        "need_answer": "answer",
        "need_receipt": "receipt",
        "closed_off": "sit",
        "numb_dark": "reassure",
        "heartbreak_storm": "reassure",
        "anxiety_spiral": "sit",
        "bad_choice": "company",  # stupid choice night → friend listen
        "intoxicated": "company",  # stated drunk/high → stay in that moment
        "shame": "company",
        "acute_heat": "acute",
    }
    for h in hits:
        need = map_need.get(h.name)
        if need:
            scores[need] = scores.get(need, 0.0) + h.weight

    # Hard priority: shock / acute / way_out beat soft company
    if "friend_shock" in scores:
        return "friend_shock", "shock"
    if "acute" in scores:
        return "acute", "hard"
    # Stated intoxication: stay present (MHFA) — company/listen, not lecture spiral
    if "intoxicated" in names and "way_out" not in scores:
        return "company", "steady"
    if "way_out" in scores:
        # Soft loop + asking for a way out → hard truth + path
        if mem.soft_loop_count >= 2:
            return "hard_path", "hard"
        return "way_out", "steady"
    if "receipt" in scores:
        return "receipt", "soft"

    # Depression soft-hope loop without new info → escalate
    looping = mem.soft_loop_count >= 2 and (
        "reassure" in scores or "numb_dark" in names or "shame" in names
    )
    if looping and "company" not in scores:
        return "hard_path", "hard"

    if mem.likes_reassurance_path and "reassure" in scores:
        scores["reassure"] = scores.get("reassure", 0) + 0.25
    # company only wins if they asked AND no way_out (already handled)
    if mem.soft_company and "company" in scores:
        scores["company"] += 0.35

    if not scores:
        return "witness", "steady"
    need = max(scores.keys(), key=lambda k: scores[k])
    intensity = "soft" if need in {"receipt", "sit", "company"} else "steady"
    return need, intensity


def _pick_domain(hits: List[PatternHit], protocols: Sequence[str], need: str) -> str:
    if need in {"acute", "friend_shock"}:
        return "acute" if need == "acute" else "shock"
    names = {h.name for h in hits}
    if "heartbreak_storm" in names or any("grief" in p.lower() for p in protocols):
        return "grief"
    if "anxiety_spiral" in names:
        return "anxiety"
    return "mental_health"


def _pick_shape(need: str, mem: TalkPatternMemory, word_count: int) -> tuple[str, int]:
    """Medium route — not essay, not telegram."""
    if need == "friend_shock":
        return "sms_burst", 3
    if need in {"receipt", "sit"} or mem.prefers_short:
        return "sms_short", 3
    if need in {"way_out", "hard_path"}:
        return "sms_medium", 5  # talk-through, still medium
    if need == "answer":
        return "sms_short", 3
    if need == "company":
        return "sms_short", 3
    if need == "reassure":
        return "sms_short", 4
    if word_count <= 15:
        return "sms_short", 3
    return "sms_medium", 4


def _banned_for_turn(mem: TalkPatternMemory) -> List[str]:
    banned = list(_CLICHE_BANK)
    banned.extend(mem.recent_phrases[-12:])
    # de-dupe preserve order
    seen = set()
    out = []
    for b in banned:
        k = b.lower()
        if k not in seen:
            seen.add(k)
            out.append(b)
    return out[:20]


def _move_text(
    need: str,
    domain: str,
    mem: TalkPatternMemory,
    *,
    way_out_line: str,
    intensity: str,
) -> str:
    learned = []
    if mem.hates_worksheets:
        learned.append("No five-step worksheets — ONE concrete thing max.")
    if mem.prefers_short:
        learned.append("Keep it SMS-short.")
    if mem.notes:
        learned.append("Notes: " + "; ".join(mem.notes[-3:]))

    moves = {
        "friend_shock": (
            "MOVE: best-friend SMS. Short bursts. Match their jolt. "
            'Vary it — not always "ok ok". Ask what happened. No tasks.'
        ),
        "way_out": (
            "MOVE: show a way out by talking them through it. "
            "Honesty about the long crawl. Reasons. A concrete example of how people "
            "actually leave this hole — while you stay in the chat with them. "
            "FORBIDDEN: timers, 'one thing for right now', notes-app homework, task stuffing. "
            "Fresh vocabulary. Never open with 'Real talk'."
        ),
        "hard_path": (
            "MOVE: raw truth + talk-through path. Soft hope has been looping — hit harder. "
            "Waiting can feel pointless; the stretch is long; that's the truth. "
            "Then walk them through how the dark loosens for real people (examples/reasons). "
            "No homework. No 'Real talk'. No recycled lines."
        ),
        "reassure": (
            "MOVE: honest reassurance — not empty comfort. Answer straight. "
            "If 'what's wrong with me' after a bad choice: be real about the choice "
            "without calling them broken. Ask into it. Don't medical-card it."
        ),
        "company": (
            "MOVE: realistic friend grounded ONLY in their words. "
            "Name what they actually said they did → ask why / what hit → one honest take. "
            "Example energy: 'Okay I get what you did. Why'd you hit send?' "
            "If they said drunk/high/crying — USE that; stay in that moment. "
            "NEVER invent drunk/high/crying/cheating/etc. if they didn't say it. "
            "NOT: 'you already know' / 'I'm here if you want to sit' / soft absolution. "
            "Truthful. Human. Friend — not a judge inventing a scene."
        ),
        "answer": (
            "MOVE: answer first in plain words. If they asked 'am I broken?' — say no/yes clearly. "
            "Do NOT explain their nervous system or 'the system.' One short follow beat max."
        ),
        "receipt": "MOVE: short receipt. Stop.",
        "sit": "MOVE: closed-off — short. Don't pry.",
        "witness": "MOVE: witness + one honest take. Fresh language.",
        "acute": "MOVE: acute — short, clear, safety first. Still Lotus.",
    }
    base = moves.get(need, moves["witness"])
    if way_out_line and need in {"way_out", "hard_path"}:
        base += f"\nPATH ANGLE (talk through, don't assign): {way_out_line}"
    if intensity == "hard":
        base += " Intensity=HARD — truth over comfort padding."
    if intensity == "shock":
        base += " Intensity=SHOCK — friend SMS bursts."
    if domain == "mental_health":
        base += " Domain: mental/emotional health — direct, pattern-aware."
    if learned:
        base += " LEARNED: " + " ".join(learned)
    return base


def build_talk_plan(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
    memory: Optional[TalkPatternMemory] = None,
) -> TalkPlan:
    mem = memory or load_pattern_memory()
    hits = recognize_hits(user_text)
    if crisis or affect == "crisis":
        hits.append(PatternHit("acute_heat", 3.0, "crisis_flag"))

    need, intensity = _pick_need(hits, mem)
    domain = _pick_domain(hits, protocols or [], need)
    words = len((user_text or "").split())
    shape, max_sents = _pick_shape(need, mem, words)

    way_out = ""
    if need in {"way_out", "hard_path"}:
        way_out = compound_way_out_line()

    # EI skim only when it won't fight a clear SMS move
    include_ei = need in {"reassure", "witness", "answer"} and domain not in {
        "acute",
        "shock",
    }

    banned = _banned_for_turn(mem)
    move = _move_text(
        need, domain, mem, way_out_line=way_out, intensity=intensity
    )

    return TalkPlan(
        need=need,
        domain=domain,
        reply_shape=shape,
        max_sentences=max_sents,
        include_ei_detail=include_ei,
        hits=[h.name for h in hits if not h.name.startswith("len_")],
        learned=mem.notes[-3:],
        move=move,
        banned=banned,
        way_out_line=way_out,
        intensity=intensity,
    )


def talk_plan_block(plan: TalkPlan) -> str:
    shape_line = {
        "sms_burst": (
            f"LENGTH: ~{plan.max_sentences} short bursts max. "
            "Best-friend texting — fragments OK. Not a paragraph."
        ),
        "sms_short": (
            f"LENGTH: ~{plan.max_sentences} sentences max. SMS/Messenger energy."
        ),
        "sms_medium": (
            f"LENGTH: up to ~{plan.max_sentences} sentences. Still one human text, not an essay."
        ),
        "sms_long": (
            f"LENGTH: up to ~{plan.max_sentences} sentences. Chat, not a paper."
        ),
    }.get(plan.reply_shape, f"LENGTH: ~{plan.max_sentences} sentences.")

    banned = plan.banned[:10]
    banned_line = (
        "ANTI-REPEAT — do NOT reuse these (already used or cliché): "
        + "; ".join(banned)
        if banned
        else "ANTI-REPEAT: invent fresh language every turn."
    )

    return "\n".join(
        [
            "[L.O.T.U.S. TALK PLAN — unified workflow · one voice]",
            "You are their sharp best friend over text for mental/emotional health — "
            "someone to talk to in the dark who can also hand them a real way out when they need one.",
            f"need={plan.need} domain={plan.domain} shape={plan.reply_shape} "
            f"intensity={plan.intensity}",
            f"patterns_hit={', '.join(plan.hits) or 'general'}",
            shape_line,
            plan.move,
            banned_line,
            "FRIEND SMS RULES:",
            "- Best-friend character texting. Fresh grammar. No script openers.",
            "- Way out = talk them through it (reasons/examples). Not a task.",
            "- Never 'Real talk'. Never 'one thing for right now'. Never timers-as-homework.",
            "- If they say no — drop it. If they say too slow — punch up.",
            'GOOD way-out: walk them through how the dark actually loosens, in conversation.',
            "BAD: Real talk + micro-task. BAD: same soft hope twice.",
        ]
    )


def _extract_phrase_fingerprints(assistant_text: str) -> List[str]:
    text = (assistant_text or "").lower()
    found = []
    for c in _CLICHE_BANK:
        if c in text:
            found.append(c)
    # Also keep distinctive 6+ word spans from first sentences
    for sent in re.split(r"[.!?]+", assistant_text or ""):
        words = sent.strip().split()
        if 6 <= len(words) <= 14:
            found.append(" ".join(words).lower()[:80])
            break
    return found


def sync_pattern_memory_to_model(model: object, mem: Optional[TalkPatternMemory] = None) -> TalkPatternMemory:
    """Push talk_patterns.json prefs into LivingUserModel so adaptive/living injects see them.

    Hermes models only "use everything" when pattern learning lands in the same
    living model / VOICE.md surface that every turn already injects.
    """
    mem = mem or load_pattern_memory()
    style = dict(getattr(model, "voice_style", None) or {})
    if mem.prefers_short:
        style["reply_length"] = "short"
        style["sms_short"] = True
    style["hates_meta"] = bool(mem.hates_meta)
    style["hates_worksheets"] = bool(mem.hates_worksheets)
    style["hates_lecture"] = bool(mem.hates_lecture)
    style["soft_company"] = bool(mem.soft_company)
    style["soft_loop_count"] = int(mem.soft_loop_count or 0)
    style["pattern_last_need"] = mem.last_need or ""
    style["pattern_turns"] = int(mem.turn_count or 0)
    if mem.need_counts:
        top = sorted(mem.need_counts.items(), key=lambda x: -x[1])[:3]
        style["frequent_needs"] = ",".join(f"{k}:{v}" for k, v in top)
    if hasattr(model, "voice_style"):
        model.voice_style = style  # type: ignore[attr-defined]

    remember = getattr(model, "remember", None)
    if callable(remember):
        if mem.hates_worksheets:
            remember("avoided_language", "five-step worksheet dumps", limit=24)
        if mem.hates_meta:
            remember("avoided_language", "meta-negation about advice", limit=24)
        if mem.hates_lecture:
            remember("preferred_language", "no lectures — statements when refused", limit=24)
        if mem.prefers_short:
            remember("preferred_language", "short SMS-length replies", limit=24)
        if mem.soft_company:
            remember("preferred_language", "company / listen first sometimes", limit=24)
        if mem.soft_loop_count >= 2:
            remember(
                "failed_moves",
                "soft-hope loop — escalate hard truth + one path",
                limit=20,
            )
        for note in mem.notes[-3:]:
            remember("relatability_notes", f"pattern:{note}", limit=12)
    return mem


def learn_from_turn(
    user_text: str,
    assistant_text: str,
    *,
    plan: Optional[TalkPlan] = None,
) -> TalkPatternMemory:
    mem = load_pattern_memory()
    mem.turn_count += 1
    plan = plan or build_talk_plan(user_text, memory=mem)

    mem.bump(mem.need_counts, plan.need)
    mem.bump(mem.domain_counts, plan.domain)
    prev_need = mem.last_need
    mem.last_need = plan.need
    mem.last_move = plan.need

    # Soft-hope loop tracker
    soft_needs = {"reassure", "witness", "company"}
    if plan.need in soft_needs and prev_need in soft_needs:
        mem.soft_loop_count += 1
    elif plan.need in {"way_out", "hard_path", "friend_shock"}:
        mem.soft_loop_count = 0
    elif plan.need == "receipt":
        pass
    else:
        mem.soft_loop_count = max(0, mem.soft_loop_count - 1)

    mem.remember_phrases(_extract_phrase_fingerprints(assistant_text))

    low = (user_text or "").lower()
    if any(
        p in low
        for p in ("that landed", "that helped", "kinda landed", "thank", "appreciate")
    ):
        mem.bump(mem.move_success, mem.last_move or plan.need)
        mem.likes_reassurance_path = True
        mem.soft_loop_count = 0

    # Company preference is soft; worksheets are hard-ban
    if any(
        p in low
        for p in (
            "don't want advice",
            "no advice",
            "just listen",
            "just talk to me",
            "talk to me like a person",
            "stay with",
        )
    ):
        mem.soft_company = True
        mem.remember_note("sometimes wants company over tips")

    if any(p in low for p in ("five step", "five-step", "don't fix", "not a worksheet")):
        mem.hates_worksheets = True
        mem.remember_note("hates five-step worksheets — ONE path OK")

    if any(
        p in low
        for p in (
            "don't lecture",
            "dont lecture",
            "no lecture",
            "don't wanna hear",
            "dont wanna hear",
            "don't want a lecture",
            "please don't lecture",
            "please dont lecture",
            "without the lecture",
        )
    ):
        mem.hates_lecture = True
        mem.soft_company = True
        mem.remember_note("hates lectures — statements only when refused")

    # Asking for a way out clears soft-company veto for path-giving
    if any(
        p in low
        for p in (
            "get out",
            "way out",
            "what's even the point",
            "what do i do",
            "help me out",
        )
    ):
        mem.soft_company = False
        mem.remember_note("asked for a way out — give a real path")

    if any(p in low for p in ("too long", "shorter", "less paragraphs", "just say it")):
        mem.prefers_short = True

    uw = len((user_text or "").split())
    aw = len((assistant_text or "").split())
    if uw > 0 and aw > max(40, uw * 2.2):
        mem.bump(mem.move_fail, "too_long")
        if mem.move_fail.get("too_long", 0) >= 2:
            mem.prefers_short = True

    alow = (assistant_text or "").lower()
    if any(
        p in alow
        for p in (
            "not handing you",
            "i'm not here to",
            "no to-do",
            "not going to give you advice",
        )
    ):
        mem.hates_meta = True
        mem.bump(mem.move_fail, "meta_negation")

    # Detect recycled clichés in our own mouth
    for c in _CLICHE_BANK:
        if c in alow:
            mem.bump(mem.move_fail, "cliche_loop")
            mem.remember_note(f"stop recycling: {c}")

    save_pattern_memory(mem)
    return mem


def pattern_memory_directive(mem: Optional[TalkPatternMemory] = None) -> str:
    mem = mem or load_pattern_memory()
    if mem.turn_count < 1 and not mem.notes:
        return ""
    bits = [f"[PATTERN MEMORY — {mem.turn_count} turns · loop={mem.soft_loop_count}]"]
    if mem.need_counts:
        top = sorted(mem.need_counts.items(), key=lambda x: -x[1])[:3]
        bits.append("frequent needs: " + ", ".join(f"{k}×{v}" for k, v in top))
    if mem.soft_loop_count >= 2:
        bits.append("SOFT LOOP DETECTED — escalate: hard truth + one path, new language")
    if mem.prefers_short:
        bits.append("prefer SMS-short")
    if mem.hates_worksheets:
        bits.append("no five-step worksheets (one path OK)")
    if mem.hates_lecture:
        bits.append("hates lectures — ZERO questions when they refuse")
    if mem.soft_company:
        bits.append("recently wanted company — still give path if they ask how to get out")
    if mem.notes:
        bits.append("notes: " + "; ".join(mem.notes[-3:]))
    return "\n".join(bits)
