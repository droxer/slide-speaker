#!/usr/bin/env python3
"""
Locale and language utilities for consistent language handling across the application.
Provides locale-aware language code mapping, validation, and formatting utilities.
"""

from loguru import logger


class LocaleUtils:
    """Locale and language utility class for consistent language handling"""

    # Standard language to locale code mapping (BCP 47 format)
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

    # Reverse mapping for locale to language name
    LOCALE_LANGUAGE_MAP = {v: k for k, v in LANGUAGE_LOCALE_MAP.items()}

    # Language display names for UI
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
        """
        Get BCP 47 locale code for a given language name.

        Args:
            language: Language name (e.g., "english", "traditional_chinese")

        Returns:
            BCP 47 locale code (e.g., "en", "zh-Hant")
        """
        locale_code = cls.LANGUAGE_LOCALE_MAP.get(language.lower(), "en")
        logger.debug(f"Converted language '{language}' to locale code '{locale_code}'")
        return locale_code

    @classmethod
    def get_language_name(cls, locale_code: str) -> str:
        """
        Get language name from BCP 47 locale code.

        Args:
            locale_code: BCP 47 locale code (e.g., "zh-Hant", "ja")

        Returns:
            Language name (e.g., "traditional_chinese", "japanese")
        """
        language = cls.LOCALE_LANGUAGE_MAP.get(locale_code, "english")
        logger.debug(f"Converted locale code '{locale_code}' to language '{language}'")
        return language

    @classmethod
    def get_display_name(cls, language: str) -> str:
        """
        Get display name for a language (localized name).

        Args:
            language: Language name (e.g., "traditional_chinese")

        Returns:
            Localized display name (e.g., "繁體中文")
        """
        display_name = cls.LANGUAGE_DISPLAY_NAMES.get(
            language.lower(), language.title()
        )
        logger.debug(f"Got display name '{display_name}' for language '{language}'")
        return display_name

    @classmethod
    def validate_language(cls, language: str) -> bool:
        """
        Validate if a language is supported.

        Args:
            language: Language name to validate

        Returns:
            True if language is supported, False otherwise
        """
        is_valid = language.lower() in cls.LANGUAGE_LOCALE_MAP
        logger.debug(f"Language validation for '{language}': {is_valid}")
        return is_valid

    @classmethod
    def get_supported_languages(cls) -> list[dict[str, str]]:
        """
        Get list of all supported languages with metadata.

        Returns:
            List of dictionaries with language information
        """
        languages = []
        for lang_name, locale_code in cls.LANGUAGE_LOCALE_MAP.items():
            languages.append(
                {
                    "name": lang_name,
                    "locale_code": locale_code,
                    "display_name": cls.LANGUAGE_DISPLAY_NAMES.get(
                        lang_name, lang_name.title()
                    ),
                }
            )

        logger.debug(f"Returning {len(languages)} supported languages")
        return languages

    @classmethod
    def normalize_language(cls, language: str | None) -> str:
        """
        Normalize language input, handling None and case variations.

        Args:
            language: Language input (may be None, mixed case, etc.)

        Returns:
            Normalized language name or "english" as default
        """
        if not language:
            logger.debug("Language is None or empty, defaulting to 'english'")
            return "english"

        normalized = language.lower().strip()
        if normalized not in cls.LANGUAGE_LOCALE_MAP:
            logger.warning(
                f"Language '{language}' not found in supported "
                f"languages, defaulting to 'english'"
            )
            return "english"

        logger.debug(f"Normalized language '{language}' to '{normalized}'")
        return normalized


# Create singleton instance for easy import
locale_utils = LocaleUtils()
