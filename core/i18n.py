"""
界面多语言：中文 / English
"""
from typing import Optional

# 当前语言： "zh" 中文（默认），"en" 英语
_LANG: str = "zh"


def get_language() -> str:
    return _LANG


def set_language(lang: str):
    global _LANG
    if lang in ("zh", "en"):
        _LANG = lang


def t(zh: str, en: str, lang: Optional[str] = None) -> str:
    """根据当前语言返回中文或英文。"""
    use = (lang or _LANG)
    return zh if use == "zh" else en
