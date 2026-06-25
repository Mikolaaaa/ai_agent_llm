from __future__ import annotations

from typing import Any

from agent_runtime.core.errors import ValidationRuntimeError


JSONSchema = dict[str, Any]


def validate_payload(payload: dict[str, Any], schema: JSONSchema, *, label: str) -> dict[str, Any]:
    """Validate a dict against the small JSON-schema subset used by this project.

    Supported keywords: type, properties, required, additionalProperties, enum,
    minimum, maximum, minLength, maxLength, minItems, maxItems, items.
    """
    if not isinstance(payload, dict):
        raise ValidationRuntimeError(f"{label} must be an object.")
    _validate_value(payload, schema, path=label)
    return payload


def validate_output_size(output: dict[str, Any], max_chars: int) -> None:
    size = len(repr(output))
    if size > max_chars:
        raise ValidationRuntimeError(
            f"Tool output is too large: {size} chars > {max_chars}.",
            details={"size": size, "max_chars": max_chars},
        )


def _validate_value(value: Any, schema: JSONSchema, *, path: str) -> None:
    expected_type = schema.get("type")
    if expected_type:
        _validate_type(value, expected_type, path=path)

    if "enum" in schema and value not in schema["enum"]:
        raise ValidationRuntimeError(
            f"{path} must be one of {schema['enum']}.",
            details={"path": path, "allowed": schema["enum"]},
        )

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                raise ValidationRuntimeError(
                    f"{path}.{field} is required.",
                    details={"path": f"{path}.{field}"},
                )
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ValidationRuntimeError(
                    f"{path} has unknown fields: {extra}.",
                    details={"path": path, "unknown_fields": extra},
                )
        for field, field_value in value.items():
            if field in properties:
                _validate_value(field_value, properties[field], path=f"{path}.{field}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValidationRuntimeError(f"{path} must contain at least {schema['minItems']} items.")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValidationRuntimeError(f"{path} must contain at most {schema['maxItems']} items.")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_value(item, item_schema, path=f"{path}[{index}]")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValidationRuntimeError(f"{path} must be >= {schema['minimum']}.")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValidationRuntimeError(f"{path} must be <= {schema['maximum']}.")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValidationRuntimeError(f"{path} is shorter than {schema['minLength']} chars.")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValidationRuntimeError(f"{path} is longer than {schema['maxLength']} chars.")


def _validate_type(value: Any, expected_type: str | list[str], *, path: str) -> None:
    types = expected_type if isinstance(expected_type, list) else [expected_type]
    if any(_matches_type(value, type_name) for type_name in types):
        return
    raise ValidationRuntimeError(
        f"{path} has invalid type. Expected {types}.",
        details={"path": path, "expected": types, "actual": type(value).__name__},
    )


def _matches_type(value: Any, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    return False
