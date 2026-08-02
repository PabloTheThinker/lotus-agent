"""Medical → everyday language helpers for the L.O.T.U.S. realtime core.

Grounded in CDC plain-language practice and optional OpenMed (local NER/PII).
Falls back to a seed glossary when OpenMed is not installed. Not a diagnostic engine.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Seed glossary (everyday alternatives). Expand via research pulse / living model.
_GLOSSARY: Dict[str, str] = {
    "hypertension": "high blood pressure",
    "hypotension": "low blood pressure",
    "myocardial infarction": "heart attack",
    "cerebrovascular accident": "stroke",
    "dyspnea": "shortness of breath",
    "edema": "swelling",
    "tachycardia": "fast heart rate",
    "bradycardia": "slow heart rate",
    "nausea": "feeling like you might throw up",
    "emesis": "vomiting",
    "fatigue": "deep tiredness",
    "insomni": "trouble sleeping",  # prefix match via custom
    "anemia": "low red blood cells / low iron-related energy in many cases — ask your clinician what it means for you",
    "benign": "not cancer (in many medical contexts — confirm with your clinician)",
    "malignant": "cancerous (confirm with your clinician)",
    "idiopathic": "the cause is not known yet",
    "prophylaxis": "something done to help prevent a problem",
    "contraindication": "a reason not to use a treatment",
    "comorbidity": "another health condition someone also has",
    "chronic": "long-lasting / ongoing",
    "acute": "sudden or short-term",
    "inflammation": "the body's swelling/irritation response",
    "lesion": "an area of tissue that looks or feels abnormal",
    "biopsy": "taking a small sample of tissue to look at more closely",
    "prognosis": "the likely course of a condition over time",
    "etiology": "the cause or origin",
    "auscultation": "listening to the body with a stethoscope",
    "prn": "as needed",
    "npo": "nothing by mouth",
    "bid": "twice a day",
    "tid": "three times a day",
    "qhs": "at bedtime",
    "stat": "right away",
    "referral": "sending you to another clinician or specialist",
    "differential diagnosis": "the list of possible explanations a clinician is considering",
}

_MED_SIGNAL = re.compile(
    r"\b("
    r"diagnosis|diagnosed|prescription|mg\b|mcg\b|lab results?|bloodwork|"
    r"discharge|clinical|pathology|radiology|hypertension|dyspnea|"
    r"myocardial|biopsy|prognosis|comorbid|contraindicat|idiopathic|"
    r"CBC|BMP|A1C|HbA1c|MRI|CT scan|ultrasound|echocardiogram|"
    r"NPO|PRN|BID|TID|qHS|STAT"
    r")\b",
    re.I,
)


def looks_medical(text: str) -> bool:
    if not text:
        return False
    if _MED_SIGNAL.search(text):
        return True
    tokens = re.findall(r"[A-Za-z]{8,}", text)
    latinish = [
        t for t in tokens if re.search(r"(tion|osis|itis|emia|pathy|ectomy|ology)$", t, re.I)
    ]
    return len(latinish) >= 2


def glossary_hits(text: str) -> List[Tuple[str, str]]:
    lowered = (text or "").lower()
    hits: List[Tuple[str, str]] = []
    for term, plain in sorted(_GLOSSARY.items(), key=lambda kv: -len(kv[0])):
        if term.endswith("i") and term == "insomni":
            if re.search(r"\binsomnia\b", lowered):
                hits.append(("insomnia", "trouble sleeping"))
            continue
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            hits.append((term, plain))
    return hits


def _openmed_enabled() -> bool:
    return os.environ.get("LOTUS_OPENMED_DISABLE", "").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }


def try_openmed(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort OpenMed structure pass. Returns None if unavailable/fails.

    Never raises — privacy and resilience beat hard dependency.
    """
    if not text or not _openmed_enabled():
        return None
    try:
        import openmed  # type: ignore
    except ImportError:
        return None

    result: Dict[str, Any] = {"backend": "openmed", "entities": [], "redacted": None}
    try:
        if hasattr(openmed, "deidentify"):
            redacted = openmed.deidentify(text)
            if isinstance(redacted, str):
                result["redacted"] = redacted
            elif isinstance(redacted, dict):
                result["redacted"] = redacted.get("text") or redacted.get("redacted")
                ents = redacted.get("entities") or redacted.get("pii") or []
                if isinstance(ents, list):
                    result["entities"].extend(ents[:24])
        if hasattr(openmed, "analyze_text"):
            analysis = openmed.analyze_text(text)
            if isinstance(analysis, dict):
                ents = analysis.get("entities") or analysis.get("ner") or []
                if isinstance(ents, list):
                    result["entities"].extend(ents[:24])
            elif isinstance(analysis, list):
                result["entities"].extend(analysis[:24])
        elif hasattr(openmed, "extract_entities"):
            ents = openmed.extract_entities(text)
            if isinstance(ents, list):
                result["entities"].extend(ents[:24])
    except Exception as exc:  # noqa: BLE001
        logger.debug("OpenMed call failed; falling back to glossary: %s", exc)
        return None

    # Normalize entity labels for prompt readability
    labels: List[str] = []
    for ent in result["entities"]:
        if isinstance(ent, str):
            labels.append(ent)
        elif isinstance(ent, dict):
            label = ent.get("text") or ent.get("entity") or ent.get("label") or ent.get("type")
            if label:
                labels.append(str(label))
    result["labels"] = labels[:16]
    if not result["labels"] and not result["redacted"]:
        return None
    return result


def plain_language_directive(text: str) -> str:
    """Context block injected when medical language is detected."""
    hits = glossary_hits(text)
    openmed = try_openmed(text)
    lines = [
        "[L.O.T.U.S. MEDICAL → NATURAL LANGUAGE BRIDGE]",
        "Mission refocus: translate medical language into calm, everyday words.",
        "Foundations: OpenMed (optional local NER/PII) + CDC Everyday Words / plain language.",
        "Rules: short sentences; define jargon once; no diagnosing; no dosing; emergencies → emergency care.",
        "Prefer MedlinePlus/CDC/NIH when looking up a term. Follow skills/lotus/medical-plain-language.",
    ]
    if openmed:
        lines.append("OpenMed structure pass: available locally.")
        labels = openmed.get("labels") or []
        if labels:
            lines.append("Entities / concepts to explain in everyday words:")
            for label in labels:
                lines.append(f"  • {label}")
        if openmed.get("redacted"):
            lines.append(
                "PII-aware note: prefer discussing structure without repeating identifiers."
            )
    else:
        lines.append(
            "OpenMed not installed or disabled — using seed glossary + plain-language rules."
        )
    if hits:
        lines.append("Seed glossary hits in this message:")
        for term, plain in hits[:12]:
            lines.append(f"  • {term} → {plain}")
    lines.append(
        "Output shape: everyday meaning first, then optional (medical term), then clinician questions."
    )
    return "\n".join(lines)
