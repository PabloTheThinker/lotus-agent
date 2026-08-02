"""Learning subroutine — integrate each turn into the living user model."""

from __future__ import annotations

import re
from typing import Optional

from .model import LivingUserModel
from .understanding import UnderstandingSnapshot
from .voice_adapt import VoiceSample, extract_voice

_NEXT_STEP_RE = re.compile(
    r"(?:one small step|try this|could we|would you be open to|for the next (?:few )?(?:minutes|hour))\s*[:—-]?\s*(.+?)(?:\n|$)",
    re.I,
)

_MOMENT_RE = re.compile(
    r"(?:remember when|last time|you said|we talked about|that day|anniversary|"
    r"since (?:my|the)|after (?:my|the))\s+(.+?)(?:[.!]|$)",
    re.I,
)


class LearningSubroutine:
    """Always learning what helps *this* user — including how they speak."""

    def integrate(
        self,
        model: LivingUserModel,
        snap: UnderstandingSnapshot,
        *,
        assistant_text: str = "",
        user_text: str = "",
    ) -> LivingUserModel:
        model.turn_count += 1
        model.push_affect(snap.affect)
        model.active_protocols = [p.value for p in snap.protocols]
        model.last_user_summary = snap.summary

        for item in snap.extracted_preferences:
            model.remember("preferred_language", item)
        for item in snap.extracted_avoids:
            model.remember("avoided_language", item)
        for item in snap.extracted_triggers:
            model.remember("triggers", item)
        for item in snap.extracted_strengths:
            model.remember("strengths", item)
        for item in snap.extracted_grounding:
            model.remember("grounding_tools_that_work", item)
        for item in snap.help_feedback_positive:
            model.remember("successful_moves", item)
        for item in snap.help_feedback_negative:
            model.remember("failed_moves", item)
        for gap in snap.gaps:
            model.remember("open_gaps", gap, limit=20)

        voice = extract_voice(user_text or "")
        self._integrate_voice(model, voice)

        for m in _MOMENT_RE.finditer(user_text or ""):
            frag = m.group(0).strip()[:160]
            model.remember("shared_moments", frag, limit=20)
            # Bridge into moments connection graph (best-effort)
            try:
                from lotus.moments import get_moments

                get_moments().after_turn(
                    user_text or frag,
                    "",
                    protocols=list(model.active_protocols or []),
                    affect=model.current_affect or "",
                )
            except Exception:
                pass

        if assistant_text:
            step = self._extract_next_step(assistant_text)
            if step:
                model.last_next_step = step
            if snap.affect.valence in {"rising", "calm"} and model.last_next_step:
                model.remember("successful_moves", f"step_context:{model.last_next_step[:120]}")
            # When user said something helped, bind it to relatability
            if snap.help_feedback_positive:
                model.remember(
                    "relatability_notes",
                    "Mirror their words more; keep the tone that landed last turn.",
                    limit=12,
                )

        if "P1_depression" in model.active_protocols and not model.hypotheses:
            model.hypotheses.append(
                "Low approach motivation may respond better to tiny activation than insight dumps."
            )
        if "P3_grief" in model.active_protocols:
            model.remember(
                "hypotheses",
                "Grief may need witnessing and continuing bonds more than problem-solving.",
            )

        model.touch()
        return model

    def _integrate_voice(self, model: LivingUserModel, voice: VoiceSample) -> None:
        for p in voice.phrases:
            model.remember("user_phrases", p, limit=40)
        for m in voice.metaphors:
            model.remember("user_metaphors", m, limit=24)
        for e in voice.emotion_words:
            model.remember("emotion_lexicon", e, limit=30)
        for c in voice.connection_cues:
            model.remember("connection_anchors", c, limit=24)

        # Running average sentence length + formality / reply length hint.
        # Prefer total share size (words this turn) over avg sentence length alone —
        # a long paragraph of short sentences is still a long share.
        prev = float(model.voice_style.get("avg_sentence_len") or voice.avg_sentence_len or 12)
        blended = (prev * 0.7) + (voice.avg_sentence_len * 0.3) if voice.avg_sentence_len else prev
        turn_words = int(voice.word_count or 0)
        if turn_words >= 55 or blended > 22:
            reply_length = "long"
        elif turn_words >= 20 or blended >= 10:
            reply_length = "medium"
        else:
            reply_length = "short"
        # Formality: prefer latest non-neutral signal, else keep prior
        formality = voice.formality
        if formality == "neutral" and model.voice_style.get("formality"):
            formality = str(model.voice_style.get("formality"))
        model.voice_style = {
            "avg_sentence_len": round(blended, 1),
            "formality": formality,
            "reply_length": reply_length,
            "last_turn_words": turn_words,
        }

    def _extract_next_step(self, assistant_text: str) -> Optional[str]:
        m = _NEXT_STEP_RE.search(assistant_text or "")
        if m:
            return m.group(1).strip()[:200]
        for line in (assistant_text or "").splitlines():
            s = line.strip()
            if 20 <= len(s) <= 160 and s.endswith("?"):
                return s
        return None
