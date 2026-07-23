from __future__ import annotations

from typing import Any

from mcp_tool_server.core.errors import MCPValidationError


JSONSchema = dict[str, Any]


def validate_payload(payload: dict[str, Any], schema: JSONSchema, *, label: str) -> dict[str, Any]:
    """Small JSON Schema subset for this educational project.

    Supported keywords: type, properties, required, additionalProperties, enum,
    minimum, maximum, minLength, maxLength, minItems, maxItems, items.
    """
    if not isinstance(payload, dict):
        raise MCPValidationError(f"{label} must be an object.")
    _validate_value(payload, schema, path=label)
    return payload


def assert_valid_schema(schema: JSONSchema, *, label: str) -> None:
    if not isinstance(schema, dict):
        raise MCPValidationError(f"{label} must be a JSON object.")
    if schema.get("type") != "object":
        raise MCPValidationError(f"{label}.type must be 'object'.")
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    if not isinstance(required, list):
        raise MCPValidationError(f"{label}.required must be a list.")
    if not isinstance(properties, dict):
        raise MCPValidationError(f"{label}.properties must be an object.")
    unknown_required = sorted(set(required) - set(properties))
    if unknown_required:
        raise MCPValidationError(
            f"{label}.required contains fields missing from properties.",
            details={"unknown_required": unknown_required},
        )


def _validate_value(value: Any, schema: JSONSchema, *, path: str) -> None:
    expected_type = schema.get("type")
    if expected_type:
        _validate_type(value, expected_type, path=path)

    if "enum" in schema and value not in schema["enum"]:
        raise MCPValidationError(
            f"{path} must be one of {schema['enum']}.",
            details={"path": path, "allowed": schema["enum"]},
        )

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                raise MCPValidationError(
                    f"{path}.{field} is required.",
                    details={"path": f"{path}.{field}"},
                )
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise MCPValidationError(
                    f"{path} has unknown fields: {extra}.",
                    details={"path": path, "unknown_fields": extra},
                )
        for field, field_value in value.items():
            if field in properties:
                _validate_value(field_value, properties[field], path=f"{path}.{field}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise MCPValidationError(f"{path} must contain at least {schema['minItems']} items.")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise MCPValidationError(f"{path} must contain at most {schema['maxItems']} items.")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_value(item, item_schema, path=f"{path}[{index}]")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise MCPValidationError(f"{path} must be >= {schema['minimum']}.")
        if "maximum" in schema and value > schema["maximum"]:
            raise MCPValidationError(f"{path} must be <= {schema['maximum']}.")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise MCPValidationError(f"{path} is shorter than {schema['minLength']} chars.")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise MCPValidationError(f"{path} is longer than {schema['maxLength']} chars.")


def _validate_type(value: Any, expected_type: str | list[str], *, path: str) -> None:
    types = expected_type if isinstance(expected_type, list) else [expected_type]
    if any(_matches_type(value, type_name) for type_name in types):
        return
    raise MCPValidationError(
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
