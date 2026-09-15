"""
decision_support/text_parser.py
────────────────────────────────
يحلّل رسالة المستخدم النصية ويستخرج منها:
  • اسم المنتج
  • نوع البشرة

الاستراتيجية:
  1. استخراج نوع البشرة بمطابقة كلمات مفتاحية.
  2. حذف الجزء المتعلق بالبشرة من الجملة.
  3. البحث عن اسم المنتج في الجزء المتبقي باستخدام
     trigger keywords صريحة فقط (بدون optional patterns).
"""

import re
from typing import Optional


VALID_SKIN_TYPES: list[str] = [
    "Combination", "Dry", "Normal", "Oily", "Sensitive"
]

_SKIN_KEYWORDS: dict[str, list[str]] = {
    "Combination": ["combination", "combined", "mixed", "combo"],
    "Dry":         ["dry", "dehydrated"],
    "Normal":      ["normal"],
    "Oily":        ["oily", "greasy", "shiny"],
    "Sensitive":   ["sensitive", "sensitiv", "reactive"],
}

_TRIGGERS = [
    r"i(?:'?m|\s+am)\s+(?:looking|searching|interested)\s+(?:for\s+)?",
    r"(?:i\s+want\s+to\s+)?buy\s+",
    r"(?:please\s+)?(?:check|analyse|analyze|evaluate|review)\s+",
    r"can\s+i\s+use\s+",
    r"i\s+want\s+",
    r"purchase\s+",
    r"recommend\s+",
    r"suggest\s+",
    r"about\s+",
    r"(?:is|are)\s+",   # "Is CeraVe good for..." — يجب أن يكون آخراً
]

# regex يطابق: <trigger> ثم اسم المنتج (يبدأ بأي حرف، أحرف كبيرة أو صغيرة)
_TRIGGER_RE = re.compile(
    r"(?:" + "|".join(_TRIGGERS) + r")"
    r"([A-Za-z0-9][A-Za-z0-9\s'®™%&+.,()™\-/]{2,120})",
    re.IGNORECASE,
)


def parse_message(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    استخراج (product_name, skin_type) من رسالة المستخدم.

    Returns
    -------
    product_name : str or None
    skin_type    : str or None  (e.g. "Dry", "Oily")
    """
    skin_type    = _extract_skin_type(text)
    # نحذف جملة البشرة من النص قبل استخراج اسم المنتج
    # حتى لا تتداخل كلمة "dry/oily/..." مع اسم المنتج
    cleaned_text = _remove_skin_phrase(text)
    product_name = _extract_product_name(cleaned_text)
    return product_name, skin_type


def is_offtopic(text: str) -> bool:
    """
    True إذا كانت الرسالة دردشة عامة لا تتعلق بالمنتجات.
    """
    lower = text.lower().strip()

    # كلمات تحية / دردشة واضحة
    greet_patterns = [
        r"\bhello\b", r"\bhey\b", r"\bhi\b",
        r"\bhow are you\b", r"\bwhat'?s up\b",
        r"\bwho are you\b", r"\bwhat can you do\b",
        r"\bthank(?:s|you)?\b", r"\bbye\b", r"\bgoodbye\b",
        r"\bgood (?:morning|evening|night)\b",
        r"\btell me a joke\b", r"\bweather\b",
    ]
    for pattern in greet_patterns:
        if re.search(pattern, lower):
            return True

    # يجب أن تحتوي على إشارة لمنتج أو بشرة
    has_skin_signal = any(
        re.search(r"\b" + re.escape(kw) + r"\b", lower)
        for kws in _SKIN_KEYWORDS.values()
        for kw in kws
    )
    has_product_signal = any(
        kw in lower
        for kw in [
            "skin", "want", "buy", "product", "cream", "serum",
            "moisturizer", "cleanser", "sunscreen", "mask",
            "treatment", "eye cream", "check", "analyse", "analyze",
            "suitable", "recommend", "use",
        ]
    )
    return not (has_skin_signal or has_product_signal)


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_skin_type(text: str) -> Optional[str]:
    """استخراج نوع البشرة من النص."""
    lower = text.lower()
    for canonical, keywords in _SKIN_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return canonical
    return None


def _remove_skin_phrase(text: str) -> str:
    """
    يحذف الجزء المتعلق بنوع البشرة من الجملة.
    مثال:
      "My skin type is dry and I want Weleda Cream"
      → "I want Weleda Cream"
    """
    all_skin_kws = "|".join(
        re.escape(kw)
        for kws in _SKIN_KEYWORDS.values()
        for kw in kws
    )

    # حذف عبارات من شكل:
    # "my skin type is dry", "I have oily skin", "skin is sensitive" إلخ
    patterns = [
        # "my skin type is dry and"  /  "my skin is dry and"
        r"my\s+skin(?:\s+type)?\s+is\s+(?:" + all_skin_kws + r")\s*(?:and\s+)?",
        # "I have dry skin and"
        r"i\s+have\s+(?:" + all_skin_kws + r")\s+skin\s*(?:and\s+)?",
        # "for dry skin and"
        r"for\s+(?:" + all_skin_kws + r")\s+skin\s*(?:and\s+)?",
        # standalone "dry skin"
        r"(?:" + all_skin_kws + r")\s+skin\s*(?:type)?\s*(?:and\s+)?",
        # standalone كلمة البشرة بمفردها
        r"\b(?:" + all_skin_kws + r")\b",
    ]

    result = text
    for p in patterns:
        result = re.sub(p, " ", result, flags=re.IGNORECASE)

    return result.strip()


def _extract_product_name(text: str) -> Optional[str]:
    """
    استخراج اسم المنتج من النص (بعد حذف جملة البشرة).
    يستخدم trigger keywords صريحة فقط.
    """
    # المحاولة 1: trigger keyword واضحة قبل اسم المنتج
    match = _TRIGGER_RE.search(text)
    if match:
        candidate = _clean_candidate(match.group(1))
        if candidate and len(candidate) >= 3:
            return candidate

    # المحاولة 2: إذا بقي نص بعد حذف جملة البشرة وكان طويلاً بما يكفي
    # نأخذ أطول مقطع متواصل (يحتوي على رقم أو حرف خاص — علامة على اسم منتج)
    # نتجاهل كلمات الربط القصيرة فقط
    fallback = re.sub(
        r"\b(?:and|the|a|an|is|for|to|my|i|me|have|want|use|please|can)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    ).strip()
    fallback = re.sub(r"\s{2,}", " ", fallback).strip(" .,;?!")

    if len(fallback) >= 4:
        return fallback

    return None


def _clean_candidate(raw: str) -> Optional[str]:
    """تنظيف المرشح: إزالة فراغات ولواحق غير مرغوبة."""
    if not raw:
        return None

    cleaned = raw.strip(" .,;?!\n\t")

    # إزالة لواحق نوع البشرة إن التصقت بآخر الاسم
    all_skin_kws = "|".join(
        re.escape(kw)
        for kws in _SKIN_KEYWORDS.values()
        for kw in kws
    )
    skin_suffix = (
        r"\s+(?:for\s+)?(?:my\s+)?(?:" + all_skin_kws + r")\s*(?:skin|type)?$"
    )
    cleaned = re.sub(skin_suffix, "", cleaned, flags=re.IGNORECASE).strip()

    # إزالة كلمات الوصف التي قد تلتصق بآخر اسم المنتج
    trailing_noise = (
        r"\s+(?:good|great|best|suitable|bad|safe|effective|"
        r"right|perfect|ok|okay|fine|well|nice)\b.*$"
    )
    cleaned = re.sub(trailing_noise, "", cleaned, flags=re.IGNORECASE).strip()

    # إزالة عبارة "for my skin / for skin" من النهاية
    cleaned = re.sub(
        r"\s+(?:for\s+(?:my\s+)?skin|for\s+me)\s*$",
        "", cleaned, flags=re.IGNORECASE
    ).strip()

    cleaned = cleaned.strip(" .,;?!-–—")  # إزالة الشرطات من الطرفين أيضاً

    return cleaned if len(cleaned) >= 3 else None