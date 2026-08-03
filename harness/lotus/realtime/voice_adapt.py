"""Adaptive language — grow relatability from the user's own words and memories."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from .paths import core_dir, hermes_home

if TYPE_CHECKING:
    from .model import LivingUserModel

# Words too common to treat as voice signature
_STOP = {
    "the", "and", "that", "this", "with", "have", "just", "like", "from", "they",
    "been", "were", "when", "what", "your", "about", "really", "there", "their",
    "would", "could", "should", "into", "than", "then", "them", "some", "also",
    "only", "over", "such", "after", "because", "before", "being", "which", "while",
    "will", "dont", "don't", "can't", "cant", "it's", "its", "i'm", "im", "you",
    "but", "for", "not", "are", "was", "how", "all", "any", "can", "had", "her",
    "him", "his", "she", "our", "out", "get", "got", "has", "who", "why", "yes",
    "yeah", "okay", "ok", "hey", "hi", "please", "thanks", "thank",
}

_METAPHOR_RE = re.compile(
    r"\b(?:like a |feels? like |as if |as though |drowning|weight|heavy|fog|void|"
    r"hollow|broken|shattered|stuck|sinking|numb|darkness|light|storm|wave|"
    r"tunnel|wall|cage|fire|burn(?:ing|ed)?|freeze|frozen|empty)\b[^.!?]{0,40}",
    re.I,
)

_CONNECTION_RE = re.compile(
    r"(?:my (?:mom|dad|mother|father|partner|wife|husband|kid|child|friend|dog|cat|sister|brother)|"
    r"(?:at work|my job|my boss)|(?:church|mosque|temple|pray)|(?:music|song|playlist)|"
    r"(?:walk|gym|run|game|anime|book))\b[^.!?]{0,30}",
    re.I,
)


@dataclass
class VoiceSample:
    """Features extracted from one user message."""

    phrases: List[str] = field(default_factory=list)
    metaphors: List[str] = field(default_factory=list)
    emotion_words: List[str] = field(default_factory=list)
    connection_cues: List[str] = field(default_factory=list)
    avg_sentence_len: float = 0.0
    word_count: int = 0
    formality: str = "neutral"  # casual | neutral | formal
    uses_you: bool = False
    raw_snippet: str = ""


_EMOTION_WORDS = re.compile(
    r"\b(numb|empty|heavy|scared|anxious|angry|lonely|tired|hopeless|okay|alright|"
    r"grateful|hopeful|overwhelmed|shame|guilty|lost|broken|calm|safe|hurt)\b",
    re.I,
)


def extract_voice(text: str) -> VoiceSample:
    text = (text or "").strip()
    if not text:
        return VoiceSample()

    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    lengths = [len(s.split()) for s in sentences] or [len(text.split())]
    avg_len = sum(lengths) / max(len(lengths), 1)

    formal_hits = len(re.findall(r"\b(however|therefore|regarding|furthermore|cannot)\b", text, re.I))
    casual_hits = len(re.findall(r"\b(gonna|wanna|kinda|idk|lol|tbh|imo|yeah|nah)\b", text, re.I))
    if casual_hits > formal_hits and casual_hits > 0:
        formality = "casual"
    elif formal_hits > casual_hits and formal_hits > 0:
        formality = "formal"
    else:
        formality = "neutral"

    # Distinctive content words (length >= 4, not stopwords)
    words = re.findall(r"[A-Za-z']{4,}", text.lower())
    counted = Counter(w for w in words if w not in _STOP and not w.endswith("'s"))
    phrases = [w for w, _ in counted.most_common(8)]

    metaphors = [_clean(m.group(0)) for m in _METAPHOR_RE.finditer(text)]
    emotion_words = list({m.group(0).lower() for m in _EMOTION_WORDS.finditer(text)})
    connection_cues = [_clean(m.group(0)) for m in _CONNECTION_RE.finditer(text)]

    return VoiceSample(
        phrases=phrases,
        metaphors=metaphors[:5],
        emotion_words=emotion_words[:8],
        connection_cues=connection_cues[:5],
        avg_sentence_len=avg_len,
        word_count=len(text.split()),
        formality=formality,
        uses_you=bool(re.search(r"\byou\b", text, re.I)),
        raw_snippet=_clean(text)[:160],
    )


def _clean(s: str) -> str:
    return " ".join(s.split()).strip(" .,;:")


def read_hermes_memory_snippets(*, max_chars: int = 1200) -> str:
    """Pull durable Hermes memories that deepen relatability."""
    home = hermes_home()
    chunks: List[str] = []
    for rel in (
        Path("memories") / "USER.md",
        Path("memories") / "MEMORY.md",
        Path("USER.md"),
        Path("MEMORY.md"),
    ):
        path = home / rel
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if text:
                chunks.append(f"--- {rel} ---\n{text[: max_chars // 2]}")
    # Also surface lotus VOICE.md if present
    voice_md = core_dir() / "VOICE.md"
    if voice_md.is_file():
        try:
            chunks.append("--- lotus-core/VOICE.md ---\n" + voice_md.read_text(encoding="utf-8")[:600])
        except OSError:
            pass
    joined = "\n\n".join(chunks).strip()
    return joined[:max_chars]


def adaptation_strength(turn_count: int) -> str:
    if turn_count < 3:
        return "light"  # listen more than mirror
    if turn_count < 12:
        return "growing"
    return "strong"


def build_adaptation_directive(
    model: "LivingUserModel",
    *,
    latest: Optional[VoiceSample] = None,
    memory_snippets: str = "",
) -> str:
    """Inject how to speak *with* this person — stronger as memories accumulate."""
    strength = adaptation_strength(model.turn_count)
    lines = [
        "[L.O.T.U.S. ADAPTIVE LANGUAGE — know them; still speak as yourself]",
        f"adaptation_strength={strength} (turns={model.turn_count})",
        "Use memory so your *own* reply lands better — not so you become a parrot.",
        "You may borrow at most one of their words; the rest must be Lotus voice.",
        "Never mock or caricature. Never invent shared history.",
    ]

    if model.user_phrases:
        lines.append(
            "words_they_use (optional light touch, do NOT structure your reply around these): "
            + "; ".join(model.user_phrases[-10:])
        )
    if model.user_metaphors:
        lines.append(
            "images_they've_used (don't recycle as your whole reply): "
            + "; ".join(model.user_metaphors[-8:])
        )
    if model.emotion_lexicon:
        lines.append("feelings_they've_named: " + "; ".join(model.emotion_lexicon[-10:]))
    if model.connection_anchors:
        lines.append("connection_anchors: " + "; ".join(model.connection_anchors[-10:]))
    if model.shared_moments:
        lines.append("shared_moments_to_honor: " + "; ".join(model.shared_moments[-6:]))
    if model.preferred_language:
        lines.append("requested_style: " + "; ".join(model.preferred_language[-6:]))
    if model.avoided_language:
        lines.append("never_use: " + "; ".join(model.avoided_language[-6:]))

    style = model.voice_style or {}
    if style:
        lines.append(
            "pace_hint: "
            f"formality={style.get('formality', 'neutral')}; "
            f"reply_length={style.get('reply_length', 'medium')} "
            "(match depth; keep Lotus diction)"
        )
        pattern_bits = []
        if style.get("sms_short") or style.get("reply_length") == "short":
            pattern_bits.append("prefer SMS-short")
        if style.get("hates_worksheets"):
            pattern_bits.append("no five-step worksheets")
        if style.get("hates_meta"):
            pattern_bits.append("no meta-negation")
        if style.get("soft_company"):
            pattern_bits.append("company-over-tips sometimes")
        loop = int(style.get("soft_loop_count") or 0)
        if loop >= 2:
            pattern_bits.append(f"soft_loop={loop} → escalate")
        if style.get("frequent_needs"):
            pattern_bits.append("frequent_needs=" + str(style["frequent_needs"]))
        if pattern_bits:
            lines.append("talk_pattern_prefs: " + "; ".join(pattern_bits))

    if latest and latest.raw_snippet:
        lines.append(f"this_turn_context (do not paraphrase back): {latest.raw_snippet}")

    if memory_snippets:
        lines.append("durable_memories (use for warmth, not surveillance):")
        lines.append(memory_snippets)

    if strength == "light":
        lines.append(
            "Early bond: show up as Lotus — a real take, not a mirror. Match how much they wrote."
        )
    elif strength == "growing":
        lines.append(
            "Growing bond: recall one real detail if it fits; answer in your voice; match depth."
        )
    else:
        lines.append(
            "Deep bond: continuity of *care and memory*, not of their exact wording. "
            "They should feel known — and still hear Lotus, not an echo."
        )

    lines.append(
        "Rules: respond before advising; match reply length to how much they shared; "
        "use 'we' sparingly and only when collaborative; never invent memories; "
        "if unsure, ask one gentle question in your own words."
    )
    return "\n".join(lines)


def write_voice_md(model: "LivingUserModel") -> None:
    path = core_dir() / "VOICE.md"
    lines = [
        "# L.O.T.U.S. Adaptive Voice Profile",
        "",
        f"Turns: {model.turn_count}",
        f"Adaptation: {adaptation_strength(model.turn_count)}",
        "",
        "## Their words",
        *([f"- {x}" for x in model.user_phrases[-16:]] or ["- (learning…)"]),
        "",
        "## Metaphors",
        *([f"- {x}" for x in model.user_metaphors[-12:]] or ["- (learning…)"]),
        "",
        "## Emotion lexicon",
        *([f"- {x}" for x in model.emotion_lexicon[-16:]] or ["- (learning…)"]),
        "",
        "## Connection anchors",
        *([f"- {x}" for x in model.connection_anchors[-16:]] or ["- (learning…)"]),
        "",
        "## Shared moments",
        *([f"- {x}" for x in model.shared_moments[-12:]] or ["- (none yet)"]),
        "",
        "## Style",
    ]
    style = model.voice_style or {}
    if style:
        for k, v in style.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- (learning…)")
    lines.append("")
    lines.append("## Talk pattern prefs (from talk_patterns.json)")
    if style.get("frequent_needs") or style.get("pattern_turns"):
        lines.append(f"- pattern_turns: {style.get('pattern_turns', 0)}")
        lines.append(f"- frequent_needs: {style.get('frequent_needs', '')}")
        lines.append(f"- soft_loop_count: {style.get('soft_loop_count', 0)}")
        lines.append(f"- hates_worksheets: {style.get('hates_worksheets', False)}")
        lines.append(f"- hates_meta: {style.get('hates_meta', True)}")
        lines.append(f"- soft_company: {style.get('soft_company', False)}")
    else:
        lines.append("- (learning…)")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
