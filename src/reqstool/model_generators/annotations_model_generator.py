# Copyright © LFV

import sys
from typing import Dict, List

from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.models.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.models.annotations import AnnotationData, AnnotationsData
from reqstool.models.generated.annotations_schema import Model as AnnotationsPydanticModel, Requirement


class AnnotationsModelGenerator:
    def __init__(self, uri: str, urn: str):
        self.uri = uri
        self.urn = urn
        self.model = self.__generate(uri)

    def __generate(self, uri: str) -> AnnotationsData:
        response = Utils.open_file_https_file(uri)

        yaml = YAML(typ="safe")

        data: dict = yaml.load(response.text)

        if not SyntaxValidator.is_valid_data(json_schema_type=JsonSchemaTypes.ANNOTATIONS, data=data, urn=self.urn):
            sys.exit(EXIT_CODE_SYNTAX_VALIDATION_ERROR)

        validated = AnnotationsPydanticModel.model_validate(data)

        tests = self.__parse_annotations(validated.requirement_annotations.tests if validated.requirement_annotations.tests else {})
        implementations = self.__parse_annotations(validated.requirement_annotations.implementations if validated.requirement_annotations.implementations else {})

        return AnnotationsData(tests=tests, implementations=implementations)

    def __parse_annotations(self, section: dict) -> Dict[UrnId, List[AnnotationData]]:
        dictionary = {}

        for requirement_id, values in section.items():
            urn_id = Utils.convert_id_to_urn_id(self.urn, requirement_id)
            if urn_id not in dictionary:
                dictionary[urn_id] = []

            for value in values:
                ad = AnnotationData(element_kind=value.elementKind.value, fully_qualified_name=value.fullyQualifiedName)
                dictionary[urn_id].append(ad)

        return dictionary
