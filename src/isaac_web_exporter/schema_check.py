"""Small validator for the JSON Schema keywords used by the v1 contracts.

The package contracts are ordinary draft-2020-12 JSON Schemas. This module
implements only the keywords present in our four shipped schemas, so offline
validation needs no extra Python distribution inside Isaac's runtime.
"""

import math
import re


def validate(data, schema, location="$"):
    errors = []
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        matches = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "number": lambda v: type(v) in (int, float) and math.isfinite(v),
            "integer": lambda v: type(v) is int,
            "null": lambda v: v is None,
        }
        if not any(matches[kind](data) for kind in kinds):
            return [f"{location}: expected {' or '.join(kinds)}"]
    if "const" in schema and data != schema["const"]:
        errors.append(f"{location}: expected {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{location}: value is outside allowed values")
    if isinstance(data, dict):
        for name in schema.get("required", []):
            if name not in data:
                errors.append(f"{location}.{name}: required field is missing")
        for name, value in data.items():
            if name in schema.get("properties", {}):
                errors.extend(validate(value, schema["properties"][name],
                                       f"{location}.{name}"))
    if isinstance(data, list):
        if len(data) < schema.get("minItems", 0):
            errors.append(f"{location}: too few items")
        if len(data) > schema.get("maxItems", float("inf")):
            errors.append(f"{location}: too many items")
        if "items" in schema:
            for index, value in enumerate(data):
                errors.extend(validate(value, schema["items"], f"{location}[{index}]"))
    if isinstance(data, str):
        if len(data) < schema.get("minLength", 0):
            errors.append(f"{location}: string is too short")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], data):
            errors.append(f"{location}: string does not match required pattern")
    if type(data) in (int, float) and math.isfinite(data):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{location}: below minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{location}: above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            errors.append(f"{location}: must exceed {schema['exclusiveMinimum']}")
    return errors
