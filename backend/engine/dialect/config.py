"""
Available dialect definitions for rewriting.
"""

from typing import Any

# Language display names for translation prompts
_LANGUAGE_NAMES: dict[str, str] = {
    "chinese_simplified": "Simplified Chinese",
    "spanish": "Spanish",
    "french": "French",
    "arabic": "Arabic",
    "hindi": "Hindi",
    "japanese": "Japanese",
    "korean": "Korean",
    "portuguese": "Portuguese",
    "german": "German",
}

def _translation_system_prompt(lang_name: str) -> str:
    return (
        f"Translate the following into natural {lang_name}. "
        "Maintain the exact same meaning, structure, and all specific details (names, numbers, categories). "
        "Output ONLY the translated text in {lang_name}."
    ).format(lang_name=lang_name)

AVAILABLE_DIALECTS: dict[str, Any] = {
    # --- English Varieties ---
    "aave": {
        "id": "aave",
        "name": "African American Vernacular English (AAVE)",
        "type": "english_dialect",
        "requires_llm": True,
        "system_prompt": (
            "Rewrite the following text in natural African American Vernacular English (AAVE). "
            "Use authentic grammar patterns (habitual be, copula deletion, negative concord) and natural phrasing. "
            "Keep the same meaning and all specific details/names/numbers. "
            "Do NOT use stereotypes or caricature. "
            "Output ONLY the rewritten text."
        ),
        "example_input": "She is always working late at the office.",
        "example_output": "She be workin late at the office.",
    },
    "gen_z": {
        "id": "gen_z",
        "name": "Gen Z Internet English",
        "type": "english_style",
        "requires_llm": True,
        "system_prompt": (
            "Rewrite in Gen Z internet-influenced casual English. "
            "Use common slang (no cap, lowkey, slay, vibe, etc.), abbreviated forms, and casual tone. "
            "Keep the same meaning and details. "
            "Output ONLY the rewritten text."
        ),
        "example_input": "That presentation was really impressive.",
        "example_output": "That presentation was lowkey slay, no cap.",
    },
    "indian_english": {
        "id": "indian_english",
        "name": "Indian English",
        "type": "english_dialect",
        "requires_llm": True,
        "system_prompt": (
            "Rewrite in natural Indian English. "
            "Use characteristic patterns like different preposition usage, progressive tenses with stative verbs, tag questions, and idiomatic expressions common in Indian English. "
            "Keep all details. "
            "Output ONLY the rewritten text."
        ),
        "example_input": "I am understanding the problem now.",
        "example_output": "I am understanding the problem now, no?",
    },
    "southern_us": {
        "id": "southern_us",
        "name": "Southern US English",
        "type": "english_dialect",
        "requires_llm": True,
        "system_prompt": (
            "Rewrite in Southern US English dialect. "
            "Use patterns like fixin' to, y'all, might could, double modals, and Southern idioms. "
            "Keep same meaning and details. "
            "Output ONLY the rewritten text."
        ),
        "example_input": "We are going to the store soon.",
        "example_output": "We're fixin' to go to the store directly.",
    },
    "british_english": {
        "id": "british_english",
        "name": "British English",
        "type": "english_style",
        "requires_llm": True,
        "system_prompt": (
            "Rewrite in British English. "
            "Use British vocabulary (lift/elevator, boot/trunk), spelling, idioms, and phrasing. "
            "Keep same meaning. "
            "Output ONLY the rewritten text."
        ),
        "example_input": "I put the bags in the trunk and took the elevator.",
        "example_output": "I put the bags in the boot and took the lift.",
    },
    # --- Languages ---
    "chinese_simplified": {
        "id": "chinese_simplified",
        "name": _LANGUAGE_NAMES["chinese_simplified"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["chinese_simplified"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "请于周五前发送报告。",
    },
    "spanish": {
        "id": "spanish",
        "name": _LANGUAGE_NAMES["spanish"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["spanish"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "Por favor envía el informe antes del viernes.",
    },
    "french": {
        "id": "french",
        "name": _LANGUAGE_NAMES["french"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["french"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "Veuillez envoyer le rapport avant vendredi.",
    },
    "arabic": {
        "id": "arabic",
        "name": _LANGUAGE_NAMES["arabic"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["arabic"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "يرجى إرسال التقرير بحلول يوم الجمعة.",
    },
    "hindi": {
        "id": "hindi",
        "name": _LANGUAGE_NAMES["hindi"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["hindi"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "कृपया शुक्रवार तक रिपोर्ट भेजें।",
    },
    "japanese": {
        "id": "japanese",
        "name": _LANGUAGE_NAMES["japanese"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["japanese"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "金曜日までにレポートを送ってください。",
    },
    "korean": {
        "id": "korean",
        "name": _LANGUAGE_NAMES["korean"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["korean"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "금요일까지 보고서를 보내 주세요.",
    },
    "portuguese": {
        "id": "portuguese",
        "name": _LANGUAGE_NAMES["portuguese"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["portuguese"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "Por favor envie o relatório até sexta-feira.",
    },
    "german": {
        "id": "german",
        "name": _LANGUAGE_NAMES["german"],
        "type": "language",
        "requires_llm": True,
        "system_prompt": _translation_system_prompt(_LANGUAGE_NAMES["german"]),
        "example_input": "Please send the report by Friday.",
        "example_output": "Bitte senden Sie den Bericht bis Freitag.",
    },
}
