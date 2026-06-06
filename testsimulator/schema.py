"""
ME4 TestSimulator — JSON Macro Schema Validation.

Defines the JSON schema for test macros and provides validation + loading
utilities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

# ---------------------------------------------------------------------------
# JSON Schema for macro files
# ---------------------------------------------------------------------------
MACRO_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ME4 TestSimulator Macro",
    "description": "A recorded or scripted UI test macro.",
    "type": "object",
    "required": ["version", "metadata", "steps"],
    "properties": {
        "version": {
            "type": "string",
            "description": "Macro format version (semver).",
        },
        "metadata": {
            "type": "object",
            "required": ["name", "created"],
            "properties": {
                "name": {"type": "string", "description": "Human-readable macro name."},
                "description": {"type": "string"},
                "created": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO-8601 creation timestamp.",
                },
                "browser": {
                    "type": "string",
                    "enum": ["chromium", "firefox", "webkit"],
                    "default": "chromium",
                },
                "viewport": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer", "minimum": 320},
                        "height": {"type": "integer", "minimum": 240},
                    },
                },
            },
        },
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "action"],
                "properties": {
                    "id": {"type": "integer", "minimum": 1},
                    "action": {
                        "type": "string",
                        "enum": [
                            "navigate",
                            "click",
                            "click_text",
                            "type",
                            "type_into",
                            "wait",
                            "wait_for_text",
                            "screenshot",
                            "assert_visible",
                            "assert_text",
                            "sleep",
                            "hover",
                            "select_option",
                            "press_key",
                            "scroll",
                        ],
                    },
                    "description": {"type": "string"},
                    # action-specific properties
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "text": {"type": "string"},
                    "placeholder": {"type": "string"},
                    "timeout": {"type": "number", "minimum": 0},
                    "path": {"type": "string"},
                    "seconds": {"type": "number", "minimum": 0},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "direction": {"type": "string", "enum": ["up", "down"]},
                },
            },
        },
    },
}


def validate_macro(macro: dict[str, Any]) -> bool:
    """Validate a macro dict against ``MACRO_SCHEMA``.

    Args:
        macro: The parsed macro dictionary.

    Returns:
        ``True`` if valid.

    Raises:
        jsonschema.ValidationError: If the macro is invalid.
    """
    jsonschema.validate(instance=macro, schema=MACRO_SCHEMA)
    return True


def load_macro(path: str | Path) -> dict[str, Any]:
    """Load and validate a macro JSON file.

    Args:
        path: Path to a ``.json`` macro file.

    Returns:
        The parsed and validated macro dict.

    Raises:
        FileNotFoundError: If *path* does not exist.
        jsonschema.ValidationError: If the macro is invalid.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Macro file not found: {path}")

    with open(path, encoding="utf-8") as fh:
        macro = json.load(fh)

    validate_macro(macro)
    return macro


# ---------------------------------------------------------------------------
# CLI entry-point: python -m testsimulator.schema
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    # Build a minimal example macro for self-test
    example: dict[str, Any] = {
        "version": "1.0",
        "metadata": {
            "name": "smproducer-full-workflow",
            "created": "2026-06-06T18:30:00Z",
            "browser": "chromium",
            "viewport": {"width": 1920, "height": 1080},
        },
        "steps": [
            {
                "id": 1,
                "action": "navigate",
                "url": "http://localhost:5173",
                "description": "Öffne SMproducer",
            },
            {
                "id": 2,
                "action": "click",
                "selector": "button[data-testid='new-project']",
                "description": "Neues Projekt starten",
            },
            {
                "id": 3,
                "action": "type_into",
                "placeholder": "https://www.youtube.com/watch?v=",
                "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "description": "YouTube URL eingeben",
            },
            {
                "id": 4,
                "action": "wait",
                "selector": ".result-item",
                "timeout": 10.0,
                "description": "Warte auf Ergebnisse",
            },
        ],
    }

    # If a file is passed, load it; otherwise validate the built-in example
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(f"[schema] Loading macro from: {filepath}")
        macro = load_macro(filepath)
        print(f"[schema] Valid: {macro['metadata']['name']} ({len(macro['steps'])} steps)")
    else:
        print("[schema] Validating built-in example macro...")
        try:
            validate_macro(example)
            print(f"[schema] Valid: {example['metadata']['name']} ({len(example['steps'])} steps)")
        except jsonschema.ValidationError as exc:
            print(f"[schema] INVALID: {exc.message}")
            sys.exit(1)

    # Also show the schema itself (compact)
    num_actions = len(MACRO_SCHEMA['properties']['steps']['items']['properties']['action']['enum'])
    print(f"[schema] Schema defines {num_actions} action types")
