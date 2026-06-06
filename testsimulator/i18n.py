"""
ME4 TestSimulator — i18n Loader.

Loads translations from ``i18n/`` JSON files as specified in the
``manifest.json``. Supports German (default) and English.
"""

from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Locate the i18n directory relative to the project root
# ---------------------------------------------------------------------------
_I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"


class I18nError(Exception):
    """Raised when i18n resources are missing or misconfigured."""


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
_manifest: dict[str, Any] | None = None
_translations: dict[str, dict[str, str]] = {}
_default_lang: str = "de"


def _load_manifest() -> dict[str, Any]:
    """Load and return the i18n manifest."""
    path = _I18N_DIR / "manifest.json"
    if not path.is_file():
        raise I18nError(f"i18n manifest not found: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_translations(lang: str) -> dict[str, str]:
    """Load translations for *lang* from disk."""
    path = _I18N_DIR / f"{lang}.json"
    if not path.is_file():
        raise I18nError(f"Translation file not found: {path} (lang={lang})")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise I18nError(f"Translation file is not a dict: {path}")
    return {str(k): str(v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def init(lang: str | None = None) -> None:
    """Initialize i18n subsystem (idempotent).

    Args:
        lang: Override the default language (``"de"`` or ``"en"``).
    """
    global _manifest, _default_lang, _translations

    _manifest = _load_manifest()
    _default_lang = lang or _manifest.get("default", "de")

    # Pre-load available languages
    available = set(_manifest.get("languages", {}).keys())
    if _default_lang not in available:
        raise I18nError(
            f"Default language '{_default_lang}' not in manifest languages: {sorted(available)}"
        )

    for code in available:
        _translations[code] = _load_translations(code)


def get_text(key: str, lang: str | None = None, **fmt: Any) -> str:
    """Look up a translated string by *key*.

    Args:
        key: Dot-separated translation key (e.g. ``"app.name"``).
        lang: Language code; defaults to initialized default.
        **fmt: Optional ``str.format`` keyword replacements.

    Returns:
        The translated string, or *key* itself if not found.
    """
    global _default_lang, _translations, _manifest

    if _manifest is None:
        init()

    code = lang or _default_lang
    table = _translations.get(code, {})

    text = table.get(key, key)
    if fmt:
        with suppress(KeyError):
            text = text.format(**fmt)  # Return unformatted if placeholders don't match

    return text


def available_languages() -> list[str]:
    """Return sorted list of available language codes."""
    if _manifest is None:
        init()
    return sorted((_manifest or {}).get("languages", {}).keys())


def default_language() -> str:
    """Return the current default language code."""
    if _manifest is None:
        init()
    return _default_lang


# ---------------------------------------------------------------------------
# CLI entry-point: python -m testsimulator.i18n [--validate] [--lang de|en]
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    init()

    validate_mode = "--validate" in sys.argv
    show_lang = _default_lang
    for i, arg in enumerate(sys.argv):
        if arg == "--lang" and i + 1 < len(sys.argv):
            show_lang = sys.argv[i + 1]

    print(f"[i18n] Available languages: {available_languages()}")
    print(f"[i18n] Default language: {_default_lang}")

    if validate_mode:
        # Validate every key in every language exists in all languages
        all_keys: dict[str, set[str]] = {}
        for code in available_languages():
            all_keys[code] = set(_translations[code].keys())

        base = all_keys[available_languages()[0]]
        errors = []
        for code in available_languages()[1:]:
            missing = base - all_keys[code]
            extra = all_keys[code] - base
            if missing:
                errors.append(f"  {code} missing keys: {sorted(missing)}")
            if extra:
                errors.append(f"  {code} extra keys: {sorted(extra)}")

        if errors:
            print("[i18n] VALIDATION FAILED:")
            for e in errors:
                print(e)
            sys.exit(1)
        else:
                    print(
            f"[i18n] Validation OK — {len(base)} keys consistent"
            f" across {len(available_languages())} languages"
        )

    # Show a few translated keys
    demo_keys = ["app.name", "app.tagline", "webdriver.launching", "cli.record.help"]
    print(f"\n[i18n] Demo texts ({show_lang}):")
    for k in demo_keys:
        print(f"  {k} = {get_text(k, lang=show_lang)}")
