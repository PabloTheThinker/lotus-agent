"""Speech stack — Gateway owns inject; patterns/EI/humanizer feed it."""

from .ei import EmotionReading, ei_block, perceive_emotions, understand_emotions
from .emotion import EmotionalStance, choose_emotional_stance, emotion_block
from .engine import (
    apply_corrections_to_model,
    brutal_truth_mode,
    build_speech_care_directive,
    extract_language_corrections,
)
from .flow import FLOW_DIRECTIVE, adjacency_hint, flow_block, scrub_verbal_tics
from .gateway import build_via_gateway, gateway_block
from .humanizer import (
    HUMANIZER_DIRECTIVE,
    cursor_length_hint,
    humanizer_block,
    length_match_directive,
    turn_depth,
    user_word_count,
)
from .moment_route import MomentRoute, moment_route_block, route_moment
from .patterns import (
    TalkPlan,
    build_talk_plan,
    learn_from_turn,
    sync_pattern_memory_to_model,
    talk_plan_block,
)
from .profiles import SpeechProfile, profiles_for
from .voice_os import VOICE_OS_DIRECTIVE, voice_os_block

__all__ = [
    "EmotionReading",
    "EmotionalStance",
    "FLOW_DIRECTIVE",
    "HUMANIZER_DIRECTIVE",
    "VOICE_OS_DIRECTIVE",
    "SpeechProfile",
    "adjacency_hint",
    "apply_corrections_to_model",
    "build_speech_care_directive",
    "brutal_truth_mode",
    "choose_emotional_stance",
    "cursor_length_hint",
    "ei_block",
    "emotion_block",
    "extract_language_corrections",
    "flow_block",
    "humanizer_block",
    "MomentRoute",
    "TalkPlan",
    "build_talk_plan",
    "build_via_gateway",
    "gateway_block",
    "learn_from_turn",
    "sync_pattern_memory_to_model",
    "length_match_directive",
    "moment_route_block",
    "perceive_emotions",
    "profiles_for",
    "route_moment",
    "scrub_verbal_tics",
    "talk_plan_block",
    "turn_depth",
    "understand_emotions",
    "user_word_count",
    "voice_os_block",
]
