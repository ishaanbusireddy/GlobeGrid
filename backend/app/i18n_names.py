"""v6 §11 — locale code → English language name for translation prompts.

Mirrors the v5 §2 frontend locale list (frontend/src/i18n.js). The model is
told the target language by NAME (\"Simplified Chinese\"), not code, because
codes are ambiguous to smaller models.
"""

LANGUAGE_NAMES = {
    "en": "English", "bg": "Bulgarian", "hr": "Croatian", "cs": "Czech",
    "da": "Danish", "nl": "Dutch", "et": "Estonian", "fi": "Finnish",
    "fr": "French", "de": "German", "el": "Greek", "hu": "Hungarian",
    "ga": "Irish", "it": "Italian", "lv": "Latvian", "lt": "Lithuanian",
    "mt": "Maltese", "pl": "Polish", "pt": "Portuguese", "ro": "Romanian",
    "sk": "Slovak", "sl": "Slovenian", "es": "Spanish", "sv": "Swedish",
    "no": "Norwegian", "is": "Icelandic", "uk": "Ukrainian", "be": "Belarusian",
    "sr": "Serbian", "bs": "Bosnian", "sq": "Albanian", "mk": "Macedonian",
    "fa": "Persian", "tr": "Turkish", "ka": "Georgian", "hy": "Armenian",
    "az": "Azerbaijani", "ur": "Urdu", "id": "Indonesian", "th": "Thai",
    "vi": "Vietnamese", "fil": "Filipino", "ms": "Malay", "my": "Burmese",
    "km": "Khmer", "lo": "Lao", "ja": "Japanese", "ko": "Korean",
    "zh-Hans": "Simplified Chinese", "zh-Hant": "Traditional Chinese",
    "sw": "Swahili", "he": "Hebrew", "am": "Amharic", "ar": "Arabic",
    "ru": "Russian", "hi": "Hindi",
}
