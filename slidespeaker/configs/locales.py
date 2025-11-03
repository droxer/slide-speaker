#!/usr/bin/env python3
"""
Locale and language utilities for consistent language handling across the application.
"""

from loguru import logger


class LocaleUtils:
    LANGUAGE_LOCALE_MAP = {
        "english": "en",
        "simplified_chinese": "zh-Hans",
        "traditional_chinese": "zh-Hant",
        "japanese": "ja",
        "korean": "ko",
        "thai": "th",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "italian": "it",
        "portuguese": "pt",
        "russian": "ru",
        "arabic": "ar",
        "hindi": "hi",
    }

    LOCALE_LANGUAGE_MAP = {v: k for k, v in LANGUAGE_LOCALE_MAP.items()}
    _LANGUAGE_LOOKUP = {
        key.lower().replace("_", "-"): value
        for key, value in LANGUAGE_LOCALE_MAP.items()
    }
    _LOCALE_LOOKUP = {key.lower().replace("_", "-"): key for key in LOCALE_LANGUAGE_MAP}

    LANGUAGE_DISPLAY_NAMES = {
        "english": "English",
        "simplified_chinese": "简体中文",
        "traditional_chinese": "繁體中文",
        "japanese": "日本語",
        "korean": "한국어",
        "thai": "ไทย",
        "spanish": "Español",
        "french": "Français",
        "german": "Deutsch",
        "italian": "Italiano",
        "portuguese": "Português",
        "russian": "Русский",
        "arabic": "العربية",
        "hindi": "हिन्दी",
    }

    @classmethod
    def get_locale_code(cls, language: str) -> str:
        if not language:
            return "en"
        normalized = language.strip()
        key = normalized.lower().replace("_", "-")
        if key in cls._LANGUAGE_LOOKUP:
            code = cls._LANGUAGE_LOOKUP[key]
        elif key in cls._LOCALE_LOOKUP:
            code = cls._LOCALE_LOOKUP[key]
        else:
            code = "en"
        logger.debug(f"Converted language '{language}' to locale code '{code}'")
        return code

    @classmethod
    def get_language_name(cls, locale_code: str) -> str:
        if not locale_code:
            return "english"
        key = locale_code.strip()
        lookup = cls.LOCALE_LANGUAGE_MAP.get(key)
        if lookup:
            language = lookup
        else:
            lowered = key.lower().replace("_", "-")
            language = cls.LOCALE_LANGUAGE_MAP.get(
                cls._LOCALE_LOOKUP.get(lowered, ""), "english"
            )
        logger.debug(f"Converted locale code '{locale_code}' to language '{language}'")
        return language

    @classmethod
    def get_display_name(cls, language: str) -> str:
        canonical = cls.normalize_language(language)
        return cls.LANGUAGE_DISPLAY_NAMES.get(canonical, canonical.title())

    @classmethod
    def validate_language(cls, language: str) -> bool:
        if not language:
            return False
        normalized = language.lower().replace("_", "-")
        return normalized in cls._LANGUAGE_LOOKUP or normalized in cls._LOCALE_LOOKUP

    @classmethod
    def get_supported_languages(cls) -> list[dict[str, str]]:
        return [
            {
                "name": lang_name,
                "locale_code": locale_code,
                "display_name": cls.LANGUAGE_DISPLAY_NAMES.get(
                    lang_name, lang_name.title()
                ),
            }
            for lang_name, locale_code in cls.LANGUAGE_LOCALE_MAP.items()
        ]

    @classmethod
    def normalize_language(cls, language: str | None) -> str:
        if not language:
            return "english"
        normalized = language.strip()
        lowered = normalized.lower().replace("_", "-")
        if lowered in cls._LANGUAGE_LOOKUP:
            # Map back to canonical language key (with underscores)
            for key in cls.LANGUAGE_LOCALE_MAP:
                if key.lower().replace("_", "-") == lowered:
                    return key
        if lowered in cls._LOCALE_LOOKUP:
            locale = cls._LOCALE_LOOKUP[lowered]
            return cls.LOCALE_LANGUAGE_MAP.get(locale, "english")
        return "english"


locale_utils = LocaleUtils()
