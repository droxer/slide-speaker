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
        code = cls.LANGUAGE_LOCALE_MAP.get(language.lower(), "en")
        logger.debug(f"Converted language '{language}' to locale code '{code}'")
        return code

    @classmethod
    def get_language_name(cls, locale_code: str) -> str:
        language = cls.LOCALE_LANGUAGE_MAP.get(locale_code, "english")
        logger.debug(f"Converted locale code '{locale_code}' to language '{language}'")
        return language

    @classmethod
    def get_display_name(cls, language: str) -> str:
        return cls.LANGUAGE_DISPLAY_NAMES.get(language.lower(), language.title())

    @classmethod
    def validate_language(cls, language: str) -> bool:
        return language.lower() in cls.LANGUAGE_LOCALE_MAP

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
        normalized = language.lower().strip()
        return normalized if normalized in cls.LANGUAGE_LOCALE_MAP else "english"


locale_utils = LocaleUtils()
