"""JSON Schema helper for SKILL.md frontmatter.

Loads the schema published at ``skillmd_frontmatter.schema.json`` in the repo
root and exposes a single ``validate_frontmatter(fm)`` function that returns a
list of human-readable violation messages. Schema validation is intentionally
*additive* on top of the rule engine: the rules emit specific error codes
(E001..E010, W001..W013) while the schema gives users a portable, machine-
readable description of the contract.

The helper is pure-Python and has no hard dependency on ``jsonschema`` — it
implements the small subset of Draft 2020-12 we need (type, pattern, enum,
required, minLength, maxLength, minimum, uniqueItems, $ref-by-pattern). That
keeps the install footprint tiny for users who only want CLI linting.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

# Try to use the package distribution mechanism first; fall back to the repo
# source layout so ``python -m skillmd_lint`` works without an install.
_SCHEMA_TEXT: str | None = None


def _load_schema_text() -> str:
    global _SCHEMA_TEXT
    if _SCHEMA_TEXT is not None:
        return _SCHEMA_TEXT
    try:
        _SCHEMA_TEXT = (
            resources.files("skillmd_lint").joinpath("schema.json").read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError):
        # Source checkout / editable install — fall back to repo-root file.
        here = Path(__file__).resolve().parent.parent
        candidate = here / "skillmd_frontmatter.schema.json"
        _SCHEMA_TEXT = candidate.read_text(encoding="utf-8")
    return _SCHEMA_TEXT


def get_schema() -> dict[str, Any]:
    """Return the parsed SKILL.md frontmatter JSON Schema."""

    return json.loads(_load_schema_text())


def _coerce_scalar(value: Any, schema: dict[str, Any]) -> Any:
    """Coerce YAML scalars that don't match the declared type.

    YAML commonly returns ints as ``int`` and bools as ``bool``, but the spec
    sometimes declares ``"string"`` for what should be a number. We don't try
    to be too clever here — only the common, safe coercions.
    """

    if (
        schema.get("type") == "string"
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        return str(value)
    return value


def _check_one(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    schema_type = schema.get("type")
    if schema_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
            return
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: {value!r} not in enum {schema['enum']}")
    elif schema_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")
            return
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
    elif schema_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return
        if schema.get("uniqueItems"):
            seen: set[Any] = set()
            for item in value:
                key = json.dumps(item, sort_keys=True)
                if key in seen:
                    errors.append(f"{path}: duplicate item {item!r}")
                else:
                    seen.add(key)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                _check_one(item, item_schema, f"{path}[{i}]", errors)
    elif schema_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required key '{req}'")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                _check_one(_coerce_scalar(value[k], sub), sub, f"{path}.{k}", errors)


def validate_frontmatter(fm: dict[str, Any]) -> list[str]:
    """Return a list of human-readable schema violations for ``fm``.

    An empty list means the frontmatter conforms to the published schema. Note
    that schema-level checks are stricter than the rule engine (e.g. ``name``
    pattern is always checked), so a file that passes ``skillmd-lint --strict``
    can still emit schema warnings here if it uses fields outside the
    published schema — that's expected, the schema is a stricter contract.
    """

    schema = get_schema()
    errors: list[str] = []
    _check_one(fm, schema, "$", errors)
    return errors
