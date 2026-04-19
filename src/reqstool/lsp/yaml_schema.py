# Copyright © LFV


import json
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "schemas", "v1")

# Map YAML file names to their schema files
YAML_TO_SCHEMA: dict[str, str] = {
    "requirements.yml": "requirements.schema.json",
    "software_verification_cases.yml": "software_verification_cases.schema.json",
    "manual_verification_results.yml": "manual_verification_results.schema.json",
    "reqstool_config.yml": "reqstool_config.schema.json",
}


@lru_cache(maxsize=16)
def load_schema(schema_name: str) -> dict | None:
    schema_path = os.path.join(SCHEMA_DIR, schema_name)
    try:
        with open(schema_path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to load schema %s: %s", schema_name, e)
        return None


def schema_for_yaml_file(filename: str) -> dict | None:
    basename = os.path.basename(filename)
    schema_name = YAML_TO_SCHEMA.get(basename)
    if schema_name is None:
        return None
    return load_schema(schema_name)


def get_field_description(schema: dict, field_path: list[str]) -> str | None:
    """Walk schema to find description for a nested field path.

    E.g., field_path=["metadata", "variant"] looks up:
    schema -> properties.metadata -> $ref -> properties.variant -> description
    """
    current = schema
    for part in field_path:
        current = _resolve_ref(schema, current)
        props = current.get("properties", {})
        if part in props:
            current = props[part]
        else:
            # Check items for array fields
            items = current.get("items", {})
            if items:
                items = _resolve_ref(schema, items)
                props = items.get("properties", {})
                if part in props:
                    current = props[part]
                else:
                    return None
            else:
                return None

    current = _resolve_ref(schema, current)
    return current.get("description")


def get_enum_values(schema: dict, field_path: list[str]) -> list[str]:
    """Walk schema to find enum values for a field."""
    current = schema
    for part in field_path:
        current = _resolve_ref(schema, current)
        props = current.get("properties", {})
        if part in props:
            current = props[part]
        else:
            items = current.get("items", {})
            if items:
                items = _resolve_ref(schema, items)
                props = items.get("properties", {})
                if part in props:
                    current = props[part]
                else:
                    return []
            else:
                return []

    current = _resolve_ref(schema, current)
    if "enum" in current:
        return current["enum"]
    # Check items for array-of-enum fields (e.g., categories)
    items = current.get("items", {})
    if items:
        items = _resolve_ref(schema, items)
        if "enum" in items:
            return items["enum"]
    return []


def _resolve_ref(root_schema: dict, node: dict) -> dict:
    """Resolve a $ref within the same schema file."""
    ref = node.get("$ref")
    if ref is None or not isinstance(ref, str):
        return node
    # Only handle local refs (starting with #/)
    if not ref.startswith("#/"):
        return node
    parts = ref.lstrip("#/").split("/")
    resolved = root_schema
    for part in parts:
        if isinstance(resolved, dict):
            resolved = resolved.get(part, {})
        else:
            return node
    return resolved
