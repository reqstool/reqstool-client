# Copyright © LFV


from jsonschema import Draft202012Validator
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.validators.syntax_validator import JsonSchemaTypes


@SVCs("SVC_PARSE_0001")
def test_validate_annotations_schema_json():
    Draft202012Validator.check_schema(JsonSchemaTypes.ANNOTATIONS.value.schema)


@SVCs("SVC_PARSE_0001")
def test_validate_common_schema_json():
    Draft202012Validator.check_schema(JsonSchemaTypes.COMMON.value.schema)


@SVCs("SVC_PARSE_0001")
def test_validate_manual_verification_results_schema_json():
    Draft202012Validator.check_schema(JsonSchemaTypes.MANUAL_VERIFICATION_RESULTS.value.schema)


@SVCs("SVC_PARSE_0001")
def test_validate_requirements_config_schema_json():
    Draft202012Validator.check_schema(JsonSchemaTypes.REQSTOOL_CONFIG.value.schema)


@SVCs("SVC_PARSE_0001")
def test_validate_requirements_schema_json():
    Draft202012Validator.check_schema(JsonSchemaTypes.REQUIREMENTS.value.schema)


@SVCs("SVC_PARSE_0001")
def test_validate_software_verification_cases_schema_json():
    Draft202012Validator.check_schema(JsonSchemaTypes.SOFTWARE_VERIFICATION_CASES.value.schema)
