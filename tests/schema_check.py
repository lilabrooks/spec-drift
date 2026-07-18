"""A tiny, dependency-free validator for the subset of JSON Schema the report
schema uses: ``type`` (string or list), ``enum``, ``required``,
``properties``, ``additionalProperties: false``, ``items``, ``$ref``/``$defs``,
and ``minimum``/``minLength``.

The project keeps zero runtime dependencies and hand-rolls its small parsers
(the okf-map reader, the frontmatter reader); this test helper follows that
pattern rather than adding ``jsonschema`` just for tests. It is exercised
against known-good and known-bad documents in ``test_report.py`` so it can be
trusted to actually reject malformed output.
"""

from __future__ import annotations

from typing import Any


class SchemaError(AssertionError):
    """Raised when a document does not satisfy the schema."""


def validate(document: object, schema: dict[str, Any], root: dict[str, Any] | None = None) -> None:
    root = root if root is not None else schema

    if "$ref" in schema:
        validate(document, _resolve(schema["$ref"], root), root)
        return

    _check_type(document, schema)

    if "enum" in schema and document not in schema["enum"]:
        raise SchemaError(f"{document!r} is not one of {schema['enum']}")
    if "minimum" in schema and isinstance(document, int) and document < schema["minimum"]:
        raise SchemaError(f"{document} < minimum {schema['minimum']}")
    if "minLength" in schema and isinstance(document, str) and len(document) < schema["minLength"]:
        raise SchemaError(f"{document!r} shorter than {schema['minLength']}")

    if isinstance(document, dict):
        _check_object(document, schema, root)
    if isinstance(document, list) and "items" in schema:
        for item in document:
            validate(item, schema["items"], root)


_TYPE_CHECKS = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
    "integer": int,
}


def _check_type(document: object, schema: dict[str, Any]) -> None:
    if "type" not in schema:
        return
    allowed = schema["type"]
    names = allowed if isinstance(allowed, list) else [allowed]
    for name in names:
        expected = _TYPE_CHECKS[name]
        # bool is a subclass of int; keep them distinct.
        if expected is int and isinstance(document, bool):
            continue
        if expected is bool and not isinstance(document, bool):
            continue
        if isinstance(document, expected):
            return
    raise SchemaError(f"{document!r} is not of type {allowed}")


def _check_object(document: dict[str, Any], schema: dict[str, Any], root: dict[str, Any]) -> None:
    for key in schema.get("required", []):
        if key not in document:
            raise SchemaError(f"missing required key {key!r}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        extra = set(document) - set(properties)
        if extra:
            raise SchemaError(f"unexpected keys {sorted(extra)}")
    for key, value in document.items():
        if key in properties:
            validate(value, properties[key], root)


def _resolve(ref: str, root: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise SchemaError(f"unsupported $ref {ref!r}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node
