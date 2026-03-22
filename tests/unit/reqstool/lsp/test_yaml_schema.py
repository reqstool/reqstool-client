# Copyright © LFV

from reqstool.lsp.yaml_schema import (
    get_enum_values,
    get_field_description,
    load_schema,
    schema_for_yaml_file,
)


def test_load_requirements_schema():
    schema = load_schema("requirements.schema.json")
    assert schema is not None
    assert "$defs" in schema


def test_load_svcs_schema():
    schema = load_schema("software_verification_cases.schema.json")
    assert schema is not None


def test_load_mvrs_schema():
    schema = load_schema("manual_verification_results.schema.json")
    assert schema is not None


def test_load_nonexistent_schema():
    schema = load_schema("nonexistent.schema.json")
    assert schema is None


def test_schema_for_requirements_yml():
    schema = schema_for_yaml_file("requirements.yml")
    assert schema is not None
    assert "$defs" in schema


def test_schema_for_svcs_yml():
    schema = schema_for_yaml_file("software_verification_cases.yml")
    assert schema is not None


def test_schema_for_unknown_file():
    schema = schema_for_yaml_file("unknown.yml")
    assert schema is None


def test_get_field_description_metadata_urn():
    schema = load_schema("requirements.schema.json")
    desc = get_field_description(schema, ["metadata", "urn"])
    assert desc is not None
    assert "resource name" in desc.lower() or "urn" in desc.lower()


def test_get_field_description_metadata_variant():
    schema = load_schema("requirements.schema.json")
    desc = get_field_description(schema, ["metadata", "variant"])
    assert desc is not None
    assert "system" in desc.lower() or "microservice" in desc.lower()


def test_get_field_description_requirements():
    schema = load_schema("requirements.schema.json")
    desc = get_field_description(schema, ["requirements"])
    assert desc is not None


def test_get_field_description_significance():
    schema = load_schema("requirements.schema.json")
    desc = get_field_description(schema, ["requirements", "significance"])
    assert desc is not None
    assert "shall" in desc.lower() or "significance" in desc.lower()


def test_get_field_description_nonexistent():
    schema = load_schema("requirements.schema.json")
    desc = get_field_description(schema, ["nonexistent"])
    assert desc is None


def test_get_enum_values_variant():
    schema = load_schema("requirements.schema.json")
    values = get_enum_values(schema, ["metadata", "variant"])
    assert "microservice" in values
    assert "system" in values
    assert "external" in values


def test_get_enum_values_significance():
    schema = load_schema("requirements.schema.json")
    values = get_enum_values(schema, ["requirements", "significance"])
    assert "shall" in values
    assert "should" in values
    assert "may" in values


def test_get_enum_values_categories():
    schema = load_schema("requirements.schema.json")
    values = get_enum_values(schema, ["requirements", "categories"])
    assert "functional-suitability" in values
    assert "security" in values


def test_get_enum_values_implementation():
    schema = load_schema("requirements.schema.json")
    values = get_enum_values(schema, ["requirements", "implementation"])
    assert "in-code" in values
    assert "N/A" in values


def test_get_enum_values_nonexistent():
    schema = load_schema("requirements.schema.json")
    values = get_enum_values(schema, ["nonexistent"])
    assert values == []
