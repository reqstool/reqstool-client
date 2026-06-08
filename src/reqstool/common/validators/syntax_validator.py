# Copyright © LFV

import json
import logging
from dataclasses import dataclass, field
from enum import Enum, unique
from importlib.resources import files

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from reqstool_python_decorators.decorators.decorators import Requirements

import reqstool.resources.schemas.v1


@dataclass
class JsonSchemaItem:
    short_uri: str
    schema: dict = field(init=False)

    schema_module = reqstool.resources.schemas.v1
    schema_version = schema_module.__name__.split(".")[-1]

    def __post_init__(self):
        self.schema = json.loads(files(self.schema_module).joinpath(self.short_uri).read_text())


@unique
class JsonSchemaTypes(Enum):
    ANNOTATIONS = JsonSchemaItem("annotations.schema.json")
    COMMON = JsonSchemaItem("common.schema.json")
    MANUAL_VERIFICATION_RESULTS = JsonSchemaItem("manual_verification_results.schema.json")
    REQSTOOL_CONFIG = JsonSchemaItem("reqstool_config.schema.json")
    REQUIREMENTS = JsonSchemaItem("requirements.schema.json")
    SOFTWARE_VERIFICATION_CASES = JsonSchemaItem("software_verification_cases.schema.json")


class SyntaxValidator:
    registry = Registry()
    resource = Resource.from_contents(JsonSchemaTypes.COMMON.value.schema)
    registry = resource @ registry
    registry = registry.with_resource(uri="common.schema.json", resource=resource)

    @Requirements("PARSE_0001")
    @staticmethod
    def is_valid_data(json_schema_type: JsonSchemaTypes, data: dict, urn: str) -> bool:
        jsonvalidator_draft202012 = Draft202012Validator(
            schema=json_schema_type.value.schema,
            registry=SyntaxValidator.registry,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )

        validation_errors = jsonvalidator_draft202012.iter_errors(data)
        has_validation_errors: bool = False

        for index, error in enumerate(validation_errors):
            if index == 0:
                logging.error(f"Syntax error(s) for urn '{urn}' using schema: {json_schema_type.value.short_uri}")

            has_validation_errors = True
            message = f" {index + 1}. {error.message}"
            logging.error(message)

        return not has_validation_errors
