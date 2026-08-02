"""Understanding subroutine — real-time read of the user's state every turn."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from ..plain_language import looks_medical
from ..protocols import Protocol, classify_all
from .model import AffectSample, LivingUserModel


@dataclass
class UnderstandingSnapshot:
    protocols: List[Protocol]
    affect: AffectSample
    summary: str
    needs: List[str] = field(default_factory=list)
    extracted_preferences: List[str] = field(default_factory=list)
    extracted_avoids: List[str] = field(default_factory=list)
    extracted_triggers: List[str] = field(default_factory=list)
    extracted_strengths: List[str] = field(default_factory=list)
    extracted_grounding: List[str] = field(default_factory=list)
    help_feedback_positive: List[str] = field(default_factory=list)
    help_feedback_negative: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)


_AFFECT_RULES = [
    (
        "crisis",
        1.0,
        re.compile(
            r"\b(kill myself|suicid|want to die|self[-\s]?harm|"
            r"quiero morir|quero morrer|je veux mourir|ich will sterben)\b|"
            r"不想活|死にたい",
            re.I,
        ),
    ),
    (
        "low",
        0.85,
        re.compile(
            r"\b(hopeless|empty|numb|worthless|can't go on|cant go on|give up|"
            r"sin esperanza|sem esperança|sans espoir|hoffnungslos|"
            r"vacío|vazio|vide|entstellt|agotad[oa]|épuis[ée])\b",
            re.I,
        ),
    ),
    (
        "low",
        0.7,
        re.compile(
            r"\b(depress(?:ed|ion|ing)?|sad|alone|exhausted|drained|broken|"
            r"deprimid[oa]|triste|seul|allein|solo|só)\b",
            re.I,
        ),
    ),
    (
        "mixed",
        0.55,
        re.compile(
            r"\b(anxious|overwhelm|panic|scared|stress|worried|"
            r"ansios[oa]|ansieux|ängstlich|preocupad[oa]|inquiet)\b",
            re.I,
        ),
    ),
    (
        "rising",
        0.45,
        re.compile(
            r"\b(better|helped|thank you|grateful|hope|progress|"
            r"mejor|melhor|mieux|besser|gracias|obrigad[oa]|merci|danke)\b",
            re.I,
        ),
    ),
    (
        "calm",
        0.25,
        re.compile(
            r"\b(okay|ok for now|stable|managing|alright|"
            r"estable|estável|stable|ruhig|tranquilo)\b",
            re.I,
        ),
    ),
]

_HELPED_RE = re.compile(
    r"(?:that (?:really )?helped|that (?:was|felt) helpful|i liked when you|keep (?:doing|saying) that|"
    r"more of that|that landed|"
    r"eso (?:sí )?ayud[oó]|isso ajudou|ça m'a aidé|das hat geholfen)",
    re.I,
)
_HURT_RE = re.compile(
    r"(?:don't say|do not say|that (?:made|makes) it worse|too much advice|stop (?:pushing|fixing)|"
    r"that felt (?:cold|dismissive|patronizing)|"
    r"no digas|não diga|ne dis pas|sag das nicht|"
    r"empeor[oó]|piorou|empiré)",
    re.I,
)
_TRIGGER_RE = re.compile(
    r"(?:triggered by|trigger(?:s|ed)?(?: me)?(?: when| by|:)?\s+)(.+?)(?:[.!]|$)",
    re.I,
)
_STRENGTH_RE = re.compile(
    r"(?:i(?:'m| am) good at|my strength is|i can still|what keeps me going is)\s+(.+?)(?:[.!]|$)",
    re.I,
)
_GROUND_RE = re.compile(
    r"(?:helps when i|ground(?:ing)?(?: with| by|:)?|calms me(?: when| if)?)\s+(.+?)(?:[.!]|$)",
    re.I,
)
_PREFER_RE = re.compile(
    r"(?:please (?:just )?|i need you to |i want you to |prefer (?:when )?you )\s*(.+?)(?:[.!]|$)",
    re.I,
)


class UnderstandingSubroutine:
    """Always-on reader — classifies affect, protocols, and explicit preferences."""

    def read(
        self,
        user_text: str,
        *,
        history: Optional[Sequence[dict]] = None,
        model: Optional[LivingUserModel] = None,
    ) -> UnderstandingSnapshot:
        text = user_text or ""
        protocols = classify_all(text)
        affect = self._read_affect(text)
        needs = self._medical_needs(text, self._infer_needs(protocols, affect))
        prefs = self._extract_all(_PREFER_RE, text)
        avoids = []
        if _HURT_RE.search(text):
            # capture nearby clause
            avoids.append(self._trim(text, 120))
        triggers = self._extract_all(_TRIGGER_RE, text)
        strengths = self._extract_all(_STRENGTH_RE, text)
        grounding = self._extract_all(_GROUND_RE, text)
        pos, neg = [], []
        if _HELPED_RE.search(text):
            pos.append(self._recent_assistant_move(history) or "previous supportive move")
        if _HURT_RE.search(text):
            neg.append(self._recent_assistant_move(history) or "previous move that missed")

        gaps = self._infer_gaps(text, protocols, model)
        summary = self._summarize(text, protocols, affect, needs)

        return UnderstandingSnapshot(
            protocols=protocols,
            affect=affect,
            summary=summary,
            needs=needs,
            extracted_preferences=prefs,
            extracted_avoids=avoids,
            extracted_triggers=triggers,
            extracted_strengths=strengths,
            extracted_grounding=grounding,
            help_feedback_positive=pos,
            help_feedback_negative=neg,
            gaps=gaps,
        )

    def _read_affect(self, text: str) -> AffectSample:
        for valence, intensity, rx in _AFFECT_RULES:
            m = rx.search(text)
            if m:
                return AffectSample(
                    ts=__import__("time").time(),
                    valence=valence,
                    intensity=intensity,
                    signals=[m.group(0)],
                )
        return AffectSample(ts=__import__("time").time(), valence="unknown", intensity=0.3, signals=[])

    def _infer_needs(self, protocols: List[Protocol], affect: AffectSample) -> List[str]:
        needs: List[str] = []
        if affect.valence == "crisis":
            needs.append("safety_and_human_crisis_support")
        if Protocol.DEPRESSION in protocols or affect.valence == "low":
            needs.append("witnessing_plus_micro_agency")
        if Protocol.GRIEF in protocols:
            needs.append("grief_companionship")
        if Protocol.HEALTH in protocols:
            needs.append("health_stress_coping_without_diagnosis")
        if Protocol.MAJOR_EVENT in protocols:
            needs.append("regulate_then_one_secure_step")
        if affect.valence in {"mixed"}:
            needs.append("anxiety_grounding")
        if not needs:
            needs.append("attuned_listening")
        return needs

    def _medical_needs(self, text: str, needs: List[str]) -> List[str]:
        if looks_medical(text) and "medical_plain_language_bridge" not in needs:
            needs.append("medical_plain_language_bridge")
        return needs

    def _infer_gaps(
        self,
        text: str,
        protocols: List[Protocol],
        model: Optional[LivingUserModel],
    ) -> List[str]:
        gaps: List[str] = []
        if Protocol.DEPRESSION in protocols and (not model or not model.grounding_tools_that_work):
            gaps.append("personalized_depression_activation_tools")
        if Protocol.GRIEF in protocols and (not model or not model.successful_moves):
            gaps.append("grief_support_rituals_that_fit_this_user")
        if Protocol.HEALTH in protocols:
            gaps.append("reputable_coping_for_health_anxiety_without_diagnosis")
        if looks_medical(text):
            gaps.append("plain_language_explanations_for_clinical_terms")
            gaps.append("openmed_ner_to_everyday_words_companion_pattern")
        lowered = text.lower().replace("'", "'").replace("'", "'")
        if "i don't know" in lowered or "don't know how" in lowered or "dont know how" in lowered:
            gaps.append("stepwise_rebuild_plan_for_overwhelm")
        if affect_is_stuck(model):
            gaps.append("novel_safe_approaches_when_prior_moves_stall")
        return gaps

    def _extract_all(self, rx: re.Pattern[str], text: str) -> List[str]:
        out: List[str] = []
        for m in rx.finditer(text):
            frag = (m.group(1) if m.lastindex else m.group(0)).strip(" .,\"'")
            if frag and len(frag) < 160:
                out.append(frag)
        return out

    def _recent_assistant_move(self, history: Optional[Sequence[dict]]) -> str:
        if not history:
            return ""
        for msg in reversed(list(history)):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content.strip().split("\n")[0][:160]
        return ""

    def _summarize(
        self,
        text: str,
        protocols: List[Protocol],
        affect: AffectSample,
        needs: List[str],
    ) -> str:
        snippet = self._trim(text, 140)
        prots = ",".join(p.value for p in protocols)
        return f"affect={affect.valence}/{affect.intensity:.2f}; protocols={prots}; needs={','.join(needs)}; said≈{snippet}"

    @staticmethod
    def _trim(text: str, n: int) -> str:
        t = " ".join((text or "").split())
        return t if len(t) <= n else t[: n - 1] + "…"


def affect_is_stuck(model: Optional[LivingUserModel]) -> bool:
    if not model or len(model.affect_trajectory) < 4:
        return False
    recent = model.affect_trajectory[-4:]
    return all(r.get("valence") in {"low", "mixed", "crisis"} for r in recent)
